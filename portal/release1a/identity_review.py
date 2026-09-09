"""Signed BO association choices; matching stays in the canonical identity service."""
from django.core import signing
from django.db import transaction

from .document_intake import audit, evaluate_identity_proposals
from .identity import (_authorize, _lock_organization, _lock_sources, _latest_revision,
                       resolve_identity_evaluation)
from .models import IdentityEvaluation, Worker, OcrRun
from .services import StaleWrite

SALT = "release1a.identity-association.v1"


def association_review_context(user, organization, run_ids):
    """Read-only review evidence; no association or machine record is saved on GET."""
    _authorize(user, organization, "document:confirm")
    run_ids = sorted(set(run_ids))
    evidence = evaluate_identity_proposals(user, organization, run_ids)
    workers = list(Worker.objects.filter(organization=organization).exclude(
        state=Worker.State.ARCHIVED).order_by("pk"))
    revisions = {worker.pk: _latest_revision(organization, worker) for worker in workers}
    contexts = {}
    for region in evidence["regions"]:
        options = []
        for worker in workers:
            revision = revisions[worker.pk]
            token = signing.dumps({"actor": user.pk, "organization": organization.pk,
                "runs": run_ids, "run": region["run_ref"], "region": region["region_ref"],
                "evaluation": evidence["evaluation_sha256"], "worker": worker.pk,
                "worker_version": worker.version, "revision": revision.pk if revision else None},
                salt=SALT, compress=True)
            options.append({"worker": worker, "token": token})
        contexts[(region["run_ref"], region["region_ref"])] = {"worker_options": options}
    return contexts


@transaction.atomic
def confirm_association(user, organization, *, token, reason="", allowed_run_ids):
    """Validate displayed source and worker revisions before the canonical decision."""
    _authorize(user, organization, "document:confirm")
    if not isinstance(token, str) or not token or not isinstance(reason, str):
        raise StaleWrite("IDENTITY_REVIEW_TOKEN_REQUIRED")
    try:
        choice = signing.loads(token, salt=SALT)
    except (signing.BadSignature, ValueError, TypeError):
        raise StaleWrite("IDENTITY_REVIEW_TOKEN_INVALID") from None
    if (not isinstance(choice, dict) or choice.get("actor") != user.pk or
            choice.get("organization") != organization.pk or
            choice.get("runs") != sorted(set(allowed_run_ids)) or
            choice.get("run") not in allowed_run_ids):
        raise StaleWrite("IDENTITY_REVIEW_SCOPE_STALE")
    _lock_organization(organization)
    _lock_sources(organization, choice["runs"])
    try:
        evidence = evaluate_identity_proposals(user, organization, choice["runs"])
    except (ValueError, OcrRun.DoesNotExist):
        raise StaleWrite("IDENTITY_REVIEW_SOURCE_STALE") from None
    if evidence["evaluation_sha256"] != choice.get("evaluation"):
        raise StaleWrite("IDENTITY_REVIEW_SOURCE_STALE")
    # The explicit confirmation authorizes recording its exact machine evidence;
    # upload permission is intentionally not required for a reviewing operator.
    record, created = IdentityEvaluation.objects.get_or_create(
        organization=organization, evaluation_sha256=evidence["evaluation_sha256"],
        defaults={"evidence": evidence})
    if record.evidence != evidence:
        raise ValueError("IDENTITY_EVALUATION_CORRUPT")
    if created:
        audit(user, organization, "identity.evaluated", f"identity_evaluation:{record.pk}")
    try:
        return resolve_identity_evaluation(user, organization, record.pk,
            choice["run"], choice["region"], choice["worker"],
            expected_worker_version=choice["worker_version"],
            expected_revision_id=choice["revision"], reason=reason)
    except Worker.DoesNotExist:
        raise StaleWrite("IDENTITY_REVIEW_WORKER_STALE") from None
