"""Authorized access to exact published compatibility inputs; no GET publication."""
import json
import re

from django.conf import settings
from django.db import transaction
from .a1_exports import _bound_input_profiles, _current_input_snapshot
from .document_intake import audit
from .identity import _authorize, _lock_organization
from .input_artifacts import read_input_artifact
from .models import A1Case, AuditEvent
from .services import StaleWrite


@transaction.atomic
def read_input_bundle(user, organization, case_id, manifest_hash):
    _authorize(user, organization, 'a1:prepare')
    _lock_organization(organization)
    case = A1Case.objects.get(pk=case_id, organization=organization, worker__organization=organization)
    if not isinstance(manifest_hash, str) or not re.fullmatch('[0-9a-f]{64}', manifest_hash):
        raise ValueError('INPUT_BUNDLE_REFERENCE_INVALID')
    # Orphaned writes cannot become downloadable before the publisher's audit commits.
    if not AuditEvent.objects.filter(organization=organization, event_type='a1.input_bundle_published',
                                    object_ref=f'bundle:{manifest_hash}', outcome='success').exists():
        raise A1Case.DoesNotExist()
    payloads = read_input_artifact(settings.DOCUMENT_STORAGE_ROOT, manifest_hash)
    manifest = json.loads(payloads['manifest.json'])
    sources = manifest.get('sources', [])
    if (manifest.get('schema_version') != 'a1-bound-input-cohort-1'
            or manifest.get('organization_ref') != organization.pk
            or not sources or case.pk not in [s.get('case_ref') for s in sources]):
        raise ValueError('INPUT_BUNDLE_SCOPE_INVALID')
    snapshots = json.loads(payloads['input_snapshots.json'])['snapshots']
    if len(sources) != len(snapshots):
        raise ValueError('INPUT_BUNDLE_SOURCES_INVALID')
    for source, snapshot in zip(sources, snapshots):
        selected = A1Case.objects.get(pk=source['case_ref'], organization=organization,
                                     worker__organization=organization)
        current = _current_input_snapshot(user, organization, selected)
        if (selected.source_hash != source['source_hash'] or current != snapshot
                or current['employee_id'] != source['employee_id']):
            raise StaleWrite('INPUT_BUNDLE_SOURCE_CHANGED')
    if _bound_input_profiles(payloads) != payloads:
        raise StaleWrite('INPUT_BUNDLE_PROFILE_CHANGED')
    audit(user, organization, 'a1.input_bundle_read', f'bundle:{manifest_hash}')
    return payloads
