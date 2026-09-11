#!/usr/bin/env python3
"""Provision an individual synthetic operator + organization + MFA.

This script is the canonical entrypoint for Jan's first rehearsal
login. It is invoked by ``scripts/rehearse_synthetic_site.sh
provision`` with the supervised-synthetic settings module loaded.

What it does, idempotently by default:

1. Creates a synthetic-only organization with the operator as
   active member. Idempotent on the organization's natural key
   (label). Never creates a second organization with the same
   label.
2. Creates or reuses a synthetic-only user (operator) with the
   supplied email and an MFA-enrolled TOTP authenticator. The
   password and TOTP secret are preserved across ordinary reruns
   so a real browser session can keep its logged-in identity.
   ``--rotate-credentials`` is the explicit way to mint a new
   password and TOTP secret (it overwrites ``operator.json``).
3. Ensures the operator has a primary, verified ``EmailAddress``
   record so allauth's mandatory email-verification check does
   not block the rehearsal login. The EmailAddress row is created
   once and reused; ``--rotate-credentials`` does not change it.
4. Creates the ``Membership`` row with role ``jan_planner`` — the
   role Jan's workflow actually exercises (worker:create,
   assignment:create, a1:prepare, document:upload, document:confirm).
   No additional role is added.

The script refuses to run unless the supervised-synthetic
settings module is loaded (``M2_SYNTHETIC_ONLY=True``), the
runtime root is operator-owned mode 0700, and the supplied
``--runtime-root`` agrees with the ``PRACE_RUNTIME_ROOT`` the
supervised settings module is using (so the credentials land in
the same database the running gunicorn will query).

The output ``operator.json`` (mode 0600) carries the current
password and TOTP secret for the operator. ``organization.json``
(mode 0600) carries the operator-bound organization. Both live
inside the gitignored runtime root, never the repository, and
the script never prints the password outside a deliberate read
of that file.

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

OPERATOR_ROLES = ("jan_planner",)


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


def _require_existing_operator_payload(path: Path) -> dict:
    """Return the parsed operator.json payload from a previous run.

    The file is mode 0600; reading it is the only way to recover the
    password of a previously provisioned operator without resetting it.
    Missing or unreadable file is a hard error when not rotating.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found; rerun with --rotate-credentials to mint a "
            f"new password and TOTP secret for an existing operator"
        )
    if path.is_symlink():
        raise ValueError(f"{path} must not be a symlink")
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise PermissionError(f"{path} mode {oct(mode)} is not operator-only")
    try:
        payload = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise ValueError(f"{path} is unreadable: {exc}") from exc
    for required in ("password", "mfa", "email"):
        if required not in payload:
            raise ValueError(f"{path} missing required field: {required}")
    if "secret" not in payload["mfa"]:
        raise ValueError(f"{path}.mfa.secret is required for replay")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True,
                        help="Confined runtime root (operator-owned 0700)")
    parser.add_argument("--email", default="jan-operator@example.invalid",
                        help="Operator email (default: synthetic-only)")
    parser.add_argument("--password", default=None,
                        help="Operator password (default: random, "
                             "persisted in operator.json). Only used on a "
                             "fresh user or with --rotate-credentials.")
    parser.add_argument("--organization", default="Jan Test Org",
                        help="Organization label (default: 'Jan Test Org')")
    parser.add_argument("--rotate-credentials", action="store_true",
                        help="Mint a new password and TOTP secret, replacing "
                             "the existing operator.json. Use only when an "
                             "operator forgot their credentials.")
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

    # The supplied runtime root must equal the configured PRACE_RUNTIME_ROOT
    # so the credentials land in the same database the supervised settings
    # module will connect gunicorn to.
    env_root_raw = os.environ.get("PRACE_RUNTIME_ROOT", "")
    if not env_root_raw:
        print("FAIL: PRACE_RUNTIME_ROOT must be set so the script's "
              "runtime root agrees with the supervised settings module",
              file=sys.stderr)
        return 1
    env_root = Path(env_root_raw).resolve()
    arg_root = args.runtime_root.resolve()
    if env_root != arg_root:
        print(
            f"FAIL: --runtime-root {arg_root} does not match "
            f"PRACE_RUNTIME_ROOT {env_root}. Refusing to provision against "
            f"a different database than gunicorn will use.",
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
    from allauth.account.models import EmailAddress  # noqa: E402
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
    operator_json_path = args.runtime_root / "operator.json"
    rotate = bool(args.rotate_credentials or args.password)
    # First-time provisioning: no operator.json yet. Re-runs preserve
    # the prior password/TOTP unless --rotate-credentials (or a fresh
    # --password) is supplied. This keeps the rehearsal idempotent:
    # an operator already logged in keeps their session/identity across
    # ordinary reruns.
    preserved_payload = None
    if operator_json_path.is_file() and not rotate:
        try:
            preserved_payload = _require_existing_operator_payload(
                operator_json_path)
        except (FileNotFoundError, ValueError, PermissionError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        if preserved_payload["email"] != email:
            print(
                f"FAIL: operator.json records email "
                f"{preserved_payload['email']!r}, requested {email!r}. "
                f"Use --rotate-credentials or --email to match.",
                file=sys.stderr,
            )
            return 1

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

    if rotate or user_created:
        password = args.password or secrets.token_urlsafe(24)
        user.set_password(password)
        user.save(update_fields=["password"])
    else:
        # Reuse the prior password verbatim — the operator.json file
        # is the source of truth for the credential a browser will use.
        password = preserved_payload["password"]

    # Membership for Jan's workflow is jan_planner. operator lacks
    # worker:create and assignment:create; organization_admin would
    # broaden the rehearsal beyond Jan's actual capabilities.
    membership_role = OPERATOR_ROLES[0]
    Membership.objects.update_or_create(
        user=user, organization=org, role=membership_role,
        defaults={"active": True},
    )

    # Primary, verified EmailAddress — required for allauth's mandatory
    # email-verification login flow. Idempotent: reruns reuse the
    # existing verified address.
    EmailAddress.objects.update_or_create(
        user=user, email=email,
        defaults={"primary": True, "verified": True},
    )

    # TOTP enrollment. Reuse the existing secret on ordinary reruns;
    # rotate only when the operator asks. allauth encrypts the secret
    # using its adapter (keyed by SECRET_KEY); the encrypted blob is
    # what we persist in the database. The plain-text secret is
    # persisted only to operator.json (mode 0600).
    existing_auth = Authenticator.objects.filter(
        user=user, type=Authenticator.Type.TOTP).first()
    if rotate or existing_auth is None:
        totp_secret = base64.b32encode(
            secrets.token_bytes(20)).decode("ascii").rstrip("=")
        if existing_auth is not None:
            existing_auth.delete()
        Authenticator.objects.create(
            user=user,
            type=Authenticator.Type.TOTP,
            data={"secret": allauth_encrypt(totp_secret)},
        )
    else:
        # Reuse the operator.json secret — the encrypted DB secret can
        # only be decrypted with the original SECRET_KEY; rotating
        # without --rotate-credentials would silently break login.
        totp_secret = preserved_payload["mfa"]["secret"]
    totp_code_now = _current_totp(
        base64.b32decode(totp_secret + "=" * (-len(totp_secret) % 8)))
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
        "membership_role": membership_role,
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
    print(f"operator: id={user.pk} email={user.email} role={membership_role}")
    print(f"credentials: {args.runtime_root / 'operator.json'} (mode 0600)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())