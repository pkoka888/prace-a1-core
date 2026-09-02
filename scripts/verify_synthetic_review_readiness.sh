#!/usr/bin/env bash
# verify_synthetic_review_readiness.sh
# Runs automated readiness checks for the synthetic review environment.
# Writes deterministic verdict to runtime/portal/synthetic-review/readiness.json.
# Does NOT run pytest inside a Django request — runs as a standalone script.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REVIEW_DIR="$REPO_ROOT/runtime/portal/synthetic-review"
READINESS_FILE="${REVIEW_DIR}/readiness.json"
PYTEST_BIN="$REPO_ROOT/venv/bin/python"
PYTEST="$PYTEST_BIN -m pytest"

mkdir -p "$REVIEW_DIR"
cd "$REPO_ROOT"

# Gather build identity — must match _get_build_id() in views.py
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
GIT_DIRTY="$(git status --porcelain 2>/dev/null | grep -v '^??' | wc -l | tr -d ' ')"
GIT_CLEAN=$([ "$GIT_DIRTY" -eq 0 ] && echo "true" || echo "false")

PYTEST_VERSION=$($PYTEST --version 2>/dev/null | head -1 || echo "not installed")

# Build ID: sha256(commit:dirty_flag:settings_module:python_version)[:16]
# Must match _get_build_id() in portal/release1a/views.py
APP_BUILD_ID=$(DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review $PYTEST_BIN -c "
import hashlib, sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_synthetic_review'
import django; django.setup()
from django.conf import settings
commit = '$GIT_COMMIT'
dirty = 'dirty' if $GIT_DIRTY -gt 0 else 'clean'
build_id = hashlib.sha256(
    f'{commit}:{dirty}:{settings.SETTINGS_MODULE}:{sys.version}'.encode()
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

# Check: axe script exists
run_check "axe_script_exists" "[ -f '$REPO_ROOT/scripts/axe_check.sh' ]"

# Check: axe requirements installed (playwright)
run_check "axe_deps_installed" "
    $PYTEST_BIN -c 'import playwright' 2>/dev/null
"

VERDICT="passed"
if [ $FAILED -gt 0 ]; then
    VERDICT="failed"
fi

SUMMARY="$PASSED passed, $FAILED failed"

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
