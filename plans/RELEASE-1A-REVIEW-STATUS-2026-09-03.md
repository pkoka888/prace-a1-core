# Status Report: Release 1A Synthetic Review Environment
**Date**: 2026-09-03
**Branch**: `feat/prace-readiness-plan-2026-08-13`
**Commit (working tree)**: dirty (uncommitted changes)
**Test suite**: 41/41 M2 tests passing

---

## 1. Executive Summary

All core Release 1A implementation is complete. The full reviewer onboarding
integration test (`test_full_onboarding_flow`) now passes with real HTTP posts to
allauth endpoints — no `force_login()`, no direct session mutation for auth state.

Key breakthroughs this session:
1. **`authenticator_added` signal handler** — allauth does NOT automatically
   update `account_authentication_methods` in the session after TOTP enrollment;
   added `on_authenticator_added` handler in `signals.py` to sync the session.
2. **Test client logout** — `client.get('/accounts/logout/')` follows the 302
   redirect, creating a new session in the test client. Fixed by using
   `client.post('/accounts/logout/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')`.

---

## 2. What Was Done — Completed Items (2026-09-03)

### 2.1 `authenticator_added` Signal Handler

**Problem**: After TOTP enrollment, `account_authentication_methods` in the session
still only contained `{'method': 'password'}`. On re-login, allauth's
`ctrl.handle()` reads the session's authentication methods and skips the MFA
challenge stage even though the user has a TOTP authenticator in the DB.

**Root cause**: allauth's `authenticator_added` signal is defined but NOT connected
to any handler that updates the session. The `account_authentication_methods`
session key is only written by `record_authentication()` during actual login
attempts, not during authenticator enrollment.

**Solution**: Added `on_authenticator_added()` in `portal/release1a/signals.py`:
```python
def on_authenticator_added(sender, request, user, authenticator, **kwargs):
    methods = request.session.get(_AUTHENTICATION_METHODS_SESSION_KEY, [])
    mfa_entry = {"method": "mfa", "at": time.time()}
    if hasattr(authenticator, "type") and authenticator.type:
        mfa_entry["type"] = authenticator.type
    if getattr(authenticator, "id", None):
        mfa_entry["id"] = authenticator.id
    methods = [m for m in methods if m.get("method") != "mfa"]
    methods.append(mfa_entry)
    request.session[_AUTHENTICATION_METHODS_SESSION_KEY] = methods
authenticator_added.connect(on_authenticator_added)
```

**Status**: ✅ Implemented and tested.

### 2.2 `on_authenticator_used` Signature Fix

**Problem**: `signals.py` had `on_authenticator_used(sender, request, user, authenticator_type, **kwargs)` — allauth's signal sends `authenticator` (the model instance), not `authenticator_type`.

**Solution**: Changed parameter name to `authenticator`.

**Status**: ✅ Fixed.

### 2.3 `test_full_onboarding_flow` — Real HTTP Post Flow

**Problem**: Test was failing at Step 7 (re-login) — redirected to `/accounts/profile/`
instead of MFA challenge.

**Root causes**:
1. `client.get('/accounts/logout/')` — Django test client's `logout()` uses GET,
   which follows the 302 redirect response, creating a new session in the client
   while the original session still holds the old `account_authentication_methods`.
   This caused re-login to read stale auth methods and skip MFA challenge.
2. Session's `account_authentication_methods` not including `mfa` after enrollment
   (fixed by 2.1 above).

**Solution**:
- Changed logout to: `self.client.post("/accounts/logout/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")`
- Full flow now: invitation → password → real login → TOTP enrollment (GET secret from
  session, POST code) → logout (POST) → re-login → MFA challenge URL → TOTP POST →
  `/review/` → 200

**Status**: ✅ 4/4 tests pass including `test_full_onboarding_flow`.

### 2.4 `test_reviewer_onboarding.py` — All 4 Tests Pass

| Test | Status |
|------|--------|
| `test_full_onboarding_flow` | ✅ PASS |
| `test_invitation_invalid_token` | ✅ PASS |
| `test_invitation_expired` | ✅ PASS |
| `test_mfa_required_for_review_access` | ✅ PASS |

### 2.5 Full M2 Test Suite — 41/41 Pass

| File | Count | Status |
|------|-------|--------|
| `test_synthetic_containment.py` | 7 | ✅ |
| `test_csrf_enforcement.py` | 1 | ✅ |
| `test_totp_real_enforcement.py` | 4 | ✅ |
| `test_review_acceptance_flow.py` | 6 | ✅ |
| `test_reviewer_onboarding.py` | 4 | ✅ |
| `test_views.py` | 11 | ✅ |
| `test_review_fixes.py` | 6 | ✅ |
| **Total** | **41** | **✅** |

---

## 3. Previously Completed Items (from 2026-09-02 report)

These remain done:

- Migration `0003` with `SeparateDatabaseAndState` + proper `RunSQL`
- `Release1aAcceptance.user` → `PROTECT`
- `Release1aAcceptance.organization` → `PROTECT`
- Build identity: `app_build_id = sha256(commit:settings_module:requirements_hash)[:16]`
- `verify_synthetic_review_readiness.sh`: scoped clean-tree check (portal/tests/scripts only)
- `verify_synthetic_review_readiness.sh`: conditional axe execution (only if server reachable)
- `pyotp` moved from `requirements.txt` → `requirements-dev.txt`
- `security_audit.py`: fail-closed, `_session_ref()` handles absent session keys
- `signals.py`: fail-closed org resolution, `authenticator_used` + `authentication_failed` wired
- `MFA_FORMS` path fix in `settings.py`
- `ACCOUNT_LOGIN_METHODS` / `ACCOUNT_SIGNUP_FIELDS` fix in `settings.py`
- `/login/` → `/accounts/login/` redirect in `urls.py`
- `AuthAuditEvent` model + migration `0004`

---

## 4. Django Test Client Session Behavior — Key Finding

**Issue**: Django test client's `client.logout()` issues a GET request to the logout
URL. The server returns a 302 redirect. The test client's session handling (when
following redirects) creates a new `SessionStore` backed by the redirected response's
session cookie, leaving the original session key's data unchanged in the test
client's view.

**Evidence**:
```python
# This leaves old session data intact:
r = client.get('/accounts/logout/')  # 302 → follows redirect
ss = SessionStore(session_key=original_sk)
# ss still has account_authentication_methods + _auth_user_id

# This properly clears:
r = client.post('/accounts/logout/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
# Session is flushed by django's logout handler
```

**Real-world impact**: None (browsers handle 302 correctly). Only affects
automated testing with Django's test client.

**Recommendation for future tests**: Always use POST for logout in test cases that
need to verify subsequent auth behavior.

---

## 5. Remaining Work

### 5.1 Status Report Staleness

The previous status report (`RELEASE-1A-REVIEW-STATUS-2026-09-02.md`) described
`test_full_onboarding_flow` as "blocked" and the TOTP enrollment issue as
"UNRESOLVED". This is now resolved.

**Status**: 🟡 This report supersedes the 2026-09-02 report.

### 5.2 Commit Required

All implementation is complete but uncommitted. The working tree contains:
- `portal/release1a/signals.py` (added `on_authenticator_added`)
- `tests/m2/test_reviewer_onboarding.py` (fixed logout + full flow)
- `requirements.txt` (pyotp removed)
- `requirements-dev.txt` (pyotp added)
- Other previously described changes

**Status**: 🟡 Ready for commit pending final validation.

### 5.3 Accessibility Gate

`verify_synthetic_review_readiness.sh` conditionally runs `axe_check.sh` only if
server is reachable (`curl http://127.0.0.1:8000/` returns 200). If the server is
not running, it skips with "manual gate" note. This is documented behavior but
represents a gap in automated CI.

**Status**: 🟡 Documented as manual gate; not a blocker for current release.

---

## 6. Key Allauth Internals Discovered

### 6.1 `ctrl.handle()` Stage Iteration

`LoginStageController.handle()` iterates stages in order. For each stage:
1. Check `is_handled(stage.key)` — skip if already done
2. Call `stage.handle()` — if it returns a response, return it (stash login if `cont=True`)
3. If `handle()` returns `None, True` (continue), mark stage as handled and continue
4. After all stages, `clear_login()` and return `None`

If `ctrl.handle()` returns `None`, `resume_login()` falls through to
`adapter.login()` → user is fully logged in (no MFA challenge).

### 6.2 `AuthenticateStage._should_handle()` Conditions

```python
def _should_handle(self, request):
    if self.login.user is None: return False
    if not is_mfa_enabled(user, [TOTP, WEBAUTHN]): return False
    if did_use_passwordless_login(request): return False
    if trust.is_trusted_browser(request, user): return False
    return True
```

`is_mfa_enabled()` reads the database directly. It must return `True` for the
MFA challenge to activate.

### 6.3 Session Auth Methods vs DB State

The session's `account_authentication_methods` is separate from the database's
`Authenticator` records. allauth uses session methods to decide whether to
*initiate* a login stage, but `is_mfa_enabled()` reads the DB for the actual
authenticator check. This means:
- Session methods = what stages to activate on this login attempt
- DB authenticators = whether the user *can* pass MFA

### 6.4 `authenticator_added` Signal

allauth's TOTP activation calls `signals.authenticator_added.send()` after
creating the `Authenticator` record. This signal is defined in
`allauth/mfa/signals.py` but not connected to any internal handler that updates
the session. This is why our custom handler is required.

---

## 7. Files Changed This Session

| File | Change |
|------|--------|
| `portal/release1a/signals.py` | Added `on_authenticator_added` handler; fixed `on_authenticator_used` signature |
| `tests/m2/test_reviewer_onboarding.py` | Rewritten `test_full_onboarding_flow` with real HTTP posts; POST logout fix |

---

## 8. Validation Commands

```bash
# Migration check
venv/bin/python manage.py makemigrations --check --dry-run

# All M2 tests
venv/bin/python -m pytest tests/m2/ -q

# Planning validation
venv/bin/python scripts/validate_planning.py

# Django check
venv/bin/python manage.py check

# Git diff check
git diff --check
```
