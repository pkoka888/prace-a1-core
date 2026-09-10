"""Explicit synthetic legacy-key mappings; never infer identity from names or files."""
import re
from django.db import transaction
from django.utils import timezone
from src.document_core.serialization import result_hash
from .identity import _authorize, _lock_organization
from .document_intake import audit
from .models import Worker, A1Case
from .services import StaleWrite


@transaction.atomic
def reconcile_legacy_keys(user, organization, mappings, *, source_sha256):
    """Apply one selected-source mapping batch or roll it back in full.

    source_sha256 identifies the operator-selected reconciliation input. It does
    not assert that this service has read or verified an external source file.
    """
    _authorize(user, organization, "worker:update")
    if (not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
            or not isinstance(mappings, list) or not mappings):
        raise ValueError("LEGACY_MAPPING_INPUT_INVALID")
    selected, keys = {}, set()
    for item in mappings:
        if not isinstance(item, dict) or set(item) != {"worker_id", "expected_version", "legacy_employee_id"}:
            raise ValueError("LEGACY_MAPPING_INPUT_INVALID")
        worker_id, version, key = item["worker_id"], item["expected_version"], item["legacy_employee_id"]
        if (type(worker_id) is not int or worker_id <= 0 or type(version) is not int or version <= 0
                or not isinstance(key, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key)
                or len(key) > 120 or re.fullmatch(r"worker-[0-9]+", key)):
            raise ValueError("LEGACY_MAPPING_INPUT_INVALID")
        if worker_id in selected or key in keys:
            raise ValueError("LEGACY_MAPPING_DUPLICATE")
        selected[worker_id] = item
        keys.add(key)
    _lock_organization(organization)
    workers = list(Worker.objects.select_for_update().filter(
        organization=organization, pk__in=selected).order_by("pk"))
    if len(workers) != len(selected):
        raise ValueError("LEGACY_WORKER_UNAVAILABLE")
    if Worker.objects.filter(organization=organization, legacy_employee_id__in=keys).exclude(pk__in=selected).exists():
        raise ValueError("LEGACY_KEY_COLLISION")
    pending = []
    for worker in workers:
        item = selected[worker.pk]
        if worker.state == Worker.State.ARCHIVED:
            raise ValueError("LEGACY_WORKER_ARCHIVED")
        if worker.legacy_employee_id:
            provenance = worker.legacy_key_provenance
            if worker.legacy_employee_id != item["legacy_employee_id"]:
                raise ValueError("LEGACY_KEY_ALREADY_ESTABLISHED")
            if (not isinstance(provenance, dict) or provenance.get("source_sha256") != source_sha256
                    or provenance.get("expected_version") != item["expected_version"]
                    or worker.version != item["expected_version"] + 1):
                raise StaleWrite("LEGACY_MAPPING_STALE")
            continue
        if worker.version != item["expected_version"]:
            raise StaleWrite("WORKER_VERSION_STALE")
        pending.append(worker)
    # Every mapping has been checked before the first mutation.
    occurred_at = timezone.now().isoformat()
    for worker in pending:
        item = selected[worker.pk]
        worker.legacy_employee_id = item["legacy_employee_id"]
        worker.legacy_key_provenance = {"schema_version": 1, "source_sha256": source_sha256,
            "mapping_sha256": result_hash(item), "actor_ref": user.pk,
            "occurred_at": occurred_at, "expected_version": item["expected_version"]}
        worker.version += 1
        worker.save(update_fields=["legacy_employee_id", "legacy_key_provenance", "version"])
        A1Case.objects.filter(organization=organization, worker=worker).update(is_stale=True)
        audit(user, organization, "worker.legacy_key_reconciled", f"worker:{worker.pk}")
    return workers
