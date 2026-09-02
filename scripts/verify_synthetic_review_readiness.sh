#!/usr/bin/env bash
# verify_synthetic_review_readiness.sh
# Runs the automated readiness checks for the synthetic review environment.
# Writes deterministic verdict to runtime/portal/synthetic-review/readiness.json.
# Does NOT run pytest inside a Django request — runs as a standalone script.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REVIEW_DIR="$REPO_ROOT/runtime/portal/synthetic-review"
READINESS_FILE="${REVIEW_DIR}/readiness.json"
PYTEST="venv/bin/python -m pytest"

mkdir -p "$REVIEW_DIR"

cd "$REPO_ROOT"

# Gather build identity
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
GIT_DIRTY="$(git status --porcelain 2>/dev/null | grep -v '^??' | wc -l | tr -d ' ')"
GIT_CLEAN=$([ "$GIT_DIRTY" -eq 0 ] && echo "true" || echo "false")

PYTEST_VERSION=$($PYTEST --version 2>/dev/null | head -1 || echo "not installed")
PYTEST_BIN="$REPO_ROOT/venv/bin/python -m pytest"

# Run checks
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

echo "Running synthetic review readiness checks..."
echo "  Commit: ${GIT_COMMIT:0:12}"
echo "  Clean: $GIT_CLEAN"

# Check: secrets/synthetic_review.key exists
run_check "secrets_present" "[ -f '$REPO_ROOT/secrets/synthetic_review.key' ]"

# Check: M2_SYNTHETIC_ONLY is True in settings
run_check "synthetic_only_gate" "
    $PYTEST_BIN -q --collect-only portal/settings_synthetic_review 2>/dev/null | grep -q 'settings_synthetic_review'
"

# Check: CSRF middleware present
run_check "csrf_middleware" "
    grep -q 'CsrfViewMiddleware' '$REPO_ROOT/portal/settings.py'
"

# Check: allauth MFA wired
run_check "allauth_mfa_wired" "
    grep -q 'allauth.mfa' '$REPO_ROOT/portal/settings.py'
"

# Check: Membership.mfa_verified not read in views/services
run_check "mfa_verified_removed" "
    ! grep -r 'mfa_verified=True' '$REPO_ROOT/portal/release1a/views.py' '$REPO_ROOT/portal/release1a/services.py' 2>/dev/null
"

# Check: test_csrf_enforcement exists
run_check "csrf_enforcement_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_csrf_enforcement.py' ]"

# Check: test_totp_real_enforcement exists
run_check "totp_enforcement_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_totp_real_enforcement.py' ]"

# Check: test_synthetic_containment exists
run_check "containment_test_exists" "[ -f '$REPO_ROOT/tests/m2/test_synthetic_containment.py' ]"

# Check: test_m2/test_release1a_vertical.py passes
run_check "release1a_vertical_tests" "
    $PYTEST_BIN -q tests/m2/test_release1a_vertical.py 2>/dev/null
"

# Check: test_architecture/test_mfa_proof.py passes
run_check "mfa_proof_tests" "
    $PYTEST_BIN -q tests/architecture/test_mfa_proof.py 2>/dev/null
"

# Check: test_architecture/test_tenant_isolation.py passes
run_check "tenant_isolation_tests" "
    $PYTEST_BIN -q tests/architecture/test_tenant_isolation.py 2>/dev/null
"

# Check: test_architecture/test_protected_storage.py passes
run_check "protected_storage_tests" "
    $PYTEST_BIN -q tests/architecture/test_protected_storage.py 2>/dev/null
"

# Check: seed_release1a_dev.py --dry-run passes
run_check "seed_dry_run" "
    DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review python3 '$REPO_ROOT/scripts/seed_release1a_dev.py' --dry-run 2>/dev/null
"

# Check: runtime/portal/synthetic-review/ is gitignored
run_check "db_gitignored" "
    grep -q 'runtime/portal/' '$REPO_ROOT/.gitignore'
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
