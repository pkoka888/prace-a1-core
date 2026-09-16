#!/usr/bin/env bash
# check_readiness.sh
# Readiness probe for the s62 delivery gaps (G-1..G-4, D-1, static files).
# Produces a pass/fail verdict per gap with actionable next steps.
# Never prints secret values; only metadata (length, presence, hash prefix).
#
# Exit codes:
#   0 - all checks pass
#   1 - one or more checks fail
#   2 - usage / environment error
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
PASSED=0

die() { echo "ERROR: $*" >&2; exit 2; }

# ---------------------------------------------------------------------------
# Helper: bounded rg scan (no networkidle in automation code)
# ---------------------------------------------------------------------------
check_no_networkidle() {
    echo -n "D-1  no networkidle in automation code: "
    if ! command -v rg >/dev/null 2>&1; then
        echo "SKIP (rg not installed)"
        return 0
    fi
    local hits
    hits=$(rg -n \
        'wait_until\s*=\s*"networkidle"|wait_for_load_state\s*\(\s*"networkidle"|waitForLoadState\s*\(\s*"networkidle"' \
        tests/_rehearse_workflow_browser.py \
        tests/document_web/ \
        scripts/axe_check.sh \
        scripts/smoke_synthetic_review_ui.mjs \
        scripts/playwright_smoke.py \
        2>/dev/null || true)
    if [ -n "$hits" ]; then
        echo "FAIL"
        echo "  Offending matches:" >&2
        echo "$hits" >&2
        FAILED=$((FAILED + 1))
        return 0
    fi
    echo "PASS"
    PASSED=$((PASSED + 1))
}

# ---------------------------------------------------------------------------
# Helper: systemd unit status
# ---------------------------------------------------------------------------
check_unit_status() {
    echo -n "G-2  gunicorn unit status: "
    local status
    status=$(systemctl is-active prace-v-nemecku-gunicorn.service 2>/dev/null || true)
    case "$status" in
        active)
            echo "PASS ($status)"
            PASSED=$((PASSED + 1))
            ;;
        *)
            echo "FAIL ($status)"
            FAILED=$((FAILED + 1))
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Helper: nginx alias vs STATIC_ROOT
# ---------------------------------------------------------------------------
check_nginx_alias() {
    echo -n "G-3  nginx /static/ alias: "
    local nginx_conf="/etc/nginx/sites-enabled/prace-v-nemecku.expc.cz.conf"
    if [ ! -r "$nginx_conf" ]; then
        echo "SKIP (nginx conf not readable)"
        return 0
    fi
    local expected_alias="/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/"
    if grep -qF "alias $expected_alias" "$nginx_conf"; then
        echo "PASS (points to STATIC_ROOT)"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL"
        echo "  Expected alias: $expected_alias" >&2
        echo "  Actual:" >&2
        grep -A1 'location /static/' "$nginx_conf" >&2 || true
        FAILED=$((FAILED + 1))
    fi
}

# ---------------------------------------------------------------------------
# Helper: static files present at STATIC_ROOT
# ---------------------------------------------------------------------------
check_static_files() {
    echo -n "G-3  static files at STATIC_ROOT: "
    local static_dir="/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/portal"
    # Runtime dir is owned by prace-synthetic with 0700; need sudo for access
    if ! sudo test -d "$static_dir"; then
        echo "FAIL (directory missing or inaccessible)"
        FAILED=$((FAILED + 1))
        return 0
    fi
    local js_count css_count
    js_count=$(sudo find "$static_dir" -maxdepth 1 -name '*.js' 2>/dev/null | wc -l)
    css_count=$(sudo find "$static_dir" -maxdepth 1 -name '*.css' 2>/dev/null | wc -l)
    if [ "$js_count" -gt 0 ] && [ "$css_count" -gt 0 ]; then
        echo "PASS ($js_count js, $css_count css)"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL (js=$js_count, css=$css_count)"
        FAILED=$((FAILED + 1))
    fi
}

# ---------------------------------------------------------------------------
# Helper: journald capture (ProtectSystem=strict + --capture-output)
# ---------------------------------------------------------------------------
check_journald_capture() {
    echo -n "G-4  journald capture for unit: "
    local unit_file="/etc/systemd/system/prace-v-nemecku-gunicorn.service"
    if [ ! -r "$unit_file" ]; then
        echo "SKIP (unit file not readable)"
        return 0
    fi
    local protect_system capture_output
    protect_system=$(grep -E '^ProtectSystem=' "$unit_file" 2>/dev/null | cut -d= -f2 || true)
    capture_output=$(grep -F -- '--capture-output' "$unit_file" 2>/dev/null || true)
    if [ "$protect_system" = "strict" ] && [ -n "$capture_output" ]; then
        echo "FAIL (ProtectSystem=strict blocks journald when --capture-output is used)"
        FAILED=$((FAILED + 1))
    else
        echo "PASS (journald not blocked)"
        PASSED=$((PASSED + 1))
    fi
}

# ---------------------------------------------------------------------------
# Helper: G-1 password desync (read-only, never prints secret)
# ---------------------------------------------------------------------------
check_db_password_sync() {
    echo -n "G-1  DB password sync: "
    local env_file="$REPO_ROOT/.runtime-config/gunicorn.env"
    if [ ! -r "$env_file" ]; then
        # File is root-owned 640; try sudo
        if ! sudo test -r "$env_file"; then
            echo "SKIP (env file not readable even with sudo)"
            return 0
        fi
    fi

    # Extract password length metadata (never print the value)
    local pw_len
    pw_len=$(sudo grep -E '^PRACE_DB_PASSWORD=' "$env_file" 2>/dev/null | cut -d= -f2 | wc -c || true)
    if [ "$pw_len" -le 1 ]; then
        echo "FAIL (PRACE_DB_PASSWORD not set or empty)"
        FAILED=$((FAILED + 1))
        return 0
    fi

    # Check PostgreSQL role password hash (requires sudo)
    local role_hash
    role_hash=$(sudo -u postgres psql -tAc \
        "SELECT rolpassword FROM pg_authid WHERE rolname='prace_synth_app'" 2>/dev/null || true)
    if [ -z "$role_hash" ]; then
        echo "FAIL (role prace_synth_app not found)"
        FAILED=$((FAILED + 1))
        return 0
    fi

    # Compare: env file has password but role hash is empty/null
    if [ -z "$role_hash" ] || [ "$role_hash" = "NULL" ]; then
        echo "FAIL (env file has password (len=$pw_len) but role has no password hash)"
        FAILED=$((FAILED + 1))
        return 0
    fi

    # Actual authentication test: try to connect using env credentials
    # Never prints the password; only reports pass/fail
    local db_name db_user db_host db_port
    db_name=$(sudo grep -E '^PRACE_DB_NAME=' "$env_file" 2>/dev/null | cut -d= -f2 || true)
    db_user=$(sudo grep -E '^PRACE_DB_USER=' "$env_file" 2>/dev/null | cut -d= -f2 || true)
    db_host=$(sudo grep -E '^PRACE_DB_HOST=' "$env_file" 2>/dev/null | cut -d= -f2 || true)
    db_port=$(sudo grep -E '^PRACE_DB_PORT=' "$env_file" 2>/dev/null | cut -d= -f2 || true)

    if [ -z "$db_name" ] || [ -z "$db_user" ]; then
        echo "FAIL (DB name or user not set in env file)"
        FAILED=$((FAILED + 1))
        return 0
    fi

    local pg_password
    pg_password=$(sudo grep -E '^PRACE_DB_PASSWORD=' "$env_file" 2>/dev/null | cut -d= -f2- || true)

    local auth_test
    auth_test=$(PGPASSWORD="$pg_password" \
        psql \
        -h "${db_host:-localhost}" \
        -p "${db_port:-5432}" \
        -U "$db_user" \
        -d "$db_name" \
        -tAc "SELECT 1" 2>/dev/null || true)
    if [ "$auth_test" = "1" ]; then
        echo "PASS (authentication test succeeded)"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL (authentication test failed — env password does not match role)"
        FAILED=$((FAILED + 1))
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
cd "$REPO_ROOT"

echo "=== Delivery Readiness Check ==="
echo "Repo: $REPO_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

check_no_networkidle
check_unit_status
check_nginx_alias
check_static_files
check_journald_capture
check_db_password_sync

echo ""
echo "=== Summary ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo "RESULT: FAIL — $FAILED check(s) need attention" >&2
    exit 1
fi

echo "RESULT: PASS — all checks green"
exit 0
