#!/usr/bin/env python3
"""Reset one active synthetic reviewer password and print it once locally.

This command is intentionally limited to the synthetic review settings. It
never writes credentials to a tracked file, logs, or database field other than
the normal Django password hash.
"""

import argparse
import os
import secrets
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--login",
        help="Existing synthetic reviewer username or email address.",
    )
    target.add_argument(
        "--list",
        action="store_true",
        help="List active synthetic reviewer usernames without showing passwords or emails.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required acknowledgement that this invalidates the prior password.",
    )
    parser.add_argument(
        "--show-totp-code",
        action="store_true",
        help="Also print the current synthetic TOTP code; use only on the local operator terminal.",
    )
    args = parser.parse_args()

    if not args.list and not args.confirm:
        parser.error("pass --confirm to reset a password")
    if args.list and args.show_totp_code:
        parser.error("--show-totp-code requires --login")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal.settings_synthetic_review")

    import django

    django.setup()

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from allauth.mfa.models import Authenticator
    import pyotp
    from portal.release1a.models import AuthAuditEvent, Membership

    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise RuntimeError("refusing to run outside the synthetic review environment")

    user_model = get_user_model()
    if args.list:
        user_ids = (
            Membership.objects.filter(active=True)
            .values_list("user_id", flat=True)
            .distinct()
        )
        users = user_model.objects.filter(id__in=user_ids, is_active=True).order_by(
            "username"
        )
        for user in users:
            print(user.username)
        return 0

    users = list(
        user_model.objects.filter(Q(username=args.login) | Q(email__iexact=args.login))[
            :2
        ]
    )
    if len(users) != 1:
        raise RuntimeError("login did not resolve to exactly one account")

    user = users[0]
    if not user.is_active:
        raise RuntimeError(
            "reviewer is inactive; use the invitation activation flow instead"
        )
    if Membership.objects.filter(user=user, active=True).count() != 1:
        raise RuntimeError(
            "reviewer must have exactly one active organization membership"
        )

    temporary_pwd = secrets.token_urlsafe(20)
    user.set_password(temporary_pwd)
    user.save(update_fields=["password"])
    AuthAuditEvent.objects.create(
        event_type="authentication.password_reset_by_operator",
        outcome="success",
        actor_ref="actor:operator",
        object_ref=f"actor:user:{user.pk}",
        reason_code="operator_reset",
    )

    print("Synthetic reviewer password reset successfully.")
    print(f"Login: {user.username}")
    print(f"Temporary password: {temporary_pwd}")
    if args.show_totp_code:
        try:
            authenticator = Authenticator.objects.get(
                user=user, type=Authenticator.Type.TOTP
            )
            totp = pyotp.TOTP(authenticator.data["secret"])
        except (Authenticator.DoesNotExist, KeyError) as exc:
            raise RuntimeError("reviewer has no usable TOTP authenticator") from exc
        # Do not hand an operator a code that is about to expire while they are
        # switching back to the browser. At most one 30-second period is waited.
        seconds_remaining = totp.interval - (time.time() % totp.interval)
        if seconds_remaining < 25:
            time.sleep(seconds_remaining + 0.2)
        totp_code = totp.now()
        seconds_remaining = max(1, int(totp.interval - (time.time() % totp.interval)))
        print(f"Current TOTP code: {totp_code}")
        print(f"Enter it now; it remains valid for about {seconds_remaining} seconds.")
    print("Use it once in the browser, then store or replace it securely.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
