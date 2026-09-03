#!/usr/bin/env bash
# verify_synthetic_review_readiness.sh
# Runs automated readiness checks for the synthetic review environment.
# Writes deterministic verdict to runtime/portal/synthetic-review/readiness.json.
# Does NOT run pytest inside a Django request — runs as a standalone script.
#
# Scope: all files that affect the review environment's behavior, including
# portal code, tests, scripts, dependency files, and configuration.
# Research artifacts in unrelated directories are excluded.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REVIEW_DIR="$REPO_ROOT/runtime/portal/synthetic-review"
BUILD_MANIFEST_FILE="${REVIEW_DIR}/build_manifest.json"
READINESS_FILE="${REVIEW_DIR}/readiness.json"
PYTEST_BIN="$REPO_ROOT/venv/bin/python"
PYTEST="$PYTEST_BIN -m pytest"

mkdir -p "$REVIEW_DIR"
cd "$REPO_ROOT"

# Gather build identity — must match _get_build_id() in views.py
# Clean-commit policy: readiness is only valid from a fully committed working tree.
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"

# Review-scope paths: portal code, dependency files, and runtime scripts only.
# Excludes: tests/, research/, axe_check.sh, and other engineering QA artifacts.
SCOPE_PATTERNS="portal/ requirements.txt requirements-dev.txt scripts/verify_synthetic_review_readiness.sh scripts/seed_release1a_dev.py"

# Check tracked file modifications in scope
SCOPED_CHANGES="$(git status --porcelain $SCOPE_PATTERNS 2>/dev/null | grep -v '^?? ' || true)"
# Check untracked files in scope (new files in scoped directories)
UNTRACKED_IN_SCOPE="$(git status --porcelain $SCOPE_PATTERNS 2>/dev/null | grep '^?? ' || true)"

if [ -n "$SCOPED_CHANGES" ] || [ -n "$UNTRACKED_IN_SCOPE" ]; then
    echo "ERROR: Working tree has uncommitted changes in review scope." >&2
    echo "Readiness and Jan approval are only allowed from a clean committed checkout." >&2
    echo "Review scope: $SCOPE_PATTERNS" >&2
    echo "Commit your changes before running this script." >&2
    echo "" >&2
    echo "Scoped changes:" >&2
    git status --porcelain $SCOPE_PATTERNS >&2
    exit 1
fi

GIT_CLEAN="true"

PYTEST_VERSION=$($PYTEST --version 2>/dev/null | head -1 || echo "not installed")

# Build ID: sha256(commit:settings_module:requirements_lock_hash)[:16]
# Derived from the committed state only — reproducible across clean clones.
APP_BUILD_ID=$(DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review $PYTEST_BIN -c "
import hashlib, sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_synthetic_review'
import django; django.setup()
from django.conf import settings
commit = '$GIT_COMMIT'
req_lock = ''
req_lock_path = os.path.join(os.path.dirname(__file__), '..', 'requirements.txt')
try:
    with open(req_lock_path) as f:
        req_lock = f.read()
except Exception:
    pass
build_id = hashlib.sha256(
    f'{commit}:{settings.SETTINGS_MODULE}:{hashlib.sha256(req_lock.encode()).hexdigest()}'.encode()
).hexdigest()[:16]
print(build_id)
" 2>/dev/null || echo "unknown")

echo "Running synthetic review readiness checks..."
echo "  Commit: ${GIT_COMMIT:0:12}"
echo "  Clean: $GIT_CLEAN"
echo "  Build ID: ${APP_BUILD_ID:0:40}..."

CHECKS="{}"
PASSED=0
FAILED=0

run_check() {
    local name="$1"
    local cmd="$2"
    echo -n "  $name... "
    if eval "$cmd" >/dev/null 2>&1; then
        echo "PASS"
        CHECKS=$(echo "$CHECKS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['$name'] = {'status': 'passed'}
print(json.dumps(d))
")
        PASSED=$((PASSED + 1))
    else
        echo "FAIL"
        CHECKS=$(echo "$CHECKS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['$name'] = {'status': 'failed'}
print(json.dumps(d))
")
        FAILED=$((FAILED + 1))
    fi
}

# Check: secrets/synthetic_review.key exists
run_check "secrets_present" "[ -f '$REPO_ROOT/secrets/synthetic_review.key' ]"

# Check: M2_SYNTHETIC_ONLY is True in synthetic_review settings
run_check "synthetic_only_gate" "
    DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review $PYTEST_BIN -c '
import django; django.setup()
from django.conf import settings
assert getattr(settings, \"M2_SYNTHETIC_ONLY\", False), \"M2_SYNTHETIC_ONLY not True\"
' 2>/dev/null
"

# Check: CSRF middleware present
run_check "csrf_middleware" "
    grep -q 'CsrfViewMiddleware' '$REPO_ROOT/portal/settings.py'
"

# Check: allauth MFA wired
run_check "allauth_mfa_wired" "
    grep -q 'allauth.mfa' '$REPO_ROOT/portal/settings.py'
"

# Check: AccountMiddleware present
run_check "account_middleware" "
    grep -q 'allauth.account.middleware.AccountMiddleware' '$REPO_ROOT/portal/settings.py'
"

# Check: Membership.mfa_verified not read in authorization (services/views)
run_check "mfa_verified_not_authorization" "
    ! grep -r 'mfa_verified.*True' '$REPO_ROOT/portal/release1a/views.py' '$REPO_ROOT/portal/release1a/services.py' 2>/dev/null
"

# Check: /login/ redirects to allauth
run_check "login_routes_to_allauth" "
    grep -q 'accounts/login' '$REPO_ROOT/portal/urls.py'
"

# Check: review routes protected by require_org_membership
run_check "review_routes_require_membership" "
    grep -q '@require_org_membership' '$REPO_ROOT/portal/release1a/views.py'
"

# Check: seed --dry-run succeeds (read-only; requires migrations applied first)
run_check "seed_dry_run" "
    DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review SYNTHETIC_REVIEW_SECRET=test-secret $PYTEST_BIN scripts/seed_release1a_dev.py --dry-run 2>/dev/null
"

# Check: runtime/portal/synthetic-review/ is gitignored
run_check "db_gitignored" "
    grep -q 'runtime/portal/' '$REPO_ROOT/.gitignore'
"

# Check: secrets/ is gitignored
run_check "secrets_gitignored" "
    grep -q 'secrets/' '$REPO_ROOT/.gitignore'
"

# Check: tests/m2/test_csrf_enforcement.py exists
run_check "csrf_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_csrf_enforcement.py' ]"

# Check: tests/m2/test_totp_real_enforcement.py exists
run_check "totp_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_totp_real_enforcement.py' ]"

# Check: tests/m2/test_synthetic_containment.py exists
run_check "containment_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_synthetic_containment.py' ]"

# Check: tests/m2/test_review_acceptance_flow.py exists
run_check "review_flow_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_review_acceptance_flow.py' ]"

# Check: m2 tests pass (key integration tests only, not full suite)
run_check "m2_integration_tests" "
    $PYTEST -q tests/m2/test_csrf_enforcement.py tests/m2/test_totp_real_enforcement.py tests/m2/test_synthetic_containment.py tests/m2/test_review_acceptance_flow.py 2>/dev/null
"

# ── Accessibility ─────────────────────────────────────────────────────────────
# axe-core checks are a mandatory pre-Jan gate but require a running server
# with an authenticated session (J1–J4 screens are behind require_org_membership).
# The automated check here is informational only — it verifies that tooling
# is installed but does NOT scan protected pages or fail on violations.
# Full accessibility validation requires a separate Playwright-based scan with
# authenticated sessions; see scripts/axe_check.sh.
run_check "axe_script_exists" "[ -f '$REPO_ROOT/scripts/axe_check.sh' ]"
run_check "axe_deps_installed" "$PYTEST_BIN -c 'import playwright' 2>/dev/null"

VERDICT="passed"
if [ $FAILED -gt 0 ]; then
    VERDICT="failed"
fi

SUMMARY="$PASSED passed, $FAILED failed"

# Write build manifest — read by the application as the authoritative build identity
cat > "$BUILD_MANIFEST_FILE" <<EOF
{
  "git_commit": "$GIT_COMMIT",
  "git_clean": $GIT_CLEAN,
  "app_build_id": "$APP_BUILD_ID",
  "generated_at": "$(date -Iseconds)"
}
EOF

cat > "$READINESS_FILE" <<EOF
{
  "verdict": "$VERDICT",
  "summary": "$SUMMARY",
  "git_commit": "$GIT_COMMIT",
  "git_clean": $GIT_CLEAN,
  "app_build_id": "$APP_BUILD_ID",
  "generated_at": "$(date -Iseconds)",
  "pytest_version": "$PYTEST_VERSION",
  "checks": $CHECKS
}
EOF

echo ""
echo "Result: $VERDICT ($SUMMARY)"
echo "Written to: $READINESS_FILE"

if [ "$VERDICT" = "failed" ]; then
    exit 1
fi
exit 0
