#!/usr/bin/env python3
"""Provision an individual synthetic operator + organization + MFA.

This script is the canonical entrypoint for Jan's first rehearsal
login. It is invoked by ``scripts/rehearse_synthetic_site.sh
provision`` with the supervised-synthetic settings module loaded.

What it does, idempotently:

1. Creates a synthetic-only organization with the operator as
   active member. Idempotent on the organization's natural key
   (label + country). Never creates a second organization with
   the same label.
2. Creates a synthetic-only user (operator) with the supplied
   email and password. Idempotent on the email. Never re-uses a
   username. Membership is made active.
3. Enrolls TOTP MFA for the operator. The TOTP secret is written
   to ``$RUNTIME_ROOT/operator.json`` (mode 0600) outside the
   repository and outside ordinary logs. The operator.json file
   is the only place the secret is persisted; it is rotated on
   each invocation.

The script refuses to run unless the supervised-synthetic
settings module is loaded (``M2_SYNTHETIC_ONLY=True``) and the
runtime root is operator-owned mode 0700. The output
``operator.json`` and ``organization.json`` are created mode 0600
so the password and TOTP secret are private.

A 6-digit TOTP code for "now" is included in operator.json for
automated tests. The URI (``otpauth://...``) is also included so
any TOTP authenticator app can complete the same enrollment.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import json
import os
import re
import secrets
import struct
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SAFETY = REPO_ROOT / "portal" / "release1a" / "runtime_safety.py"


def _now_unix() -> int:
    return int(time.time())


def _hotp_token(secret: bytes, counter: int, digits: int = 6) -> str:
    """RFC 6238 TOTP code for the given time-step counter."""
    msg = struct.pack(">Q", counter)
    digest = hmac.new(secret, msg, "sha1").digest()
    offset = digest[-1] & 0x0F
    code = (
        (digest[offset] & 0x7F) << 24
        | (digest[offset + 1] & 0xFF) << 16
        | (digest[offset + 2] & 0xFF) << 8
        | (digest[offset + 3] & 0xFF)
    )
    return str(code % (10 ** digits)).zfill(digits)


def _current_totp(secret: bytes, at_unix: int | None = None,
                  period: int = 30) -> str:
    counter = (at_unix if at_unix is not None else _now_unix()) // period
    return _hotp_token(secret, counter)


def _atomic_write(path: Path, body: bytes, mode: int) -> None:
    """Write body to path atomically with the given mode (after close)."""
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        os.chmod(path, mode)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True,
                        help="Confinined runtime root (operator-owned 0700)")
    parser.add_argument("--email", default="jan-operator@example.invalid",
                        help="Operator email (default: synthetic-only)")
    parser.add_argument("--password", default=None,
                        help="Operator password (default: random, "
                             "persisted in operator.json)")
    parser.add_argument("--organization", default="Jan Test Org",
                        help="Organization label (default: 'Jan Test Org')")
    args = parser.parse_args()

    # The supervised-synthetic settings module must already be loaded
    # (the rehearsal script exports DJANGO_SETTINGS_MODULE). We verify
    # it here too so the script fails closed if called directly.
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if settings_module != "portal.settings_supervised_synthetic":
        print(
            f"FAIL: DJANGO_SETTINGS_MODULE must be "
            f"portal.settings_supervised_synthetic (got {settings_module!r})",
            file=sys.stderr,
        )
        return 1

    # Refuse to run if the runtime root is not a confined layout. We
    # reuse the canonical helpers so this script never invents its
    # own confinement contract.
    sys.path.insert(0, str(REPO_ROOT))
    from portal.release1a.runtime_safety import confined_root, no_symlinks  # noqa: E402
    confined_root(str(args.runtime_root))
    # Sidecar/state files must not be pre-existing symlinks.
    for sibling in (
        args.runtime_root / "operator.json",
        args.runtime_root / "organization.json",
    ):
        no_symlinks(sibling)

    import django  # noqa: E402
    django.setup()
    from django.conf import settings  # noqa: E402
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        print("FAIL: M2_SYNTHETIC_ONLY is not True", file=sys.stderr)
        return 1
    if not getattr(settings, "PRACE_SUPERVISED", False):
        print("FAIL: PRACE_SUPERVISED is not True", file=sys.stderr)
        return 1

    from django.contrib.auth import get_user_model  # noqa: E402
    from portal.release1a.models import (  # noqa: E402
        Organization, Membership, AuditEvent,
    )
    from allauth.mfa.models import Authenticator  # noqa: E402
    from allauth.mfa.utils import encrypt as allauth_encrypt  # noqa: E402

    User = get_user_model()
    org_label = args.organization
    # Idempotent organization lookup on natural key (label). The
    # synthetic-only posture is enforced at the settings module
    # (M2_SYNTHETIC_ONLY=True); the database does not store a
    # per-organization is_real_data flag. A pre-existing organization
    # with the same label is reused.
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", org_label).strip("-").lower()[:50] or "synthetic-org"
    org, _created = Organization.objects.get_or_create(
        label=org_label, defaults={"key": slug},
    )

    email = args.email.lower().strip()
    username = email.split("@", 1)[0]
    password = args.password or secrets.token_urlsafe(24)
    user, user_created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )
    if not user_created:
        # Refresh mutable fields without changing the password if it
        # was previously set by the operator. We never read or echo
        # the existing password.
        user.is_active = True
        user.save(update_fields=["is_active"])
    # Always set the password to the value supplied. This is
    # provisioning, not a rotate-on-mismatch check; the operator is
    # the only consumer and it reads operator.json for the password.
    user.set_password(password)
    user.save(update_fields=["password"])

    Membership.objects.update_or_create(
        user=user, organization=org, role="operator",
        defaults={"active": True},
    )

    # TOTP enrollment. Generate a fresh secret on every run so the
    # script is fully idempotent and the test environment is
    # reproducible. allauth encrypts the secret using its adapter
    # (keyed by SECRET_KEY); the encrypted blob is what we persist
    # in the database. The plain-text secret is persisted only to
    # operator.json (mode 0600) under the runtime root.
    totp_secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).delete()
    Authenticator.objects.create(
        user=user,
        type=Authenticator.Type.TOTP,
        data={"secret": allauth_encrypt(totp_secret)},
    )
    totp_code_now = _current_totp(base64.b32decode(totp_secret + "=" * (-len(totp_secret) % 8)))
    issuer = "Prace-v-Nemecku"
    otpauth_uri = (
        f"otpauth://totp/{issuer}:{username}?secret={totp_secret}&issuer={issuer}"
    )

    AuditEvent.objects.create(
        organization=org,
        actor_ref=f"user:{user.pk}",
        event_type="provision.synthetic_operator",
        object_ref=f"organization:{org.pk}",
        outcome="success",
    )

    org_payload = {
        "id": org.pk,
        "key": org.key,
        "label": org.label,
        "is_real_data": False,
        "settings_module": settings_module,
        "created_at": _now_unix(),
    }
    operator_payload = {
        "id": user.pk,
        "email": user.email,
        "username": user.username,
        "password": password,
        "organization_id": org.pk,
        "mfa": {
            "type": "totp",
            "secret": totp_secret,
            "otpauth_uri": otpauth_uri,
            "current_code": totp_code_now,
            "period_seconds": 30,
        },
        "credentials_location": str(args.runtime_root / "operator.json"),
        "issued_at": _now_unix(),
    }

    _atomic_write(
        args.runtime_root / "organization.json",
        json.dumps(org_payload, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        mode=0o600,
    )
    _atomic_write(
        args.runtime_root / "operator.json",
        json.dumps(operator_payload, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        mode=0o600,
    )

    # Enforce private file modes on the database and any other
    # operator-owned state. Django's SQLite opener uses 0644 by
    # default unless umask is restrictive; we chmod explicitly so
    # the contract is honoured under any incoming umask.
    db_path = args.runtime_root / "db.sqlite3"
    if db_path.exists() and not db_path.is_symlink():
        os.chmod(db_path, 0o600)

    print(f"organization: id={org.pk} label={org.label}")
    print(f"operator: id={user.pk} email={user.email}")
    print(f"credentials: {args.runtime_root / 'operator.json'} (mode 0600)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
