"""Sequential, organization-scoped consumer of durable synthetic OCR runs."""
import json
import math
import os
from pathlib import Path
import tempfile
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connections, DatabaseError

from portal.release1a.document_intake import authorize, process_pending
from portal.release1a.models import Organization


class Command(BaseCommand):
    help = "Process committed OCR work; one job at a time, synthetic environments only."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", type=int, required=True)
        parser.add_argument("--actor-id", type=int, required=True)
        parser.add_argument("--run-id", type=int)
        parser.add_argument("--max-runs", type=int, default=1)
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--poll-interval", type=float, default=1.0)
        parser.add_argument("--ready-file")

    def _scope(self, options):
        if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
            raise CommandError("OCR_SYNTHETIC_ONLY")
        try:
            actor = get_user_model().objects.get(pk=options["actor_id"], is_active=True)
            organization = Organization.objects.get(pk=options["organization_id"])
            authorize(actor, organization, "document:upload")
        except DatabaseError:
            raise
        except Exception:
            raise CommandError("OCR_SCOPE_OR_ACTOR_DENIED") from None
        return actor, organization

    def _ready(self, value):
        if not value:
            return
        path = Path(value)
        root = Path(getattr(settings, "PRACE_RUNTIME_ROOT", ""))
        # The lifecycle helper owns this single private handshake location.
        if not root.is_absolute() or path != root / ".ocr-worker.ready" or path.is_symlink():
            raise CommandError("OCR_READY_PATH_INVALID")
        if root.resolve() != root or path.exists():
            raise CommandError("OCR_READY_PATH_INVALID")
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix=".ocr-ready-", dir=root)
            with os.fdopen(fd, "w") as stream:
                stream.write("ready\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def handle(self, *args, **options):
        interval = options["poll_interval"]
        if options["max_runs"] < 1 or not math.isfinite(interval) or interval <= 0:
            raise CommandError("OCR_WORKER_OPTIONS_INVALID")
        try:
            self._scope(options)
            self._ready(options.get("ready_file"))
        except CommandError:
            raise
        except Exception:
            raise CommandError("OCR_WORKER_STARTUP_FAILED") from None
        try:
            while True:
                try:
                    close_old_connections()
                    # Reload actor and membership authorization on every batch.
                    actor, organization = self._scope(options)
                    results = process_pending(actor, organization, max_runs=options["max_runs"], run_id=options.get("run_id"))
                    if results or not options["loop"]:
                        self.stdout.write(json.dumps(results, sort_keys=True))
                        self.stdout.flush()
                except CommandError:
                    raise
                except Exception:
                    # Never include OCR values, database DSNs or raw exceptions.
                    if not options["loop"]:
                        raise CommandError("OCR_WORKER_BATCH_FAILED") from None
                    self.stderr.write("OCR_WORKER_BATCH_FAILED; durable work remains retryable")
                    self.stderr.flush()
                finally:
                    connections.close_all()
                if not options["loop"]:
                    return
                time.sleep(interval)
        finally:
            connections.close_all()
