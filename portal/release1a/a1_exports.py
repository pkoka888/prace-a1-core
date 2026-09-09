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
    row.update(employee_id=f"worker-{worker.pk}", identity_reviewed="NO", certificate_reviewed="NO",
               approved_for_pdf="NO", validated_by_user="0")
    for subject in ("activity", "certificate", "signatory"):
        row[subject + "_source_status"] = "UNVERIFIED"
    provenance, blockers = {}, []
    dependencies = {"worker_ref": worker.pk, "worker_version": worker.version,
                    "activity_profile": worker.activity_profile, "worker_state": worker.state}
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
    provenance["employee_id"] = {"kind": "database_key", "worker_ref": worker.pk, "confirmed": False}
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


@transaction.atomic
def export_input_case(user, organization, case_id):
    """Return revision-bound JSON and exactly 44 CSV fields; no publication side effect."""
    _authorize(user, organization, "a1:prepare")
    _lock_organization(organization)
    case = A1Case.objects.get(pk=case_id, organization=organization, worker__organization=organization)
    snapshot = case.source_snapshot_json
    if snapshot.get("schema_version") != "a1-input-1" or result_hash(snapshot) != case.source_hash:
        raise ValueError("A1_SNAPSHOT_UNSUPPORTED_OR_CORRUPT")
    deps = snapshot["dependencies"]
    current = _snapshot(user, organization, case.worker_id,
        deps.get("assignment", {}).get("ref"), deps.get("claim", {}).get("claim_ref"))
    if case.is_stale or result_hash(current) != case.source_hash:
        raise StaleWrite("A1_INPUT_STALE")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(snapshot["row"])
    audit(user, organization, "a1.input_exported", f"a1:{case.pk}")
    return {"json": canonical_json(snapshot).encode("utf-8"), "csv": output.getvalue().encode("utf-8")}
