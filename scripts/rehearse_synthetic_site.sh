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
#   2  start failure (gunicorn did not accept requests in time)
#   3  stop failure (gunicorn still listening)
#   4  restart failure (start after stop did not accept)
#   5  rollback failure (operator intervention required)
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
SOCKETFILE="$RUNTIME_ROOT/gunicorn.sock"
BIND="${PRACE_BIND:-127.0.0.1:8001}"
WORKERS="${PRACE_WORKERS:-2}"
START_TIMEOUT="${PRACE_REHEARSE_TIMEOUT:-30}"

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

ensure_runtime_root() {
    if [ ! -d "$RUNTIME_ROOT" ]; then
        echo "FAIL: runtime root $RUNTIME_ROOT does not exist. Run 'prepare' first." >&2
        exit 1
    fi
    if [ "$(stat -c %u "$RUNTIME_ROOT")" != "$(id -u)" ]; then
        echo "FAIL: runtime root not owned by current user" >&2
        exit 1
    fi
    if [ "$(stat -c %a "$RUNTIME_ROOT" | tail -c 4)" != "700" ]; then
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

cmd_prepare() {
    step "Prepare: confined runtime root + manifest + child directories"
    require_executable "$PYTHON_BIN"
    require_executable "$GUNICORN"
    mkdir -p "$RUNTIME_ROOT"
    chmod 700 "$RUNTIME_ROOT"
    for child in storage media static cache tmp logs; do
        mkdir -p "$RUNTIME_ROOT/$child"
        chmod 700 "$RUNTIME_ROOT/$child"
    done
    # Manifest is required by settings_supervised_synthetic.
    "$PYTHON_BIN" "$REPO_ROOT/scripts/build_release_manifest.py" \
        --output "$MANIFEST_PATH"
    local actual_sha
    actual_sha="$(sha256sum "$MANIFEST_PATH" | awk '{print $1}')"
    printf '%s' "$actual_sha" > "$MANIFEST_SHA_FILE"
    chmod 600 "$MANIFEST_SHA_FILE"
    echo "Manifest SHA: $actual_sha  (recorded at $MANIFEST_SHA_FILE)"
    # The settings module requires PRACE_RELEASE_MANIFEST_SHA256. The
    # script exports it from the sidecar file for downstream commands
    # (migrate, collectstatic, start) so a single prepare → start flow
    # works without the operator copying the SHA into the environment.
    export PRACE_RELEASE_MANIFEST_SHA256="$actual_sha"
    if [ -n "${PRACE_RELEASE_MANIFEST_SHA256_OVERRIDE:-}" ] \
            && [ "${PRACE_RELEASE_MANIFEST_SHA256_OVERRIDE}" != "$actual_sha" ]; then
        echo "FAIL: PRACE_RELEASE_MANIFEST_SHA256_OVERRIDE does not match" >&2
        exit 1
    fi
    # Django migrate + collectstatic for DEBUG=False.
    cmd_migrate
    cmd_collectstatic
    echo "OK: prepared $RUNTIME_ROOT"
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

cmd_start() {
    step "Start: gunicorn $BIND workers=$WORKERS"
    ensure_runtime_root
    ensure_env
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "gunicorn already running with PID $(cat "$PIDFILE")" >&2
        exit 1
    fi
    rm -f "$SOCKETFILE"
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
    cmd_wait_ready "$BIND" "$START_TIMEOUT"
    echo "OK: gunicorn started PID=$(cat "$PIDFILE")"
}

cmd_wait_ready() {
    local hostport="$1"
    local timeout="${2:-30}"
    local host="${hostport%:*}"
    local port="${hostport#*:}"
    local deadline=$(( $(date +%s) + timeout ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if (echo > "/dev/tcp/$host/$port") 2>/dev/null; then
            # Confirm Django is responding (not just a bound socket).
            local code
            code="$(curl -sS -o /dev/null -w '%{http_code}' \
                -H "Host: ${PRACE_ALLOWED_HOSTS%%,*}" \
                "http://$hostport/login/" 2>/dev/null || echo 000)"
            if [ "$code" != "000" ] && [ "$code" != "502" ]; then
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

cmd_stop() {
    step "Stop: graceful shutdown of gunicorn"
    if [ ! -f "$PIDFILE" ]; then
        echo "gunicorn not running (no pidfile)"
        return 0
    fi
    local pid
    pid="$(cat "$PIDFILE")"
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "stale pidfile; removing"
        rm -f "$PIDFILE"
        return 0
    fi
    kill -TERM "$pid"
    local deadline=$(( $(date +%s) + "$START_TIMEOUT" ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$PIDFILE" "$SOCKETFILE"
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
    if kill -0 "$pid" 2>/dev/null; then
        echo "running PID=$pid bind=$BIND"
    else
        echo "stale pidfile (PID $pid not alive)"
        return 1
    fi
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
    step "Rollback: stop + remove the supervised runtime"
    ensure_runtime_root
    if [ -f "$PIDFILE" ]; then
        cmd_stop
    fi
    echo "Preserving $RUNTIME_ROOT for inspection."
    echo "Operator action: remove $RUNTIME_ROOT manually when investigation is done."
    echo "This script does NOT delete the runtime root; the operator confirms"
    echo "deletion after inspecting logs and the manifest."
}

cmd_smoke() {
    step "Smoke: HTTP probes against the supervised deployment"
    ensure_runtime_root
    local hostport="$BIND"
    local host="${hostport%:*}"
    local port="${hostport#*:}"
    local host_header
    host_header="$(echo "$PRACE_ALLOWED_HOSTS" | cut -d, -f1)"
    local base="http://$hostport"
    local pass=0 fail=0
    for path in "/health/" "/login/" "/static/" "/review/"; do
        local code
        code="$(curl -sS -o /dev/null -w '%{http_code}' \
            -H "Host: $host_header" \
            "$base$path" 2>/dev/null || echo 000)"
        if [ "$code" != "000" ]; then
            pass=$((pass+1))
            echo "  $code  $path"
        else
            fail=$((fail+1))
            echo "  $code  $path  (curl error)"
        fi
    done
    echo "smoke: $pass passed, $fail failed"
    if [ "$fail" -gt 0 ]; then
        exit 1
    fi
}

usage() {
    cat <<EOF
Usage: $0 <command> [args]
Commands:
  prepare      Create the runtime root, build the manifest, migrate, collectstatic
  start        Launch gunicorn against the supervised settings module
  stop         Graceful TERM and wait
  restart      stop + start
  status       Show pid, bind, and last log lines
  logs         Tail the gunicorn log
  smoke        HTTP smoke against the supervised deployment
  rollback     Stop the server; the operator removes the runtime root manually
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
        prepare)  cmd_prepare "$@" ;;
        start)    cmd_start "$@" ;;
        stop)     cmd_stop "$@" ;;
        restart)  cmd_restart "$@" ;;
        status)   cmd_status "$@" ;;
        logs)     cmd_logs "$@" ;;
        smoke)    cmd_smoke "$@" ;;
        rollback) cmd_rollback "$@" ;;
        *)        usage >&2; exit 1 ;;
    esac
}

main "$@"
