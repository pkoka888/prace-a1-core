"""Generate application draft. Output goes to output/provisional/."""
import json
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from portal.release1a.a1_drafts import prepare_application_draft
from portal.release1a.models import Organization


class Command(BaseCommand):
    help = "Prepare a synthetic A1 input case through the shared unverified-draft publisher; never issue or confirm."

    def add_arguments(self, parser):
        parser.add_argument("--case-id", type=int, required=True)
        parser.add_argument("--organization-id", type=int, required=True)
        parser.add_argument("--actor-id", type=int, required=True)

    def handle(self, *args, **options):
        try:
            organization = Organization.objects.get(pk=options["organization_id"])
            user = get_user_model().objects.get(pk=options["actor_id"], is_active=True)
            generation = prepare_application_draft(user, organization, options["case_id"])
            package = Path(settings.DOCUMENT_STORAGE_ROOT) / "j4" / generation.artifact_reference["key"]
        except Exception:
            raise CommandError("A1_DRAFT_BLOCKED_OR_UNAVAILABLE") from None
        self.stdout.write(json.dumps({"case_ref": generation.reservation.case_id, "generation_ref": generation.pk,
            "generation_revision": generation.revision, "status": "UNVERIFIED_DRAFT",
            "pdf": str(package / "artifact.pdf"), "receipt": str(package / "receipt.json"),
            "visual_review": "pending", "identity_verification": "pending"}, sort_keys=True))
