#!/bin/bash
# scripts/release_reproducer.sh <commit-sha>
#
# Export the tracked source tree of a committed SHA to runtime/s-<sha>/ and
# run a focused set of acceptance checks with the project venv interpreter.
# Writes a protected hash-bound receipt with command results and timing.
#
# Safety:
# - Refuses to run on a dirty/untracked working tree (per AGENTS.md).
# - Refuses to overwrite an existing export of a different commit.
# - Uses protected runtime paths (mode 0700 dirs / 0600 files).
# - Does NOT deploy, mutate historical databases, copy secrets or
#   real-data paths, or read any path outside the exported source.
#
# Usage:
#   bash scripts/release_reproducer.sh <commit-sha>
#   bash scripts/release_reproducer.sh HEAD
#   bash scripts/release_reproducer.sh feat/prace-readiness-plan-2026-08-13
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/venv/bin/python"
RUNTIME_DIR="${REPO_ROOT}/runtime"
RECEIPT_NAME="reproducer-receipt.json"

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <commit-sha>" >&2
    echo "  Export committed source to runtime/s-<sha>/ and run acceptance checks." >&2
    exit 2
fi

REQUESTED="$1"

# Resolve short / branch / tag SHA to full commit hash.
SHA="$(cd "${REPO_ROOT}" && git rev-parse --verify "${REQUESTED}^{commit}" 2>/dev/null || true)"
if [ -z "${SHA}" ]; then
    echo "ERROR: cannot resolve '${REQUESTED}' to a commit" >&2
    exit 2
fi

# Dirty-tree guard: AGENTS.md forbids exporting dirty / untracked input.
DIRTY="$(cd "${REPO_ROOT}" && git status --porcelain)"
if [ -n "${DIRTY}" ]; then
    echo "ERROR: working tree is dirty. Commit or stash before reproducing a release." >&2
    cd "${REPO_ROOT}" && git status --porcelain >&2
    exit 1
fi

EXPORT_DIR="${RUNTIME_DIR}/s-${SHA}"
RECEIPT_DIR="${EXPORT_DIR}/_receipt"

# Refuse to overwrite a differing existing export.
if [ -d "${EXPORT_DIR}" ]; then
    EXISTING="$(cd "${EXPORT_DIR}" && git rev-parse HEAD 2>/dev/null || echo "")"
    if [ "${EXISTING}" != "${SHA}" ]; then
        echo "ERROR: ${EXPORT_DIR} already contains commit ${EXISTING:-<unknown>}; refusing to overwrite." >&2
        exit 1
    fi
    echo "Reusing existing export at ${EXPORT_DIR}"
else
    mkdir -p -m 0700 "${EXPORT_DIR}"
    # Atomic export via git archive; never copies untracked or dirty state.
    if ! (cd "${REPO_ROOT}" && git archive --format=tar "${SHA}" | tar -x -C "${EXPORT_DIR}"); then
        rm -rf "${EXPORT_DIR}"
        echo "ERROR: git archive failed for ${SHA}" >&2
        exit 1
    fi
    chmod 0700 "${EXPORT_DIR}"
    echo "Exported ${SHA} to ${EXPORT_DIR}"
fi

mkdir -p -m 0700 "${RECEIPT_DIR}"
RECEIPT="${RECEIPT_DIR}/${RECEIPT_NAME}"

# Build the protected hash-bound receipt.
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RECEIPT_TMP="${RECEIPT}.tmp"
: > "${RECEIPT_TMP}"

CHECKS=(
    "venv/bin/python scripts/validate_planning.py"
    "venv/bin/python scripts/validate_change_packages.py --staged --run-checks"
    "env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m pytest tests/m2/test_synthetic_containment.py -q"
    "env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m pytest tests/test_finalize_a1.py tests/test_a1_stabilization.py -q"
)

echo "Running ${#CHECKS[@]} acceptance checks against ${EXPORT_DIR}..."
PASS_COUNT=0
FAIL_COUNT=0
{
    echo "{"
    echo "  \"schema_version\": \"1.0\","
    echo "  \"commit_sha\": \"${SHA}\","
    echo "  \"export_dir\": \"runtime/s-${SHA}\","
    echo "  \"started_at\": \"${STARTED_AT}\","
    echo "  \"checks\": ["
    FIRST=1
    for cmd in "${CHECKS[@]}"; do
        start_ns=$(date +%s%N)
        stdout_path="${RECEIPT_DIR}/check-${FIRST}.stdout"
        stderr_path="${RECEIPT_DIR}/check-${FIRST}.stderr"
        : > "${stdout_path}"
        : > "${stderr_path}"
        # shellcheck disable=SC2086
        if (cd "${EXPORT_DIR}" && eval "${cmd}") >"${stdout_path}" 2>"${stderr_path}"; then
            status="PASS"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            status="FAIL"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
        exit_code=$?
        end_ns=$(date +%s%N)
        duration_ms=$(( (end_ns - start_ns) / 1000000 ))
        cmd_hash="$("${PYTHON_BIN}" -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest())" "${cmd}")"
        if [ "${FIRST}" -gt 1 ]; then echo ","; fi
        cat <<JSON
    {
      "index": ${FIRST},
      "command": $(printf '%s' "${cmd}" | "${PYTHON_BIN}" -c "import json,sys; print(json.dumps(sys.stdin.read()))"),
      "command_sha256": "${cmd_hash}",
      "status": "${status}",
      "exit_code": ${exit_code},
      "duration_ms": ${duration_ms},
      "stdout_log": "_receipt/check-${FIRST}.stdout",
      "stderr_log": "_receipt/check-${FIRST}.stderr"
    }
JSON
        FIRST=$((FIRST + 1))
    done
    echo
    echo "  ],"
    echo "  \"summary\": {\"pass\": ${PASS_COUNT}, \"fail\": ${FAIL_COUNT}, \"total\": ${#CHECKS[@]}}"
    echo "}"
} > "${RECEIPT_TMP}"

mv "${RECEIPT_TMP}" "${RECEIPT}"
chmod 0600 "${RECEIPT}"
chmod 0600 "${RECEIPT_DIR}"/*.stdout "${RECEIPT_DIR}"/*.stderr 2>/dev/null || true

echo
echo "Receipt: ${RECEIPT}"
echo "Pass: ${PASS_COUNT}  Fail: ${FAIL_COUNT}  Total: ${#CHECKS[@]}"
if [ "${FAIL_COUNT}" -gt 0 ]; then
    echo "Some checks failed; see ${RECEIPT} and individual logs."
    exit 1
fi
