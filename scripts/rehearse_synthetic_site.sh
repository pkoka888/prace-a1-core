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
#   PRACE_READINESS_BUDGET_MS — readiness subprocess budget (default 10000)
#   PRACE_MIGRATION_STATEMENT_TIMEOUT_MS — migrate statement timeout (default 60000)
#   PRACE_OPERATOR_URL        — canonical operator-facing URL (optional)
#   PRACE_TEST_DB_*           — isolated test database target (optional)
#
# Exit codes:
#   0  success
#   1  preparation failure (confined root, manifest, settings)
#   2  start failure (gunicorn did not accept requests in time / wrong server)
#   3  stop failure (gunicorn still listening)
#   4  restart failure (start after stop did not accept)
#   5  rollback failure (operator intervention required)
#   6  smoke failure (HTTP probe did not match expected contract)
#   7  workflow failure (authenticated session could not exercise the journey)
set -euo pipefail

# Private creation policy. Every file/directory created by this script
# inherits mode 0700 from this umask regardless of the caller's umask.
# Tests that change the process umask must restore it; see
# test_manifest_mode_is_0o400_under_permissive_umask for the
# restoration pattern.
umask 077

# Caller's umask on entry (so tests can restore).
PRACE_PREVIOUS_UMASK="$(umask)"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/venv/bin/python"
GUNICORN="$REPO_ROOT/venv/bin/gunicorn"
RUNTIME_ROOT="${PRACE_RUNTIME_ROOT:-$REPO_ROOT/runtime/portal/supervised-development}"
RUNTIME_LOG_DIR="$RUNTIME_ROOT/logs"
RUNTIME_STATIC_DIR="$RUNTIME_ROOT/static"
RUNTIME_DB_PATH="$RUNTIME_ROOT/db.sqlite3"
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

# PostgreSQL target contract: all four PRACE_DB_* vars or none. A partial
# set never starts a server that might silently fall back to SQLite.
postgres_present=0
for db_var in PRACE_DB_NAME PRACE_DB_USER PRACE_DB_HOST PRACE_DB_PORT; do
    if [ -n "${!db_var:-}" ]; then
        postgres_present=$((postgres_present + 1))
    fi
done
if [ "$postgres_present" != "0" ] && [ "$postgres_present" != "4" ]; then
    echo "FAIL: partial PostgreSQL target ($postgres_present of 4 PRACE_DB_* vars set); set all four or none" >&2
    exit 1
fi
# Exact-match operator database names are never valid migration/cleanup
# targets. Ownership of these names is infra/operator authorization, so
# the script refuses them before any schema or data mutation.
operator_db_names="prace_synthetic"
if [ "$postgres_present" = "4" ] \
    && [ "${PRACE_DB_NAME:-}" = "$operator_db_names" ]; then
    echo "FAIL: refused PostgreSQL target '$operator_db_names' (operator database name)" >&2
    exit 1
fi
db_target_line() {
    if [ "$postgres_present" = "4" ]; then
        echo "DB target: PostgreSQL host=${PRACE_DB_HOST}:${PRACE_DB_PORT} db=${PRACE_DB_NAME} user=${PRACE_DB_USER}"
    else
        echo "DB target: SQLite (local rehearsal default)"
    fi
}

step() { printf '\n=== %s ===\n' "$*" >&2; }

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
# case in atomic writes. Refuses to operate on symlinks.
force_mode() {
    [ -L "$1" ] && { echo "FAIL: refusing to chmod symlink $1" >&2; exit 1; }
    [ -e "$1" ] && chmod "$2" "$1" || true
}

# True when the raw path is a symlink (does not follow the link). Used
# before any mkdir/chmod/write so we never silently follow a symlink
# and change a target's permissions.
raw_is_symlink() {
    [ -L "$1" ]
}

# Reject any raw-path symlink component. Walks the path from
# $APPROVED_RUNTIME_PARENT to the supplied leaf, refusing any
# component that is a symlink. This is the canonical confinement
# contract reused from portal.release1a.runtime_safety.no_symlinks,
# expressed for shell.
reject_path_symlinks() {
    local target="$1"
    local -a parts
    IFS='/' read -r -a parts <<< "$target"
    local current=""
    local part
    for part in "${parts[@]}"; do
        if [ -z "$part" ]; then
            current="/"
            continue
        fi
        if [ -z "$current" ] || [ "$current" = "/" ]; then
            current="/$part"
        else
            current="$current/$part"
        fi
        if [ -L "$current" ]; then
            echo "FAIL: $target contains symlink component $current" >&2
            return 1
        fi
    done
    return 0
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
    reject_path_symlinks "$RUNTIME_ROOT" || exit 1
    if raw_is_symlink "$RUNTIME_ROOT"; then
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
    # Pre-existing child symlinks: refuse before any mkdir/chmod. This
    # is the F2 case the prior prepare silently walked into a target
    # and chmod'd the target.
    for child in storage media static cache tmp logs; do
        local child_path="$RUNTIME_ROOT/$child"
        if [ -L "$child_path" ]; then
            echo "FAIL: $child_path is a pre-existing symlink" >&2
            exit 1
        fi
    done
    # Sidecar and state files must also not be pre-existing symlinks.
    for f in "$MANIFEST_PATH" "$MANIFEST_SHA_FILE" "$PIDFILE" \
             "$PID_STARTED_AT" "$PID_CMDLINE" "$SOCKETFILE" \
             "$RUNTIME_LOG_DIR/gunicorn.log" "$RUNTIME_DB_PATH"; do
        if [ -L "$f" ]; then
            echo "FAIL: $f is a pre-existing symlink" >&2
            exit 1
        fi
    done
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

# Read the gunicorn pidfile and confirm the same process holds the bind
# socket. Returns 0 on match; non-zero on any inconsistency. The
# implementation reads /proc/<pid>/fd/* for the socket inode and
# compares it to the inode of the bind port via /proc/net/tcp.
verify_socket_ownership() {
    local pid="$1"
    local host="${BIND%:*}" port="${BIND#*:}"
    [ -d "/proc/$pid" ] || { echo "FAIL: pid $pid not in /proc"; return 1; }
    # Find the listening socket inode bound by gunicorn.
    # /proc/net/tcp: local_address is hex ip:port; state 0A = LISTEN.
    local hex_port
    hex_port="$(printf '%04X' "$port")"
    local listening_inode
    listening_inode="$(awk -v hp="$hex_port" '$2 ~ ":"hp"$" && $4 == "0A" {print $10; exit}' /proc/net/tcp || true)"
    [ -n "$listening_inode" ] || { echo "FAIL: no LISTEN socket on port $port"; return 1; }
    # Walk the pid's fds looking for a socket with this inode.
    local fd
    for fd in /proc/$pid/fd/*; do
        local target
        target="$(readlink "$fd" 2>/dev/null || true)"
        case "$target" in
            "socket:[$listening_inode]")
                return 0
                ;;
        esac
    done
    echo "FAIL: pid $pid does not own LISTEN socket inode $listening_inode on port $port"
    return 1
}

cmd_prepare() {
    step "Prepare: validate confinement → mkdir → manifest → migrate → collectstatic"
    require_executable "$PYTHON_BIN"
    require_executable "$GUNICORN"
    cmd_prepare_manifest_only
    cmd_migrate
    cmd_collectstatic
    # Enforce private creation policy on every file Django or
    # collectstatic may have created with a more permissive umask.
    chmod 0600 "$RUNTIME_DB_PATH" 2>/dev/null || true
    chmod 0700 "$RUNTIME_LOG_DIR" 2>/dev/null || true
    for log_file in "$RUNTIME_LOG_DIR"/*.log; do
        [ -e "$log_file" ] || continue
        chmod 0600 "$log_file" 2>/dev/null || true
    done
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
        # mkdir -p on an existing non-symlink directory is a no-op;
        # the symlink check above rejects the F2 case where it would
        # follow a pre-existing child symlink.
        mkdir -p "$RUNTIME_ROOT/$child"
        chmod 700 "$RUNTIME_ROOT/$child"
    done
    # mkdir for the log directory specifically (gunicorn writes here).
    mkdir -p "$RUNTIME_LOG_DIR"
    chmod 700 "$RUNTIME_LOG_DIR"
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
    echo "$(db_target_line)" >&2
    cd "$REPO_ROOT"
    local sha
    sha="$(cat "$MANIFEST_SHA_FILE" 2>/dev/null || true)"
    if [ -z "$sha" ]; then
        echo "FAIL: $MANIFEST_SHA_FILE missing or empty. Run 'prepare' first." >&2
        exit 1
    fi
    local migration_timeout="${PRACE_MIGRATION_STATEMENT_TIMEOUT_MS:-60000}"
    PRACE_RELEASE_MANIFEST_SHA256="$sha" \
    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT="$RUNTIME_ROOT" \
    PRACE_SECRET_KEY="$PRACE_SECRET_KEY" \
    PRACE_RELEASE_MANIFEST="$MANIFEST_PATH" \
    PRACE_ALLOWED_HOSTS="$PRACE_ALLOWED_HOSTS" \
    PRACE_MIGRATION_SCOPE=1 \
    PRACE_MIGRATION_STATEMENT_TIMEOUT_MS="$migration_timeout" \
    "$PYTHON_BIN" manage.py migrate --noinput
    # Re-assert private mode on the database after Django's create.
    chmod 0600 "$RUNTIME_DB_PATH" 2>/dev/null || true
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

# OCR is a separate sequential process; persisted OcrRun rows are its queue.
# Credentials are read only by the confined helper; argv carries opaque IDs.
cmd_ocr_worker() {
    "$PYTHON_BIN" "$REPO_ROOT/scripts/run_ocr_worker_lifecycle.py" "$1" \
        --runtime-root "$RUNTIME_ROOT" --timeout "$START_TIMEOUT"
}

cmd_start() {
    validate_runtime_root_layout
    step "Start: gunicorn $BIND workers=$WORKERS"
    echo "$(db_target_line)" >&2
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
    # Truncate gunicorn.log before launching so we can chmod it 0600
    # without racing with gunicorn's open(2). With umask 077 the file
    # would still be 0600, but we chmod explicitly to satisfy the
    # AGENTS.md private file mode contract under any umask.
    : > "$RUNTIME_LOG_DIR/gunicorn.log"
    chmod 0600 "$RUNTIME_LOG_DIR/gunicorn.log"
    # The readiness subprocess orchestrates multiple checks and
    # exceeds the 2 s default budget on cold-start synthetic
    # deployments. Default the rehearsal budget to 10 s so the
    # strict /readiness/ contract check passes; the operator can
    # override PRACE_READINESS_BUDGET_MS to a tighter or looser
    # value as needed.
    local readiness_budget="${PRACE_READINESS_BUDGET_MS:-10000}"
    PRACE_RELEASE_MANIFEST_SHA256="$manifest_sha" \
    DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic \
    PRACE_RUNTIME_ROOT="$RUNTIME_ROOT" \
    PRACE_SECRET_KEY="$PRACE_SECRET_KEY" \
    PRACE_RELEASE_MANIFEST="$MANIFEST_PATH" \
    PRACE_ALLOWED_HOSTS="$PRACE_ALLOWED_HOSTS" \
    PRACE_READINESS_BUDGET_MS="$readiness_budget" \
    nohup "$GUNICORN" portal.wsgi:application \
        --bind "$BIND" \
        --workers "$WORKERS" \
        --access-logfile - \
        --error-logfile - \
        --pid "$PIDFILE" \
        >> "$RUNTIME_LOG_DIR/gunicorn.log" 2>&1 &
    local launch_pid=$!
    # Re-chmod in case the redirect happened after the open(2). Use
    # the actual file path; this is not racing with the write because
    # the open(2) has already happened and we only modify the inode's
    # mode.
    chmod 0600 "$RUNTIME_LOG_DIR/gunicorn.log" 2>/dev/null || true
    # Readiness is allowed to fail. If it does, we must clean up the
    # gunicorn we actually launched — even before the launch record
    # (PID_CMDLINE/PID_STARTED_AT) was written.
    if ! cmd_wait_ready "$BIND" "$START_TIMEOUT"; then
        echo "FAIL: gunicorn did not accept requests within ${START_TIMEOUT}s" >&2
        if [ -f "$PIDFILE" ]; then
            kill "$(cat "$PIDFILE")" 2>/dev/null || true
        fi
        kill -TERM "$launch_pid" 2>/dev/null || true
        # Also kill any descendants the gunicorn master may have
        # forked, in case the pidfile was never written.
        pkill -P "$launch_pid" 2>/dev/null || true
        exit 2
    fi
    # Now the gunicorn has written its pidfile. Verify ownership and
    # record the launch identity so stop can refuse wrong PIDs.
    local pid
    pid="$(cat "$PIDFILE")"
    if ! verify_socket_ownership "$pid"; then
        echo "FAIL: gunicorn pid $pid does not own the bind socket" >&2
        kill "$pid" 2>/dev/null || true
        exit 2
    fi
    if ! verify_launched_process; then
        kill "$pid" 2>/dev/null || true
        exit 2
    fi
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
    if [ -f "$RUNTIME_ROOT/operator.json" ]; then
        if ! cmd_ocr_worker start; then
            echo "FAIL: OCR worker startup failed; stopping owned rehearsal" >&2
            cmd_stop
            exit 2
        fi
    fi
    echo "OK: gunicorn started PID=$pid (verified owns socket, /health/ served)"
}

# Confirm the launched gunicorn:
#   1. Still has the pid we recorded.
#   2. Serves /health/ with our build identity (not 000/500/502 from a wrong server).
#   3. Body is JSON with the supervised-synthetic contract.
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
        return 1
    fi
    local expected_commit
    expected_commit="$(jq -r '.git_commit' "$MANIFEST_PATH")"
    local expected_build
    expected_build="$(jq -r '.app_build_id' "$MANIFEST_PATH")"
    # /health/ must return 200 and must identify our manifest's commit
    # and the supervised build. Use the same strict JSON contract as
    # smoke (see scripts/smoke_probe.py::_check_health).
    local health_status health_body
    health_status="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" -o /dev/null \
        -w '%{http_code}' \
        "http://$hostport/health/" 2>/dev/null || true)"
    [ -z "$health_status" ] && health_status=000
    health_body="$(curl -sS --connect-timeout 2 --max-time 5 \
        -H "Host: $host_header" \
        "http://$hostport/health/" 2>/dev/null || true)"
    if [ "$health_status" != "200" ]; then
        echo "FAIL: /health/ returned $health_status (expected 200 from our gunicorn)" >&2
        tail -n 20 "$RUNTIME_LOG_DIR/gunicorn.log" >&2 || true
        return 1
    fi
    # Parse JSON and assert the typed fields, not substrings.
    local health_check
    local health_check_stderr
    # Capture stdout (the JSON report) separately from stderr
    # (Python tracebacks). The contract is that smoke_probe.py
    # prints exactly one JSON document on stdout.
    health_check="$("$PYTHON_BIN" "$REPO_ROOT/scripts/smoke_probe.py" \
        "http://$hostport" "$host_header" "$MANIFEST_PATH" 2>/tmp/smoke.err)" || true
    local health_check_rc=$?
    if [ "$health_check_rc" != "0" ]; then
        echo "FAIL: /health/ did not satisfy the strict contract (commit/build/supervised/real_data/mode)" >&2
        if [ -s /tmp/smoke.err ]; then
            echo "smoke_probe stderr:" >&2
            cat /tmp/smoke.err >&2
        fi
        echo "$health_check" | "$PYTHON_BIN" -c '
import json, sys
try:
    text = sys.stdin.read()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        print("smoke_probe output had no JSON:", text[:400])
        sys.exit(1)
    r = json.loads(text[start:end+1])
    for c in r.get("checks", []):
        if not c["contract_ok"]:
            print("failed check:", c["path"], "status=" + str(c["status"]))
            print("  expected:", json.dumps(c["expected"], indent=2, sort_keys=True))
            print("  observed:", json.dumps(c["observed"], indent=2, sort_keys=True))
except Exception as exc:
    print("could not parse smoke_probe output:", exc)
' >&2 || true
        return 1
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
                "http://$hostport/health/" 2>/dev/null || true)"
            [ -z "$code" ] && code=000
            if [ "$code" = "200" ]; then
                return 0
            fi
        fi
        sleep 1
    done
    return 1
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
    validate_runtime_root_layout
    if [ -d "$RUNTIME_ROOT" ]; then
        cmd_ocr_worker stop || exit 3
    fi
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
    step "Status: pid, listening port, OCR worker, last log line"
    if [ -d "$RUNTIME_ROOT" ]; then
        cmd_ocr_worker status || return 1
    fi
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

# smoke delegates to scripts/smoke_probe.py for the strict contract
# (parsed JSON, exact boolean/status fields, same-origin redirects).
cmd_smoke() {
    step "Smoke: strict contract via scripts/smoke_probe.py"
    ensure_runtime_root
    local hostport="$BIND"
    local host_header
    host_header="$(echo "$PRACE_ALLOWED_HOSTS" | cut -d, -f1)"
    local report
    if ! report="$("$PYTHON_BIN" "$REPO_ROOT/scripts/smoke_probe.py" \
        "http://$hostport" "$host_header" "$MANIFEST_PATH" 2>&1)"; then
        echo "$report"
        exit 6
    fi
    echo "$report" | "$PYTHON_BIN" -c '
import json, sys
r = json.loads(sys.stdin.read())
ok = r.get("contract_ok")
print()
print("smoke:", "ok" if ok else "FAIL",
      "(commit=" + r.get("expected_commit", "")[:12],
      "build_id=" + r.get("expected_build_id", ""))
for c in r.get("checks", []):
    mark = "PASS" if c["contract_ok"] else "FAIL"
    print(" ", mark, c["status"], c["path"])
    if not c["contract_ok"]:
        print("       expected:", c.get("expected"))
        print("       observed:", {k: c["observed"][k] for k in list(c["observed"].keys())[:6]})
sys.exit(0 if ok else 6)
' || exit 6
}

# Workflow: real browser journey through the running gunicorn. Requires
# provision to have written operator.json with email/password/TOTP and
# start to have launched the server. The journey script is the documented
# Delivery-1 acceptance path: login + TOTP -> worker -> document upload
# -> OCR -> assignment -> A1 draft -> PDF download. It exits 7 on any
# journey failure (matching the documented exit-code table above).
cmd_workflow() {
    validate_runtime_root_layout
    step "Workflow: real-browser authenticated journey"
    ensure_runtime_root
    ensure_env
    require_executable "$PYTHON_BIN"
    if [ ! -f "$RUNTIME_ROOT/operator.json" ]; then
        echo "FAIL: $RUNTIME_ROOT/operator.json missing. Run 'provision' first." >&2
        exit 1
    fi
    if [ ! -f "$PIDFILE" ] || ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "FAIL: gunicorn is not running. Run 'start' first." >&2
        exit 1
    fi
    cd "$REPO_ROOT"
    local hostport="$BIND"
    local base_url
    if [ -n "${PRACE_OPERATOR_URL:-}" ]; then
        base_url="$PRACE_OPERATOR_URL"
    else
        base_url="http://$hostport"
    fi
    if ! verify_pid_ownership "$(cat "$PIDFILE")"; then
        echo "FAIL: workflow requires the owned rehearsal server" >&2
        exit 7
    fi
    cmd_ocr_worker start >&2 || exit 7
    local journey_tmp="$RUNTIME_ROOT/tmp/workflow-$$"
    mkdir -p "$journey_tmp"
    chmod 700 "$journey_tmp"
    local profile="core"
    while [ $# -gt 0 ]; do
        case "$1" in
            --profile)
                profile="$2"
                shift 2
                ;;
            *)
                echo "FAIL: unknown workflow option $1" >&2
                exit 7
                ;;
        esac
    done
    if [ "$profile" != "core" ] && [ "$profile" != "optional-a1" ]; then
        echo "FAIL: --profile must be 'core' or 'optional-a1' (got $profile)" >&2
        exit 7
    fi
    local rc=0
    PYTHONPATH="$REPO_ROOT:$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" "$REPO_ROOT/tests/_rehearse_workflow_browser.py" \
        --base-url "$base_url" \
        --runtime-root "$RUNTIME_ROOT" \
        --tmpdir "$journey_tmp" \
        --profile "$profile" || rc=$?
    if [ "$rc" != "0" ]; then
        echo "FAIL: workflow journey exited with $rc" >&2
        exit 7
    fi
    echo "OK: real-browser journey completed" >&2
}

# Synthetic operator + organization + MFA workflow. The first
# operator is provisioned idempotently (email + username derived
# from PRACE_OPERATOR_EMAIL, default synthetic-only), the
# organization is created with synthetic-only properties, and
# TOTP MFA is enrolled for the operator. The TOTP secret is
# written to a sidecar (mode 0600) under the ignored private runtime so a real
# browser or curl-driven session can complete the MFA challenge.
cmd_provision() {
    validate_runtime_root_layout
    step "Provision: synthetic operator + organization + MFA"
    ensure_runtime_root
    ensure_env
    require_executable "$PYTHON_BIN"
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
    "$PYTHON_BIN" "$REPO_ROOT/scripts/provision_synthetic_operator.py" \
        --runtime-root "$RUNTIME_ROOT" \
        ${PRACE_OPERATOR_EMAIL:+--email "$PRACE_OPERATOR_EMAIL"} \
        ${PRACE_OPERATOR_PASSWORD:+--password "$PRACE_OPERATOR_PASSWORD"} \
        ${PRACE_ORGANIZATION_LABEL:+--organization "$PRACE_ORGANIZATION_LABEL"}
    chmod 0600 "$RUNTIME_ROOT/operator.json" 2>/dev/null || true
    chmod 0600 "$RUNTIME_ROOT/organization.json" 2>/dev/null || true
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        verify_pid_ownership "$(cat "$PIDFILE")" || exit 2
        cmd_ocr_worker start || exit 2
    fi
    echo "OK: provisioned synthetic operator + organization + MFA"
    echo "Operator credentials and TOTP URI: $RUNTIME_ROOT/operator.json (mode 0600)"
}

usage() {
    cat <<EOF
Usage: $0 <command> [args]
Commands:
  prepare                Validate confinement, build the manifest, migrate, collectstatic
  prepare-manifest-only  Same as prepare but skips migrate/collectstatic (used by tests)
  start                  Launch gunicorn and provisioned sequential OCR worker
  stop                   Stop owned OCR worker and gunicorn
  restart                stop + start
  status                 Show pid, bind, and last log lines
  logs                   Tail the gunicorn log
  smoke                  Strict HTTP smoke via scripts/smoke_probe.py
  provision              Create a synthetic operator + organization + MFA
  workflow [--profile core|optional-a1]  Run an end-to-end authenticated session (uses provision)
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
        provision)            cmd_provision "$@" ;;
        workflow)             cmd_workflow "$@" ;;
        rollback)             cmd_rollback "$@" ;;
        *)                    usage >&2; exit 1 ;;
    esac
}

main "$@"
