"""Run the synthetic inbox adapter under an explicit existing operator account."""
import json
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from portal.release1a.inbox import process_inbox
from portal.release1a.models import Organization


class Command(BaseCommand):
    help = ("Process synthetic UUID batches with atomically published ready.json; "
            "requires DOCUMENT_INBOX_ROOTS[organization_id] beneath DOCUMENT_STORAGE_ROOT. "
            "Manifest: organization_id and files [{name: <uuidhex>.png, sha256: <digest>}]. "
            "Optional per-file activity_profile (employee/self_employed) permits eligible unconfirmed worker drafts. "
            "Stores OCR proposals and private receipts; generates eligible UNVERIFIED A1 drafts, without confirming facts.")

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", type=int,
            help="Defaults to configured DOCUMENT_INBOX_ORGANIZATION_ID; no implicit organization.")
        parser.add_argument("--actor-id", type=int,
            help="Defaults to configured DOCUMENT_INBOX_ACTOR_ID; existing authorized account required.")

    def handle(self, *args, **options):
        try:
            organization_id = options["organization_id"]
            actor_id = options["actor_id"]
            if organization_id is None:
                organization_id = getattr(settings, "DOCUMENT_INBOX_ORGANIZATION_ID", None)
            if actor_id is None:
                actor_id = getattr(settings, "DOCUMENT_INBOX_ACTOR_ID", None)
            if any(type(value) is not int or value <= 0 for value in (organization_id, actor_id)):
                raise ValueError("INBOX_OPERATOR_CONFIGURATION_REQUIRED")
            organization = Organization.objects.get(pk=organization_id)
            user = get_user_model().objects.get(pk=actor_id, is_active=True)
            results = process_inbox(user, organization)
        except Exception:
            raise CommandError("INBOX_PROCESSING_DENIED_OR_UNAVAILABLE") from None
        self.stdout.write(json.dumps(results, sort_keys=True))
        if any(result["status"] != "completed" for result in results):
            raise CommandError("INBOX_HAS_UNRESOLVED_ITEMS")
