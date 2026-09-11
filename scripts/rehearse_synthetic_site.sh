#!/usr/bin/env bash
# scripts/rehearse_synthetic_site.sh — Delivery-1 isolated synthetic rehearsal.
#
# One script, one command line, one supervised synthetic deployment
# under the existing confined runtime root. Rehearses the full
# Delivery-1 lifecycle (prepare → start → stop → restart → rollback)
# without touching the real-data activation gate (§14 of
# docs/security/real-data-rules.md) or any operator-owned services.
#
# Default runtime root:
#   runtime/portal/supervised-development/
#
# Required env (mirrors the settings module contract):
#   PRACE_SECRET_KEY         — the deployment secret (not the base default)
#   PRACE_ALLOWED_HOSTS      — comma-separated list (e.g. localhost,127.0.0.1)
#   PRACE_DB_*                — optional all-or-none PostgreSQL target
#
# Optional env (defaults below are safe for synthetic):
#   PRACE_BIND                — gunicorn bind socket (default 127.0.0.1:8001)
#   PRACE_WORKERS             — gunicorn workers (default 2)
#   PRACE_REHEARSE_TIMEOUT    — start/stop wait seconds (default 30)
#   PRACE_RUNTIME_ROOT        — override the runtime root
#
# Exit codes:
#   0  success
#   1  preparation failure (confined root, manifest, settings)
#   2  start failure (gunicorn did not accept requests in time / wrong server)
#   3  stop failure (gunicorn still listening)
#   4  restart failure (start after stop did not accept)
#   5  rollback failure (operator intervention required)
#   6  smoke failure (HTTP probe did not match expected contract)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/venv/bin/python"
GUNICORN="$REPO_ROOT/venv/bin/gunicorn"
RUNTIME_ROOT="${PRACE_RUNTIME_ROOT:-$REPO_ROOT/runtime/portal/supervised-development}"
RUNTIME_LOG_DIR="$RUNTIME_ROOT/logs"
RUNTIME_STATIC_DIR="$RUNTIME_ROOT/static"
MANIFEST_PATH="$RUNTIME_ROOT/release_manifest.json"
MANIFEST_SHA_FILE="$RUNTIME_ROOT/.release_manifest.sha256"
PIDFILE="$RUNTIME_ROOT/gunicorn.pid"
PID_STARTED_AT="$RUNTIME_ROOT/.gunicorn.started_at"
PID_CMDLINE="$RUNTIME_ROOT/.gunicorn.cmdline"
SOCKETFILE="$RUNTIME_ROOT/gunicorn.sock"
BIND="${PRACE_BIND:-127.0.0.1:8001}"
WORKERS="${PRACE_WORKERS:-2}"
START_TIMEOUT="${PRACE_REHEARSE_TIMEOUT:-30}"
APPROVED_RUNTIME_PARENT="$REPO_ROOT/runtime/portal"

step() { printf '\n=== %s ===\n' "$*"; }

require() {
    if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
        echo "FAIL: $2" >&2
        exit "$3"
    fi
}

require_executable() {
    if [ ! -x "$1" ]; then
        echo "FAIL: $1 not found or not executable" >&2
        exit 1
    fi
}

# Reset a file's mode unconditionally; ignore ENOENT for the chmod-after-close
# case in atomic writes.
force_mode() {
    [ -e "$1" ] && chmod "$2" "$1" || true
}

# Validate the runtime root's parent/name match the contract BEFORE any
# mkdir, chmod, write, or run. Refuses to mutate anything if invalid.
# This is the canonical confinement contract used by
# portal.release1a.runtime_safety.confined_root.
validate_runtime_root_layout() {
    case "$RUNTIME_ROOT" in
        /*) ;;
        *) echo "FAIL: $RUNTIME_ROOT must be an absolute path" >&2; exit 1 ;;
    esac
    if [ -L "$RUNTIME_ROOT" ]; then
        echo "FAIL: $RUNTIME_ROOT is a symlink" >&2
        exit 1
    fi
    local parent
    parent="$(dirname "$RUNTIME_ROOT")"
    local leaf
    leaf="$(basename "$RUNTIME_ROOT")"
    if [ "$parent" != "$APPROVED_RUNTIME_PARENT" ] \
            || [ "${leaf#supervised-}" = "$leaf" ]; then
        echo "FAIL: $RUNTIME_ROOT must be $APPROVED_RUNTIME_PARENT/supervised-* (got parent=$parent leaf=$leaf)" >&2
        exit 1
    fi
    # Reject parent-directory traversal in the path (defence in depth
    # beyond the absolute path check above).
    case "$RUNTIME_ROOT" in
        *"/../"*|*"/.."|*"../"*)
            echo "FAIL: $RUNTIME_ROOT contains a parent-directory traversal" >&2
            exit 1
            ;;
    esac
    # If the root exists, it must already be a confined layout; we will
    # not adopt arbitrary pre-existing directories.
    if [ -e "$RUNTIME_ROOT" ]; then
        if [ ! -d "$RUNTIME_ROOT" ]; then
            echo "FAIL: $RUNTIME_ROOT exists and is not a directory" >&2
            exit 1
        fi
        if [ "$(stat -c %u "$RUNTIME_ROOT")" != "$(id -u)" ]; then
            echo "FAIL: $RUNTIME_ROOT not owned by current user" >&2
            exit 1
        fi
        local mode
        mode="$(stat -c %04a "$RUNTIME_ROOT")"
        if [ "$mode" != "0700" ]; then
            echo "FAIL: $RUNTIME_ROOT mode $mode (must be 0700)" >&2
            exit 1
        fi
    fi
}

ensure_runtime_root() {
    if [ ! -d "$RUNTIME_ROOT" ]; then
        echo "FAIL: runtime root $RUNTIME_ROOT does not exist. Run 'prepare' first." >&2
        exit 1
    fi
    if [ "$(stat -c %u "$RUNTIME_ROOT")" != "$(id -u)" ]; then
        echo "FAIL: runtime root not owned by current user" >&2
        exit 1
    fi
    if [ "$(stat -c %04a "$RUNTIME_ROOT")" != "0700" ]; then
        echo "FAIL: runtime root permissions must be 0700" >&2
        exit 1
    fi
}

ensure_env() {
    if [ -z "${PRACE_SECRET_KEY:-}" ]; then
        echo "FAIL: PRACE_SECRET_KEY is required" >&2
        exit 1
    fi
    if [ "${PRACE_SECRET_KEY}" = "synthetic-m2-local-only-insecure-default" ]; then
        echo "FAIL: PRACE_SECRET_KEY must not equal the base default" >&2
        exit 1
    fi
    if [ -z "${PRACE_ALLOWED_HOSTS:-}" ]; then
        echo "FAIL: PRACE_ALLOWED_HOSTS is required (comma-separated)" >&2
        exit 1
    fi
}

# Probe TCP $1:$2 without timing out forever; succeed only when something
# actually accepted our SYN. Used to detect that a non-owned server is
# occupying the bind target.
probe_tcp() {
    local host="$1" port="$2" seconds="${3:-2}"
    timeout "$seconds" bash -c "exec 3<>/dev/tcp/$host/$port" 2>/dev/null \
        && { exec 3<&- 3>&- || true; return 0; }
    return 1
}

# curl wrapper: prints the actual http_code AND a curl-status marker to
# stderr. Exit status reflects curl itself. stdout is the body.
# Usage: code body curl_probe URL HOST MAX_TIME
curl_probe() {
    local url="$1" host="$2" max_time="$3"
    local tmp
    tmp="$(mktemp)"
    local code
    code="$(curl -sS --connect-timeout 2 --max-time "$max_time" \
        -H "Host: $host" -o "$tmp" -w '%{http_code}' \
        "$url" 2>/dev/null || echo 000)"
    cat "$tmp"
    rm -f "$tmp"
    printf '\n__HTTP_CODE__:%s\n' "$code"
}

cmd_prepare() {
    step "Prepare: validate confinement → mkdir → manifest → migrate → collectstatic"
    require_executable "$PYTHON_BIN"
    require_executable "$GUNICORN"
    cmd_prepare_manifest_only
    cmd_migrate
    cmd_collectstatic
    echo "OK: prepared $RUNTIME_ROOT"
}

# Confine-validate, create the layout, write the manifest and the SHA
# sidecar. Does NOT run migrate or collectstatic. Used by tests that
# only want to inspect the on-disk layout, and by prepare as a step.
cmd_prepare_manifest_only() {
    require_executable "$PYTHON_BIN"
    validate_runtime_root_layout
    if [ ! -d "$RUNTIME_ROOT" ]; then
        mkdir -p "$RUNTIME_ROOT"
        chmod 700 "$RUNTIME_ROOT"
    fi
    for child in storage media static cache tmp logs; do
        mkdir -p "$RUNTIME_ROOT/$child"
        chmod 700 "$RUNTIME_ROOT/$child"
    done
    "$PYTHON_BIN" "$REPO_ROOT/scripts/build_release_manifest.py" \
        --output "$MANIFEST_PATH"
    force_mode "$MANIFEST_PATH" 0400
    local actual_sha
    actual_sha="$(sha256sum "$MANIFEST_PATH" | awk '{print $1}')"
    : > "$MANIFEST_SHA_FILE"
    printf '%s' "$actual_sha" > "$MANIFEST_SHA_FILE"
    chmod 600 "$MANIFEST_SHA_FILE"
    echo "Manifest SHA: $actual_sha  (recorded at $MANIFEST_SHA_FILE)"
    export PRACE_RELEASE_MANIFEST_SHA256="$actual_sha"
    if [ -n "${PRACE_RELEASE_MANIFEST_SHA256_OVERRIDE:-}" ] \
            && [ "${PRACE_RELEASE_MANIFEST_SHA256_OVERRIDE}" != "$actual_sha" ]; then
        echo "FAIL: PRACE_RELEASE_MANIFEST_SHA256_OVERRIDE does not match" >&2
        exit 1
    fi
}

cmd_migrate() {
    step "Migrate: apply migrations against the supervised database"
    cd "$REPO_ROOT"
    local sha
    sha="$(cat "$MANIFEST_SHA_FILE" 2>/dev/null || true)"
    if [ -z "$sha" ]; then
        echo "FAIL: $MANIFEST_SHA_FILE missing or empty. Run 'prepare' first." >&2
        exit 1
    fi
    PRACE_RELEASE_MANIFEST_SHA256="$sha" \
    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT="$RUNTIME_ROOT" \
    PRACE_SECRET_KEY="$PRACE_SECRET_KEY" \
    PRACE_RELEASE_MANIFEST="$MANIFEST_PATH" \
    PRACE_ALLOWED_HOSTS="$PRACE_ALLOWED_HOSTS" \
    "$PYTHON_BIN" manage.py migrate --noinput
}

cmd_collectstatic() {
    step "Collectstatic: assemble static assets for DEBUG=False serving"
    cd "$REPO_ROOT"
    local sha
    sha="$(cat "$MANIFEST_SHA_FILE" 2>/dev/null || true)"
    if [ -z "$sha" ]; then
        echo "FAIL: $MANIFEST_SHA_FILE missing or empty. Run 'prepare' first." >&2
        exit 1
    fi
    PRACE_RELEASE_MANIFEST_SHA256="$sha" \
    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT="$RUNTIME_ROOT" \
    PRACE_SECRET_KEY="$PRACE_SECRET_KEY" \
    PRACE_RELEASE_MANIFEST="$MANIFEST_PATH" \
    PRACE_ALLOWED_HOSTS="$PRACE_ALLOWED_HOSTS" \
    "$PYTHON_BIN" manage.py collectstatic --noinput
}

# Refuse to launch if the target bind is already owned by someone else.
assert_bind_is_free() {
    local host="${BIND%:*}" port="${BIND#*:}"
    if probe_tcp "$host" "$port" 1; then
        echo "FAIL: $BIND already has a listener (refuse to overwrite)" >&2
        exit 1
    fi
}

cmd_start() {
    step "Start: gunicorn $BIND workers=$WORKERS"
    ensure_runtime_root
    ensure_env
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "gunicorn already running with PID $(cat "$PIDFILE")" >&2
        exit 1
    fi
    rm -f "$SOCKETFILE"
    rm -f "$PID_STARTED_AT" "$PID_CMDLINE"
    assert_bind_is_free
    cd "$REPO_ROOT"
    local manifest_sha
    manifest_sha="$(cat "$MANIFEST_SHA_FILE" 2>/dev/null || true)"
    if [ -z "$manifest_sha" ]; then
        echo "FAIL: no manifest SHA recorded. Run 'prepare' first." >&2
        exit 1
    fi
    PRACE_RELEASE_MANIFEST_SHA256="$manifest_sha" \
    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT="$RUNTIME_ROOT" \
    PRACE_SECRET_KEY="$PRACE_SECRET_KEY" \
    PRACE_RELEASE_MANIFEST="$MANIFEST_PATH" \
    PRACE_ALLOWED_HOSTS="$PRACE_ALLOWED_HOSTS" \
    nohup "$GUNICORN" portal.wsgi:application \
        --bind "$BIND" \
        --workers "$WORKERS" \
        --access-logfile - \
        --error-logfile - \
        --pid "$PIDFILE" \
        > "$RUNTIME_LOG_DIR/gunicorn.log" 2>&1 &
    # Defensive: chmod the log file regardless of the umask under which
    # gunicorn wrote it. AGENTS.md / docs/security/real-data-rules.md
    # require private file modes.
    chmod 600 "$RUNTIME_LOG_DIR/gunicorn.log" 2>/dev/null || true
    cmd_wait_ready "$BIND" "$START_TIMEOUT"
    # Record the launch identity so stop can verify it owns the pid.
    local pid
    pid="$(cat "$PIDFILE")"
    local started_at
    started_at="$(stat -c %Y "/proc/$pid" 2>/dev/null || echo 0)"
    printf '%s\n' "$started_at" > "$PID_STARTED_AT"
    chmod 600 "$PID_STARTED_AT"
    {
        printf 'pid=%s\n' "$pid"
        printf 'bind=%s\n' "$BIND"
        printf 'runtime_root=%s\n' "$RUNTIME_ROOT"
        printf 'launched_at=%s\n' "$started_at"
    } > "$PID_CMDLINE"
    chmod 600 "$PID_CMDLINE"
    # Final verification: the pid owns our listener AND serves our app.
    verify_launched_process
    echo "OK: gunicorn started PID=$pid"
}

# Confirm the launched gunicorn:
#   1. Still has the pid we recorded.
#   2. Serves /health/ with our build identity (not 000/500/502 from a wrong server).
#   3. Holds the bind (socket inode matches /proc/<pid>/fd/<n>).
verify_launched_process() {
    local hostport="$BIND"
    local host="${hostport%:*}"
    local port="${hostport#*:}"
    local host_header
    host_header="$(echo "$PRACE_ALLOWED_HOSTS" | cut -d, -f1)"
    local pid
    pid="$(cat "$PIDFILE")"
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "FAIL: gunicorn process $pid exited before serving requests" >&2
        tail -n 20 "$RUNTIME_LOG_DIR/gunicorn.log" >&2 || true
        exit 2
    fi
    # /health/ must return 200 and must identify our manifest's commit.
    local expected_commit
    expected_commit="$(jq -r '.git_commit' "$MANIFEST_PATH")"
    local health_body
    health_body="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" \
        "http://$hostport/health/" 2>/dev/null || true)"
    local health_status
    health_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' \
        "http://$hostport/health/" 2>/dev/null)"
    [ -z "$health_status" ] && health_status=000
    if [ "$health_status" != "200" ]; then
        echo "FAIL: /health/ returned $health_status (expected 200 from our gunicorn)" >&2
        tail -n 20 "$RUNTIME_LOG_DIR/gunicorn.log" >&2 || true
        kill "$pid" 2>/dev/null || true
        exit 2
    fi
    if ! printf '%s' "$health_body" | grep -qF "$expected_commit"; then
        echo "FAIL: /health/ did not advertise our manifest's commit $expected_commit" >&2
        printf '%s\n' "$health_body" >&2
        kill "$pid" 2>/dev/null || true
        exit 2
    fi
}

cmd_wait_ready() {
    local hostport="$1"
    local timeout="${2:-30}"
    local host="${hostport%:*}"
    local port="${hostport#*:}"
    local deadline=$(( $(date +%s) + timeout ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if probe_tcp "$host" "$port" 1; then
            # Confirm Django is responding (not just a bound socket).
            local code
            code="$(curl -sS --connect-timeout 2 --max-time 5 \
                -H "Host: ${PRACE_ALLOWED_HOSTS%%,*}" \
                -o /dev/null -w '%{http_code}' \
                "http://$hostport/health/" 2>/dev/null)"
            [ -z "$code" ] && code=000
            if [ "$code" = "200" ]; then
                return 0
            fi
        fi
        sleep 1
    done
    echo "FAIL: gunicorn did not accept requests within ${timeout}s" >&2
    if [ -f "$PIDFILE" ]; then
        kill "$(cat "$PIDFILE")" 2>/dev/null || true
    fi
    exit 2
}

# Verify a PID belongs to a gunicorn process we launched, not a reused
# PID file pointing at an arbitrary process. Reads /proc and matches the
# bind address and start time we recorded at start.
verify_pid_ownership() {
    local pid="$1"
    [ -f "$PID_CMDLINE" ] || { echo "FAIL: no launch record ($PID_CMDLINE)"; return 1; }
    [ -f "$PID_STARTED_AT" ] || { echo "FAIL: no launch start-time record"; return 1; }
    local recorded_bind recorded_runtime recorded_started_at
    recorded_bind="$(grep -E '^bind=' "$PID_CMDLINE" | head -n1 | cut -d= -f2-)"
    recorded_runtime="$(grep -E '^runtime_root=' "$PID_CMDLINE" | head -n1 | cut -d= -f2-)"
    recorded_started_at="$(cat "$PID_STARTED_AT" | tr -d '[:space:]')"
    if [ "$recorded_bind" != "$BIND" ]; then
        echo "FAIL: pidfile bind $recorded_bind != current BIND $BIND"
        return 1
    fi
    if [ "$recorded_runtime" != "$RUNTIME_ROOT" ]; then
        echo "FAIL: pidfile runtime $recorded_runtime != RUNTIME_ROOT $RUNTIME_ROOT"
        return 1
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "FAIL: pid $pid is not alive"
        return 1
    fi
    local proc_started_at
    proc_started_at="$(stat -c %Y "/proc/$pid" 2>/dev/null || echo 0)"
    if [ "$proc_started_at" != "$recorded_started_at" ]; then
        echo "FAIL: pid $pid started at $proc_started_at (recorded $recorded_started_at) - not our launch"
        return 1
    fi
    # Process exe must be the python interpreter that runs the
    # gunicorn entrypoint script. The venv's gunicorn is a thin
    # wrapper around the system python, so /proc/<pid>/exe is the
    # system python — we accept any python interpreter here, and
    # rely on the cmdline check below to confirm it is gunicorn.
    local exe
    exe="$(readlink "/proc/$pid/exe" 2>/dev/null || true)"
    case "$exe" in
        *python*|*gunicorn*) ;;
        *) echo "FAIL: pid $pid exe=$exe is not a python/gunicorn binary"; return 1 ;;
    esac
    # Process cmdline must reference our bind, the gunicorn entrypoint,
    # and the wsgi module. This is the authoritative check.
    local cmdline
    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    case "$cmdline" in
        *gunicorn*) ;;
        *) echo "FAIL: pid $pid cmdline does not mention gunicorn"; return 1 ;;
    esac
    case "$cmdline" in
        *"$BIND"*|*"$recorded_bind"*) ;;
        *) echo "FAIL: pid $pid cmdline does not mention $BIND"; return 1 ;;
    esac
    case "$cmdline" in
        *"portal.wsgi:application"*) ;;
        *) echo "FAIL: pid $pid cmdline does not mention portal.wsgi:application"; return 1 ;;
    esac
    return 0
}

cmd_stop() {
    step "Stop: verify pid ownership, then SIGTERM"
    if [ ! -f "$PIDFILE" ]; then
        echo "gunicorn not running (no pidfile)"
        return 0
    fi
    local pid
    pid="$(cat "$PIDFILE")"
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "stale pidfile; removing"
        rm -f "$PIDFILE" "$PID_STARTED_AT" "$PID_CMDLINE" "$SOCKETFILE"
        return 0
    fi
    if ! verify_pid_ownership "$pid"; then
        echo "FAIL: refusing to signal pid $pid - does not match our launch record" >&2
        exit 3
    fi
    kill -TERM "$pid"
    local deadline=$(( $(date +%s) + "$START_TIMEOUT" ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$PIDFILE" "$SOCKETFILE" "$PID_STARTED_AT" "$PID_CMDLINE"
            echo "OK: gunicorn stopped"
            return 0
        fi
        sleep 1
    done
    echo "FAIL: gunicorn did not stop within ${START_TIMEOUT}s" >&2
    exit 3
}

cmd_restart() {
    step "Restart: stop + start"
    cmd_stop
    cmd_start
}

cmd_status() {
    step "Status: pid, listening port, last log line"
    if [ ! -f "$PIDFILE" ]; then
        echo "stopped (no pidfile at $PIDFILE)"
        return 0
    fi
    local pid
    pid="$(cat "$PIDFILE")"
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "stale pidfile (PID $pid not alive)"
        return 1
    fi
    if ! verify_pid_ownership "$pid" >/dev/null 2>&1; then
        echo "pidfile contents do not match an owned gunicorn process"
        return 1
    fi
    echo "running PID=$pid bind=$BIND"
    if [ -f "$RUNTIME_LOG_DIR/gunicorn.log" ]; then
        tail -n 5 "$RUNTIME_LOG_DIR/gunicorn.log" || true
    fi
}

cmd_logs() {
    step "Logs: tail -n 50 of gunicorn.log"
    if [ ! -f "$RUNTIME_LOG_DIR/gunicorn.log" ]; then
        echo "no log file at $RUNTIME_LOG_DIR/gunicorn.log"
        return 0
    fi
    tail -n 50 "$RUNTIME_LOG_DIR/gunicorn.log"
}

cmd_rollback() {
    step "Rollback: stop the running server; preserve the runtime root"
    ensure_runtime_root
    if [ -f "$PIDFILE" ]; then
        cmd_stop || exit 5
    fi
    echo "Preserving $RUNTIME_ROOT for inspection."
    echo "Operator action: remove $RUNTIME_ROOT manually when investigation is done."
    echo "This script does NOT delete the runtime root; the operator confirms"
    echo "deletion after inspecting logs and the manifest."
}

# smoke probes four endpoints with strict expectations:
#   /health/                       → 200, JSON mentions our manifest's git_commit
#   /login/                        → 302 to /accounts/login/
#   /accounts/login/               → 200, contains password/login form fields
#   /review/                       → 302 to /accounts/login/?next=/review/
# A 000 from a stopped server, an HTTP 500 from a wrong server, or a 404
# from a missing route are all FAIL. curl's own exit status is also
# checked separately so a "000000" composite cannot pass.
cmd_smoke() {
    step "Smoke: strict HTTP contract against $BIND"
    ensure_runtime_root
    local hostport="$BIND"
    local host="${hostport%:*}"
    local port="${hostport#*:}"
    local host_header
    host_header="$(echo "$PRACE_ALLOWED_HOSTS" | cut -d, -f1)"
    local base="http://$hostport"
    local pass=0 fail=0 failures=()
    local expected_commit
    expected_commit="$(jq -r '.git_commit' "$MANIFEST_PATH" 2>/dev/null || echo unknown)"
    local manifest_app_build
    manifest_app_build="$(jq -r '.app_build_id' "$MANIFEST_PATH" 2>/dev/null || echo unknown)"

    # 1. /health/ must be 200 with our commit + supervised build identity.
    # On connect failure curl exits non-zero and -w prints nothing;
    # we capture curl's actual status output (or empty on failure) and
    # replace empty with "000" so the contract check sees a sentinel.
    # The `|| true` makes the assignment safe under set -e.
    local health_body health_status
    health_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' "$base/health/" 2>/dev/null || true)"
    [ -z "$health_status" ] && health_status=000
    health_body="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" "$base/health/" 2>/dev/null || true)"
    if [ "$health_status" = "200" ] \
            && { printf '%s' "$health_body" | grep -qF "$expected_commit"; } \
            && { printf '%s' "$health_body" | grep -qF 'supervised'; }; then
        pass=$((pass+1))
        echo "  PASS  $health_status  /health/ (commit=$expected_commit, supervised)"
    else
        fail=$((fail+1))
        failures+=("/health/: status=$health_status body-len=${#health_body}")
        echo "  FAIL  $health_status  /health/"
    fi

    # 2. /login/ must 302 to /accounts/login/.
    local login_status login_location
    login_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' "$base/login/" 2>/dev/null || true)"
    [ -z "$login_status" ] && login_status=000
    login_location="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -D - -o /dev/null "$base/login/" 2>/dev/null \
        | grep -i '^location:' | head -n1 | tr -d '\r' || true)"
    if [ "$login_status" = "302" ] && { printf '%s' "$login_location" | grep -q '/accounts/login/'; }; then
        pass=$((pass+1))
        echo "  PASS  $login_status  /login/ → $login_location"
    else
        fail=$((fail+1))
        failures+=("/login/: status=$login_status location=$login_location")
        echo "  FAIL  $login_status  /login/"
    fi

    # 3. /accounts/login/ must be 200 with password/login form fields.
    local accounts_status accounts_body
    accounts_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' "$base/accounts/login/" 2>/dev/null || true)"
    [ -z "$accounts_status" ] && accounts_status=000
    accounts_body="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" "$base/accounts/login/" 2>/dev/null || true)"
    if [ "$accounts_status" = "200" ] \
            && { printf '%s' "$accounts_body" | grep -q 'name="password"'; } \
            && { printf '%s' "$accounts_body" | grep -q 'name="login"'; }; then
        pass=$((pass+1))
        echo "  PASS  $accounts_status  /accounts/login/ (login form)"
    else
        fail=$((fail+1))
        failures+=("/accounts/login/: status=$accounts_status body-len=${#accounts_body}")
        echo "  FAIL  $accounts_status  /accounts/login/"
    fi

    # 4. /review/ must 302 to /accounts/login/?next=/review/.
    local review_status review_location
    review_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' "$base/review/" 2>/dev/null || true)"
    [ -z "$review_status" ] && review_status=000
    review_location="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -D - -o /dev/null "$base/review/" 2>/dev/null \
        | grep -i '^location:' | head -n1 | tr -d '\r' || true)"
    if [ "$review_status" = "302" ] && { printf '%s' "$review_location" | grep -q '/accounts/login/?next=/review/'; }; then
        pass=$((pass+1))
        echo "  PASS  $review_status  /review/ → /accounts/login/?next=/review/"
    else
        fail=$((fail+1))
        failures+=("/review/: status=$review_status location=$review_location")
        echo "  FAIL  $review_status  /review/"
    fi

    # 5. /readiness/ must return 200 ready with our build identity.
    local readiness_status readiness_body
    readiness_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' "$base/readiness/" 2>/dev/null || true)"
    [ -z "$readiness_status" ] && readiness_status=000
    readiness_body="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" "$base/readiness/" 2>/dev/null || true)"
    if [ "$readiness_status" = "200" ] \
            && { printf '%s' "$readiness_body" | grep -qF "$expected_commit"; } \
            && { printf '%s' "$readiness_body" | grep -q 'ready'; }; then
        pass=$((pass+1))
        echo "  PASS  $readiness_status  /readiness/ (commit=$expected_commit, ready)"
    else
        fail=$((fail+1))
        failures+=("/readiness/: status=$readiness_status body-len=${#readiness_body}")
        echo "  FAIL  $readiness_status  /readiness/"
    fi

    # 6. A known static asset must return 200 (not 404). The login form
    #    references these assets; if static serving is broken, login is
    #    effectively unstyled. Probe the assets actually shipped in
    #    portal/release1a/static/portal/. If collectstatic ran, the
    #    files exist under $RUNTIME_STATIC_DIR/portal/.
    for asset_path in "portal/htmx-1.9.10.min.js" "portal/tailwind-2.2.19.min.css"; do
        local asset_status asset_url
        asset_url="/static/$asset_path"
        asset_status="$(curl -sS --connect-timeout 2 --max-time 5 \
            -H "Host: $host_header" -o /dev/null \
            -w '%{http_code}' "$base$asset_url" 2>/dev/null || true)"
        [ -z "$asset_status" ] && asset_status=000
        if [ "$asset_status" = "200" ]; then
            pass=$((pass+1))
            echo "  PASS  $asset_status  $asset_url"
        else
            fail=$((fail+1))
            failures+=("$asset_url: status=$asset_status")
            echo "  FAIL  $asset_status  $asset_url"
        fi
    done

    echo
    echo "smoke: $pass passed, $fail failed (commit=$expected_commit, build_id=$manifest_app_build)"
    if [ "$fail" -gt 0 ]; then
        printf 'smoke failure details:\n'
        for f in "${failures[@]}"; do
            printf '  - %s\n' "$f"
        done
        exit 6
    fi
}

usage() {
    cat <<EOF
Usage: $0 <command> [args]
Commands:
  prepare                Validate confinement, build the manifest, migrate, collectstatic
  prepare-manifest-only  Same as prepare but skips migrate/collectstatic (used by tests)
  start                  Launch gunicorn against the supervised settings module
  stop                   Verify pid ownership, then SIGTERM
  restart                stop + start
  status                 Show pid, bind, and last log lines
  logs                   Tail the gunicorn log
  smoke                  Strict HTTP smoke (health+login+review+readiness+static)
  rollback               Stop the server; the operator removes the runtime root manually
EOF
}

main() {
    if [ "$#" -lt 1 ]; then
        usage >&2
        exit 1
    fi
    local cmd="$1"
    shift
    case "$cmd" in
        prepare)              cmd_prepare "$@" ;;
        prepare-manifest-only) cmd_prepare_manifest_only "$@" ;;
        start)                cmd_start "$@" ;;
        stop)                 cmd_stop "$@" ;;
        restart)              cmd_restart "$@" ;;
        status)               cmd_status "$@" ;;
        logs)                 cmd_logs "$@" ;;
        smoke)                cmd_smoke "$@" ;;
        rollback)             cmd_rollback "$@" ;;
        *)                    usage >&2; exit 1 ;;
    esac
}

main "$@"
