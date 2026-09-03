"""
portal/release1a/signals.py

Connects Django and allauth authentication signals to the security audit service.

Design:
- Login success is recorded ONLY when allauth MFA's authenticator_used signal fires
  (i.e., TOTP was successfully verified after MFA challenge). The initial password
  login (before MFA) is NOT recorded as a successful portal login.
- MFA failure (wrong TOTP code) is recorded via authentication_failed signal.
- Password failure is recorded via Django's user_login_failed signal.
- One denial event per request is enforced via a request attribute flag.
- Org resolution is fail-closed: if the user does not have exactly one active
  membership, the org is left unset (no invented org ID).
- Signal connections use dispatch_uid to prevent duplicate registration during
  test initialization and Django autoreload.
"""

from django.contrib.auth.signals import user_login_failed
from allauth.mfa.signals import authenticator_added, authenticator_used, authentication_failed

from . import security_audit
from .models import Membership

_LOGIN_AUDIT_FLAG = "_login_audit_recorded"


def _get_org_from_session(user):
    """
    Resolve org from user's active session membership if uniquely determinable.

    Fail-closed: returns None if zero or more than one active membership exists.
    Never invents an org ID.
    """
    memberships = list(
        Membership.objects.filter(user=user, active=True)
        .select_related("organization")
        .values_list("organization_id", flat=True)
    )
    if len(memberships) == 1:
        from .models import Organization
        return Organization.objects.get(pk=memberships[0])
    return None


def _record_authentication_mfa(request, user, authenticator, **kwargs):
    """
    Add 'mfa' to account_authentication_methods in the current session.

    This is needed because allauth's TOTP activation flow does not automatically
    update the session's authentication-methods list. Without this, a subsequent
    call to allauth's stage controller (e.g., during a reauthentication flow
    within the same session) would not recognise that MFA has been enrolled.

    This only affects the CURRENT session. After logout the session is flushed;
    subsequent logins are governed by the Authenticator record in the DB, not
    by anything this handler writes.
    """
    if not hasattr(request, "session") or request.session is None:
        return
    from allauth.account.internal.flows.login import record_authentication
    record_authentication(
        request,
        user,
        method="mfa",
        type=getattr(authenticator, "type", None),
        id=getattr(authenticator, "id", None),
    )


def on_authenticator_used(sender, request, user, authenticator, **kwargs):
    """Record successful MFA verification (TOTP or backup codes). One event per request."""
    if getattr(request, _LOGIN_AUDIT_FLAG, False):
        return
    request._login_audit_recorded = True
    org = _get_org_from_session(user)
    security_audit.record_login_success(request, user, organization=org)


def on_mfa_authentication_failed(sender, request, user, authenticator, **kwargs):
    """Record failed MFA challenge attempt (wrong TOTP code)."""
    security_audit.record_login_failure(
        request,
        outcome="denied",
        reason_code="mfa_failed",
    )


def on_password_login_failed(sender, credentials, request, **kwargs):
    """Record failed password login attempt.

    credentials may contain 'username' or 'email' — these are deliberately NOT
    logged. Only the fact of a failed attempt is recorded.
    """
    security_audit.record_login_failure(
        request,
        outcome="denied",
        reason_code="password_failed",
    )


authenticator_added.connect(
    _record_authentication_mfa,
    dispatch_uid="release1a_on_authenticator_added",
)
authenticator_used.connect(
    on_authenticator_used,
    dispatch_uid="release1a_on_authenticator_used",
)
authentication_failed.connect(
    on_mfa_authentication_failed,
    dispatch_uid="release1a_on_mfa_authentication_failed",
)
user_login_failed.connect(
    on_password_login_failed,
    dispatch_uid="release1a_on_password_login_failed",
)
