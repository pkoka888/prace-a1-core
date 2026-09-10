"""Thin synthetic CLI for the shared revision-bound compatibility publisher."""
import json
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from portal.release1a.a1_exports import publish_input_cohort
from portal.release1a.models import Organization


class Command(BaseCommand):
    help = "Publish protected synthetic A1 compatibility inputs; no PDF generation or human confirmation."

    def add_arguments(self, parser):
        parser.add_argument('--case', action='append', required=True, metavar='ID:SOURCE_SHA256')
        parser.add_argument('--organization-id', type=int, required=True)
        parser.add_argument('--actor-id', type=int, required=True)

    def handle(self, *args, **options):
        try:
            selections=[]
            for value in options['case']:
                case_id,digest=value.split(':',1)
                if not case_id.isascii() or not case_id.isdecimal():
                    raise ValueError('INVALID_CASE')
                selections.append({'case_id':int(case_id),'expected_source_hash':digest})
            organization=Organization.objects.get(pk=options['organization_id'])
            user=get_user_model().objects.get(pk=options['actor_id'],is_active=True)
            result=publish_input_cohort(user,organization,selections)
        except Exception:
            raise CommandError('A1_INPUT_EXPORT_BLOCKED_OR_UNAVAILABLE') from None
        self.stdout.write(json.dumps({**result,
            'directory':str(Path(settings.DOCUMENT_STORAGE_ROOT)/result['relative_path'])},sort_keys=True))
