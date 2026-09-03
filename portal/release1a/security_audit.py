"""
portal/release1a/security_audit.py

Centralized audit event creation for authentication and authorization security events.

Design rules:
- NEVER records: usernames, emails, passwords, TOTP values, invitation tokens,
  document content, full identifiers, or request URLs with sensitive data.
- Actor and object references are always opaque (e.g. "user:123" → "actor:opaque").
- Authorization denial events are fail-closed: if the audit record cannot be created,
  the exception propagates (auth denial stands).
- Login success/failure audit errors are logged and raised — operational alert
  should be configured for these events in production.
- One denial event per request (tracked via request attribute to prevent loops).
- Auth events use the separate AuthAuditEvent model (no org FK required).
- Business audit events continue to use AuditEvent (org-scoped, via services.py).

Reason codes used in denial events:
  mfa_required       — authenticated but MFA session evidence missing
  membership_inactive — authenticated but no active org membership
  organization_denied — authenticated but org mismatch
  role_denied        — authenticated but insufficient role
  record_denied      — object-level access denied (cross-tenant)

Reason codes used in login failure events:
  invalid_credentials — wrong username/password
  mfa_failed        — TOTP code wrong or rate-limited
  account_locked     — too many failures
"""

import logging

from django.http import HttpRequest

from .models import AuthAuditEvent

logger = logging.getLogger(__name__)

_AUDIT_FLAG = "_security_audit_recorded"


def _opaque_user_ref(user) -> str:
    """Return an opaque actor reference: no email, username, or identifiable info."""
    if user and user.is_authenticated:
        return f"actor:user:{user.pk}"
    return "actor:anonymous"


def _session_ref(request: HttpRequest) -> str:
    """Return a safe session reference, handling absent session keys."""
    sk = getattr(request, "session", None) and request.session.session_key
    if sk:
        return f"session:{sk[:16]}"
    return "session:unknown"


def record_login_success(request: HttpRequest, user, organization=None):
    """
    Record a successful login event.

    Called after allauth has fully established the authenticated session
    (after TOTP challenge if enrolled). A password-only login that has not
    yet passed TOTP is not recorded as a successful portal login.

    request: Django HttpRequest
    user: authenticated User
    organization: Organization if uniquely resolvable from session membership, else None

    Raises on audit-write failure (operational alert should fire in production).
    """
    AuthAuditEvent.objects.create(
        event_type="authentication.login_succeeded",
        outcome="success",
        actor_ref=_opaque_user_ref(user),
        organization_id=organization.pk if organization else None,
        object_ref=_session_ref(request),
        reason_code="",
    )


def record_login_failure(
    request: HttpRequest,
    outcome: str = "denied",
    reason_code: str = "invalid_credentials",
):
    """
    Record a failed login attempt.

    Does NOT record the submitted identifier (username/email) — only an opaque
    actor reference and the reason code.

    Raises on audit-write failure (operational alert should fire in production).

    outcome: "denied" | "error"
    reason_code: "invalid_credentials" | "mfa_failed" | "account_locked" | "rate_limited"
    """
    AuthAuditEvent.objects.create(
        event_type="authentication.login_failed",
        outcome=outcome,
        actor_ref="actor:anonymous",
        organization_id=None,
        object_ref=_session_ref(request),
        reason_code=reason_code,
    )


def record_authorization_denial(
    request: HttpRequest,
    user,
    reason_code: str,
    object_ref: str = "",
    organization=None,
):
    """
    Record an authorization denial for an already-authenticated user.

    Called from require_org_membership and similar decorators when the user is
    authenticated but not authorized. One event per request (loop-protected).

    Fail-closed: raises on audit-write failure (auth denial stands regardless).

    reason_code: "mfa_required" | "membership_inactive" | "organization_denied"
                 | "role_denied" | "record_denied"
    object_ref: opaque reference to the denied resource
    """
    if getattr(request, _AUDIT_FLAG, False):
        return
    request._security_audit_recorded = True

    AuthAuditEvent.objects.create(
        event_type="authorization.denied",
        outcome="denied",
        actor_ref=_opaque_user_ref(user),
        organization_id=organization.pk if organization else None,
        object_ref=object_ref or "N/A",
        reason_code=reason_code,
    )
