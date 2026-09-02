"""
activate_reviewer management command.

Creates a one-time invitation URL for a seeded reviewer account.
The reviewer visits the URL to set their password and activate their account.
The URL is valid for 24 hours and single-use.

Usage:
    python manage.py activate_reviewer --email pavel-reviewer@example.invalid

The printed URL is valid for 24 hours. Operator copy-pastes it into a browser
on the review server (via SSH tunnel or direct access to 127.0.0.1:8000).
"""
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()

INVITATIONS_DIR = Path(
    os.environ.get(
        "REVIEW_INVITATIONS_DIR",
        "/var/www/prace-v-nemecku.tvoje.info/runtime/portal/synthetic-review/invitations",
    )
)


class Command(BaseCommand):
    help = "Generate a one-time invitation URL for a seeded reviewer account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Email address of the reviewer account to activate.",
        )
        parser.add_argument(
            "--expires-hours",
            type=int,
            default=24,
            help="Hours until the invitation expires. Default: 24.",
        )
        parser.add_argument(
            "--no-random-password",
            action="store_true",
            help="Skip generating and printing a suggested random password.",
        )

    def handle(self, *args, **options):
        email = options["email"]
        expires_hours = options["expires_hours"]
        no_random_password = options["no_random_password"]

        INVITATIONS_DIR.mkdir(parents=True, exist_ok=True)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"User with email {email!r} does not exist.")

        if user.is_active:
            self.stdout.write(
                self.style.WARNING(f"User {email!r} is already active. No invitation needed.")
            )
            return

        token = str(uuid.uuid4())
        expires_at = int(time.time()) + (expires_hours * 3600)

        payload = {
            "email": email,
            "user_pk": user.pk,
            "created_at": int(time.time()),
            "expires_at": expires_at,
            "used": False,
        }

        token_file = INVITATIONS_DIR / f"{token}.json"
        token_file.write_text(json.dumps(payload, indent=2))
        token_file.chmod(0o600)

        base_url = os.environ.get(
            "REVIEW_BASE_URL",
            "http://127.0.0.1:8000",
        )
        invitation_url = f"{base_url}/accounts/activate/{token}/"

        self.stdout.write(self.style.SUCCESS(f"\nInvitation for: {email}"))
        self.stdout.write(f"URL (valid {expires_hours}h, single-use):\n")
        self.stdout.write(f"  {invitation_url}\n")
        self.stdout.write(
            f"\nThe reviewer visits this URL to set their password and activate TOTP enrollment."
        )
        if not no_random_password:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits
            suggested = "".join(secrets.choice(alphabet) for _ in range(16))
            self.stdout.write(f"\nSuggested initial password (change after first login):\n  {suggested}")
        self.stdout.write(f"\nToken file: {token_file}")
        self.stdout.write(
            self.style.WARNING(
                "\nKeep this URL private. It grants account activation access."
            )
        )
