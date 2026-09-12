"""One synthetic DB-to-canonical-CSV input contract, before A1 publication.

Exports preserve pending/confirmed provenance. They never manufacture approval,
certificate issuance, dates or numbers; canonical finalization remains separate.
"""
import csv
import io
from datetime import datetime
from django.db import transaction
from scripts.finalize_a1 import CSV_FIELDS, readiness_report
from src.document_core.serialization import canonical_json, result_hash
from .document_intake import audit, read_result
from .identity import _authorize, _lock_organization, _lock_sources
from .models import (A1Case, Assignment, Worker, WorkerIdentityRevision,
                     WorkerIdentityClaim, FieldProposal)
from .services import StaleWrite

IDENTITY = {"surname": "surname", "family_name": "surname", "given_name": "given_name",
            "dob": "dob", "birth_date": "dob", **{f: f for f in (
                "birth_place", "nationality", "sex", "insurance_number", "street",
                "house_number", "city", "district", "postal_code", "country_code")}}
GROUPS = {
    "employment": {"employer_id": "employment_id", "employer_name": "employment_name",
                   **{f: "employment_" + f for f in ("street", "house_number", "city", "postal_code", "country_code")}},
    "activity": {"name": "activity_name", "address": "activity_address"},
    "certificate": {f: f for f in ("document_id", "start_date", "end_date")},
    "institution": {"resolved_ossz": "resolved_ossz", "profile_key": "institution_profile",
                    "issue_date": "issue_date", "signed_by": "signed_by"},
}


def _facts(value):
    if not isinstance(value, dict) or set(value) - {*GROUPS, "status_profile"}:
        raise ValueError("A1_FACTS_FIELDS_INVALID")
    for group, fields in GROUPS.items():
        block = value.get(group, {})
        if (not isinstance(block, dict) or set(block) - set(fields) or
                any(not isinstance(v, str) or len(v) > 240 for v in block.values())):
            raise ValueError("A1_FACTS_FIELDS_INVALID")
    if value.get("status_profile", "") not in ("", "posted_employee", "employee_multi_state", "self_employed_multi_state"):
        raise ValueError("A1_STATUS_PROFILE_INVALID")
    return value


@transaction.atomic
def update_assignment_facts(user, organization, assignment_id, facts, *, expected_version):
    _authorize(user, organization, "assignment:update")
    _lock_organization(organization)
    assignment = Assignment.objects.select_for_update().get(pk=assignment_id, organization=organization,
                                                           worker__organization=organization)
    if type(expected_version) is not int or assignment.version != expected_version:
        raise StaleWrite("ASSIGNMENT_VERSION_STALE")
    facts = _facts(facts)
    if assignment.a1_facts_json != facts:
        assignment.a1_facts_json = facts
        assignment.version += 1
        assignment.save(update_fields=["a1_facts_json", "version"])
        A1Case.objects.filter(organization=organization, worker=assignment.worker).update(is_stale=True)
        audit(user, organization, "a1.assignment_facts_updated", f"assignment:{assignment.pk}")
    return assignment


def _value(field, value):
    if not isinstance(value, str):
        raise ValueError("A1_INPUT_VALUE_INVALID")
    if field in {"dob", "start_date", "end_date", "issue_date"} and value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            try:
                return datetime.strptime(value, "%d.%m.%Y").strftime("%d.%m.%Y")
            except ValueError:
                raise ValueError("A1_DATE_INVALID") from None
    return value


def _snapshot(user, organization, worker_id, assignment_id, claim_id):
    worker = Worker.objects.select_for_update(no_key=True).get(pk=worker_id, organization=organization)
    if worker.state == Worker.State.ARCHIVED:
        raise ValueError("WORKER_ARCHIVED")
    row = dict.fromkeys(CSV_FIELDS, "")
    row.update(employee_id=worker.legacy_employee_id or f"worker-{worker.pk}", identity_reviewed="NO", certificate_reviewed="NO",
               approved_for_pdf="NO", validated_by_user="0")
    for subject in ("activity", "certificate", "signatory"):
        row[subject + "_source_status"] = "UNVERIFIED"
    provenance, blockers = {}, []
    dependencies = {"worker_ref": worker.pk, "worker_version": worker.version,
                    "activity_profile": worker.activity_profile, "worker_state": worker.state}
    if worker.legacy_employee_id:
        dependencies["legacy_key_provenance"] = worker.legacy_key_provenance
        provenance["employee_id"] = {"kind": "explicit_legacy_mapping", "worker_ref": worker.pk,
                                     **worker.legacy_key_provenance}
    def put(field, value, source):
        row[field] = _value(field, value)
        provenance[field] = source
    for field, value in (("given_name", worker.given_name), ("surname", worker.family_name), ("dob", str(worker.birth_date))):
        put(field, value, {"kind": "worker_projection", "worker_ref": worker.pk, "confirmed": False})
    claims = WorkerIdentityClaim.objects.filter(organization=organization, worker=worker).order_by("pk")
    if claim_id is not None:
        claims = claims.filter(pk=claim_id)
    selected = list(claims)
    if claim_id is not None and not selected:
        raise ValueError("A1_CLAIM_UNAVAILABLE")
    if len(selected) > 1:
        raise ValueError("A1_CLAIM_SELECTION_REQUIRED")
    if selected:
        claim = selected[0]
        _lock_sources(organization, [claim.ocr_run_id])
        run = claim.ocr_run
        if (claim.evaluation.organization_id != organization.pk or
                run.document.documentversion_set.order_by("-version_number").first().pk != run.version_id):
            raise ValueError("A1_SOURCE_STALE")
        payload = read_result(user, organization, run.pk)
        if not payload or payload.get("status") != "completed":
            raise ValueError("A1_SOURCE_UNAVAILABLE")
        dependencies["claim"] = {"claim_ref": claim.pk, "evaluation_ref": claim.evaluation_id,
            "run_ref": run.pk, "region_ref": claim.region_id, "version_ref": run.version_id,
            "source_sha256": run.version.sha256, "output_sha256": run.output_sha256}
        put("source_scans", f"document:{run.document_id}:version:{run.version_id}",
            {"kind": "document_reference", "document_ref": run.document_id, "version_ref": run.version_id, "confirmed": False})
        proposals = FieldProposal.objects.filter(organization=organization, ocr_run=run,
            document=run.document, version=run.version, document_region_id=claim.region_id).order_by("pk")
        grouped = {}
        for proposal in proposals:
            field = IDENTITY.get(proposal.field_name)
            if field:
                grouped.setdefault(field, []).append(proposal)
        for field, proposals in grouped.items():
            try:
                values = {_value(field, p.proposed_value) for p in proposals}
            except ValueError:
                blockers.append("conflict:" + field)
                continue
            if len(values) != 1 or any(p.validation_findings for p in proposals):
                blockers.append("conflict:" + field)
                continue
            put(field, values.pop(), {"kind": "ocr_proposal", "proposal_refs": [p.pk for p in proposals], "confirmed": False})
    revision = WorkerIdentityRevision.objects.filter(organization=organization, worker=worker).order_by("-revision_number", "-pk").first()
    if revision:
        if (not revision.confirmed_by_id or not revision.source_document_id or not revision.source_version_id or
                revision.source_document.organization_id != organization.pk or
                revision.source_version.organization_id != organization.pk or
                revision.source_version.document_id != revision.source_document_id):
            raise ValueError("A1_REVISION_EVIDENCE_REQUIRED")
        dependencies["identity_revision"] = {"ref": revision.pk, "number": revision.revision_number,
                                              "fields_sha256": result_hash(revision.confirmed_fields)}
        mapped = {}
        for key, value in revision.confirmed_fields.items():
            if key in IDENTITY:
                field = IDENTITY[key]
                value = _value(field, value)
                if field in mapped and mapped[field] != value:
                    raise ValueError("A1_CONFIRMED_ALIAS_CONFLICT")
                mapped[field] = value
        for field, value in mapped.items():
            put(field, value, {"kind": "confirmed_revision", "revision_ref": revision.pk,
                "actor_ref": revision.confirmed_by_id, "confirmed_at": revision.confirmed_at.isoformat(),
                "document_ref": revision.source_document_id, "version_ref": revision.source_version_id, "confirmed": True})
            blockers = [b for b in blockers if b != "conflict:" + field]
    assignments = Assignment.objects.select_for_update().filter(organization=organization, worker=worker,
        state__in=[Assignment.State.ACTIVE, Assignment.State.PLANNED]).order_by("pk")
    if assignment_id is not None:
        assignments = assignments.filter(pk=assignment_id)
    assignments = list(assignments)
    if assignment_id is not None and not assignments:
        raise ValueError("A1_ASSIGNMENT_UNAVAILABLE")
    if len(assignments) > 1:
        raise ValueError("A1_ASSIGNMENT_SELECTION_REQUIRED")
    if assignments:
        assignment = assignments[0]
        facts = _facts(assignment.a1_facts_json)
        dependencies["assignment"] = {"ref": assignment.pk, "version": assignment.version,
                                      "facts_sha256": result_hash(facts), "state": assignment.state,
                                      "start": str(assignment.start), "end": str(assignment.end),
                                      "workplace_label": assignment.workplace_label,
                                      "activity_label": assignment.activity_label}
        put("status_profile", facts.get("status_profile", ""), {"kind": "assignment_input", "assignment_ref": assignment.pk, "confirmed": False})
        for group, fields in GROUPS.items():
            for key, field in fields.items():
                if key in facts.get(group, {}):
                    put(field, facts[group][key], {"kind": "assignment_input", "assignment_ref": assignment.pk,
                                                 "version": assignment.version, "path": f"{group}.{key}", "confirmed": False})
        if row["status_profile"] and (row["status_profile"] == "self_employed_multi_state") != (worker.activity_profile == "self_employed"):
            blockers.append("activity_profile_mismatch")
        if row["status_profile"] == "self_employed_multi_state":
            for field, value in (("activity_name", ""), ("activity_address", "DE, CZ")):
                if field not in provenance:
                    put(field, value, {"kind": "policy_default", "policy": "self-employed-provisional-section5-v1", "confirmed": False})
    else:
        blockers.append("assignment_missing")
    provenance.setdefault("employee_id", {"kind": "database_key", "worker_ref": worker.pk, "confirmed": False})
    for field in CSV_FIELDS:
        provenance.setdefault(field, {"kind": "system_state" if row[field] else "missing", "confirmed": False})
    # Gate inputs remain honest: accepted individual fields are not whole-input approval.
    readiness = readiness_report([row], provisional=True)
    blockers += readiness["employees"][0]["blockers"]
    return {"schema_version": "a1-input-1", "organization_ref": organization.pk,
            "employee_id": row["employee_id"], "row": row, "provenance": provenance,
            "dependencies": dependencies, "blockers": sorted(set(blockers)), "scope": "input_preparation"}


@transaction.atomic
def prepare_input_case(user, organization, worker_id, *, assignment_id=None, claim_id=None):
    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    snapshot = _snapshot(user, organization, worker_id, assignment_id, claim_id)
    digest = result_hash(snapshot)
    existing = A1Case.objects.filter(organization=organization, worker_id=worker_id, source_hash=digest).first()
    if existing:
        if existing.source_snapshot_json != snapshot:
            raise ValueError("A1_SNAPSHOT_CORRUPT")
        if existing.is_stale:
            A1Case.objects.filter(organization=organization, worker_id=worker_id,
                source_snapshot_json__schema_version="a1-input-1").exclude(pk=existing.pk).update(is_stale=True)
            existing.is_stale = False
            existing.save(update_fields=["is_stale"])
            audit(user, organization, "a1.input_revalidated", f"a1:{existing.pk}")
        return existing
    A1Case.objects.filter(organization=organization, worker_id=worker_id,
        source_snapshot_json__schema_version="a1-input-1").update(is_stale=True)
    case = A1Case.objects.create(organization=organization, worker_id=worker_id, source_hash=digest,
        source_snapshot_json=snapshot, readiness=A1Case.Readiness.BLOCKED)
    audit(user, organization, "a1.input_prepared", f"a1:{case.pk}")
    return case


def _current_input_snapshot(user, organization, case):
    """Validate a locked caller's snapshot without recording an export.

    The stored snapshot is authoritative: its digest must match
    ``case.source_hash`` (corruption guard) and it must declare the
    canonical schema version. Staleness is detected via the
    live-source re-hash against the same digest: ``dependencies``-
    bound snapshots recompute the canonical ``_snapshot`` for the
    recorded selections; J4 ``prepare_a1`` snapshots recompute the
    canonical ``current_a1_source`` live hash. Republishing a stale
    input is rejected before any number is reserved.
    """
    snapshot = case.source_snapshot_json
    schema_version = snapshot.get("schema_version")
    if schema_version != "a1-input-1":
        raise ValueError("A1_SNAPSHOT_UNSUPPORTED_OR_CORRUPT")
    if result_hash(snapshot) != case.source_hash:
        raise ValueError("A1_SNAPSHOT_CORRUPT")
    if case.is_stale:
        raise StaleWrite("A1_INPUT_STALE")
    deps = snapshot.get("dependencies")
    if deps is None:
        # J4 ``prepare_a1`` snapshots carry the J4 subset
        # ``{schema_version, profile, assignments}`` without a
        # ``dependencies`` block. The stored-hash check above is the
        # corruption guard for those rows; staleness is bound by
        # recomputing the live J4 source hash through the canonical
        # ``current_a1_source`` contract (profile projection +
        # assignment facts/version/state/dates) and comparing it to
        # the prepared ``source_hash``. An out-of-band mutation that
        # never set ``is_stale``—e.g. a direct assignment-fact or
        # worker-projection write—therefore cannot leak into the
        # rebuilt canonical row under the original hash.
        from .services import current_a1_source
        _, _, live_hash = current_a1_source(case.worker, case.organization)
        if live_hash != case.source_hash:
            raise StaleWrite("A1_INPUT_STALE")
        # Build the canonical ``row`` / ``dependencies`` shape on the
        # fly so downstream renderers (``export_input_case`` and the
        # application-draft publisher) receive the contract they
        # expect. ``_snapshot`` re-reads the confirmed identity
        # revision and the worker's assignment facts; the live-hash
        # check above already proved those profile/assignment inputs
        # still match what the case was prepared from.
        rebuilt = _snapshot(user, organization, case.worker_id, None, None)
        rebuilt["dependencies"] = rebuilt.get("dependencies", {})
        rebuilt["dependencies"]["source_hash"] = case.source_hash
        if "profile" in snapshot:
            rebuilt["profile"] = snapshot["profile"]
        if "assignments" in snapshot:
            rebuilt["assignments"] = snapshot["assignments"]
        return rebuilt
    current = _snapshot(user, organization, case.worker_id,
        deps.get("assignment", {}).get("ref"),
        deps.get("claim", {}).get("claim_ref"))
    if result_hash(current) != case.source_hash:
        raise StaleWrite("A1_INPUT_STALE")
    return snapshot


@transaction.atomic
def export_input_case(user, organization, case_id):
    """Return revision-bound JSON and exactly 44 CSV fields; no publication side effect."""
    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    case = A1Case.objects.get(pk=case_id, organization=organization, worker__organization=organization)
    snapshot = _current_input_snapshot(user, organization, case)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(snapshot["row"])
    audit(user, organization, "a1.input_exported", f"a1:{case.pk}")
    return {"json": canonical_json(snapshot).encode("utf-8"), "csv": output.getvalue().encode("utf-8")}


@transaction.atomic
def export_input_cohort(user, organization, selections):
    """Return deterministic compatibility inputs for explicitly pinned input cases.

    No files, profiles or PDFs are published. Pending fields stay pending; this
    bundle cannot bypass the canonical generation/confirmation gates.
    """
    import hashlib
    import json
    import re

    _authorize(user, organization, "a1:prepare")
    if not isinstance(selections, list) or not selections:
        raise ValueError("A1_COHORT_SELECTION_REQUIRED")
    selected = {}
    for item in selections:
        if (not isinstance(item, dict) or set(item) != {"case_id", "expected_source_hash"}
                or type(item["case_id"]) is not int or item["case_id"] <= 0
                or not isinstance(item["expected_source_hash"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["expected_source_hash"])):
            raise ValueError("A1_COHORT_SELECTION_INVALID")
        if item["case_id"] in selected:
            raise ValueError("A1_COHORT_DUPLICATE_CASE")
        selected[item["case_id"]] = item["expected_source_hash"]
    _lock_organization(organization)
    snapshots, workers, keys, document_ids = [], set(), set(), set()
    for case_id in sorted(selected):
        case = A1Case.objects.get(pk=case_id, organization=organization, worker__organization=organization)
        if case.source_hash != selected[case_id]:
            raise StaleWrite("A1_COHORT_SOURCE_STALE")
        # Reuse the canonical current-source validation and audit in the same transaction.
        snapshot = json.loads(export_input_case(user, organization, case_id)["json"])
        key = snapshot["employee_id"]
        document_id = snapshot["row"]["document_id"]
        if case.worker_id in workers or key in keys:
            raise ValueError("A1_COHORT_DUPLICATE_WORKER_OR_KEY")
        if document_id and document_id in document_ids:
            raise ValueError("A1_COHORT_DUPLICATE_DOCUMENT_ID")
        workers.add(case.worker_id); keys.add(key)
        if document_id:
            document_ids.add(document_id)
        snapshots.append((case_id, snapshot))
    snapshots.sort(key=lambda entry: entry[1]["employee_id"])
    rows = [snapshot["row"] for _, snapshot in snapshots]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    employees = []
    for case_id, snapshot in snapshots:
        row = snapshot["row"]
        employees.append({"id": row["employee_id"],
            "person": {field: row[field] for field in (
                "surname", "given_name", "dob", "birth_place", "nationality", "sex", "insurance_number")},
            "residence": {field: row[field] for field in (
                "street", "house_number", "city", "district", "postal_code", "country_code")},
            "employment": {"kind": snapshot["dependencies"]["activity_profile"]},
            "a1": {"status_profile": row["status_profile"]},
            "provenance": {"kind": "database_input_snapshot", "case_ref": case_id,
                "source_hash": selected[case_id], "fields": snapshot["provenance"]}})
    cohort = {"issue_dates": {row["employee_id"]: row["issue_date"] for row in rows},
              "document_ids": {row["employee_id"]: row["document_id"] for row in rows},
              "additional_people": []}
    payloads = {"review.csv": output.getvalue().encode("utf-8"),
                "cohort.json": canonical_json(cohort).encode("utf-8"),
                "employees_normalized.json": canonical_json({"employees": employees}).encode("utf-8"),
                "input_snapshots.json": canonical_json({"snapshots": [s for _, s in snapshots]}).encode("utf-8")}
    manifest = {"schema_version": "a1-input-cohort-1", "organization_ref": organization.pk,
        "scope": "pending_compatibility_inputs", "sources": [
            {"case_ref": case_id, "source_hash": selected[case_id], "employee_id": snapshot["employee_id"]}
            for case_id, snapshot in snapshots],
        "payload_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}}
    payloads["manifest.json"] = canonical_json(manifest).encode("utf-8")
    audit(user, organization, "a1.cohort_exported", f"cohort:{result_hash(manifest)}")
    return payloads


def _bound_input_profiles(payloads):
    """Freeze validated profile bytes without changing the underlying input snapshots."""
    import hashlib
    import json
    import os
    from pathlib import Path
    from django.conf import settings
    from scripts.finalize_a1 import _slug, validate_profile

    root = Path(getattr(settings, "A1_DRAFT_PROFILE_ROOT", settings.BASE_DIR / "config/institutions"))
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("A1_PROFILE_ROOT_INVALID")
    snapshots = json.loads(payloads["input_snapshots.json"])["snapshots"]
    files = {}
    for snapshot in snapshots:
        key = _slug(snapshot["row"]["institution_profile"])
        name = f"profiles/{key}.json"
        if name in files:
            continue
        path = root / f"{key}.json"
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            import stat
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("A1_PROFILE_NOT_REGULAR")
            raw = stream.read()
        validate_profile(json.loads(raw), key, provisional=True)
        files[name] = raw
    result = dict(payloads)
    result.update(files)
    manifest = json.loads(result["manifest.json"])
    manifest["schema_version"] = "a1-bound-input-cohort-1"
    manifest["payload_sha256"].update({name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()})
    result["manifest.json"] = canonical_json(manifest).encode("utf-8")
    return result


@transaction.atomic
def publish_input_cohort(user, organization, selections):
    """Publish or recover one protected synthetic input bundle, never a PDF approval."""
    import hashlib
    from django.conf import settings
    from .input_artifacts import publish_input_artifact

    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    inputs = export_input_cohort(user, organization, selections)
    payloads = _bound_input_profiles(inputs)
    # Detect a profile edit while collecting/validating the selected set.
    if _bound_input_profiles(inputs) != payloads:
        raise StaleWrite("A1_INPUT_PROFILES_CHANGED")
    reference = publish_input_artifact(settings.DOCUMENT_STORAGE_ROOT, payloads)
    if _bound_input_profiles(inputs) != payloads:
        raise StaleWrite("A1_INPUT_PROFILES_CHANGED")
    audit(user, organization, "a1.input_bundle_published", f"bundle:{reference['manifest_sha256']}")
    return {**reference, "status": "PENDING_COMPATIBILITY_INPUTS",
            "bundle_sha256": hashlib.sha256(payloads["manifest.json"]).hexdigest()}
