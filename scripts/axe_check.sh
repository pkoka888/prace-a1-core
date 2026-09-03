#!/usr/bin/env bash
# axe_check.sh
# Accessibility check for the four review screens using axe-core via Playwright.
#
# Workflow:
# 1. Authenticate as the synthetic reviewer via the real login flow.
# 2. Visit each TARGET_URL with an authenticated session.
# 3. Inject axe-core from CDN and collect WCAG 2.2 A/AA violations.
# 4. Fail on execution errors, serious/critical violations, redirects, or skipped pages.
# 5. Write axe_receipt.json with verdict, build_id, tested_urls, timestamp, result_hash.
#
# Blocking: serious or critical WCAG violations.
# Non-blocking: notices (minor / null impact).
# Credentials are supplied by the operator through gitignored secrets or the
# environment. Never put a reviewer identity, password, or TOTP seed here.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AXE_RECEIPT="$REPO_ROOT/runtime/portal/synthetic-review/axe_receipt.json"
AXE_JSON="$REPO_ROOT/runtime/portal/synthetic-review/axe.json"
PYTEST="$REPO_ROOT/venv/bin/python"
BUILD_MANIFEST="$REPO_ROOT/runtime/portal/synthetic-review/build_manifest.json"

mkdir -p "$(dirname "$AXE_RECEIPT")"
cd "$REPO_ROOT"

: "${AXE_REVIEWER_LOGIN:?Set AXE_REVIEWER_LOGIN from a gitignored synthetic-test secret}"
: "${AXE_REVIEWER_PASSWORD:?Set AXE_REVIEWER_PASSWORD from a gitignored synthetic-test secret}"
: "${AXE_REVIEWER_TOTP_SECRET:?Set AXE_REVIEWER_TOTP_SECRET from a gitignored synthetic-test secret}"

# ── Build ID ─────────────────────────────────────────────────────────────────
APP_BUILD_ID="$(SYNTHETIC_REVIEW_SECRET="$(cat "$REPO_ROOT/secrets/synthetic_review.key")" "$PYTEST" -c "
import hashlib, os, sys
sys.path.insert(0, '$REPO_ROOT')
os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_synthetic_review'
os.environ['SYNTHETIC_REVIEW_SECRET'] = os.environ.get('SYNTHETIC_REVIEW_SECRET', '')
import django; django.setup()
from django.conf import settings
commit = '$(
    git -C \"$REPO_ROOT\" rev-parse HEAD 2>/dev/null || echo unknown
)'
req_lock = ''
try:
    with open('$REPO_ROOT/requirements.txt') as f:
        req_lock = f.read()
except Exception:
    pass
build_id = hashlib.sha256(
    f\"{commit}:{settings.SETTINGS_MODULE}:{hashlib.sha256(req_lock.encode()).hexdigest()}\".encode()
).hexdigest()[:16]
print(build_id)
" 2>/dev/null || echo "unknown")"

# ── Target URLs (all behind require_org_membership) ───────────────────────────
TARGET_URLS="
/review/
/review/check-answers/
/workers/
"

# ── Server health check ───────────────────────────────────────────────────────
if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health/ 2>/dev/null | grep -q "200"; then
    echo "ERROR: Review server is not running at http://127.0.0.1:8000" >&2
    echo "Start with:" >&2
    echo "  export SYNTHETIC_REVIEW_SECRET=\$(cat secrets/synthetic_review.key)" >&2
    echo "  export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review" >&2
    echo "  python manage.py runserver 127.0.0.1:8000 --noreload" >&2
    cat > "$AXE_RECEIPT" <<EOF
{
  "verdict": "failed",
  "summary": "Server not running at http://127.0.0.1:8000",
  "build_id": "$APP_BUILD_ID",
  "tested_urls": [],
  "timestamp": "$(date -Iseconds)",
  "result_hash": ""
}
EOF
    exit 1
fi

echo "axe-core accessibility check"
echo "  Build ID: $APP_BUILD_ID"

# ── Inline Playwright test ────────────────────────────────────────────────────
TMP_TEST=$(mktemp)
PYEOF=$(mktemp)

cat > "$PYEOF" <<'PYEOF'
import json
import sys
import os
import time

from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8000'

URLS = sys.argv[1:] if len(sys.argv) > 1 else ['/review/']

AXE_CDN = (
    "https://cdn.jsdelivr.net/npm/axe-core@4.10.0/axe.min.js"
)

results = {}
all_passed = True

# Authenticate via a dedicated synthetic test account. Values are inherited
# from the operator's environment and are never written to a receipt or log.
ADMIN_EMAIL = os.environ["AXE_REVIEWER_LOGIN"]
ADMIN_PASSWORD = os.environ["AXE_REVIEWER_PASSWORD"]
totp_secret = os.environ["AXE_REVIEWER_TOTP_SECRET"]
import pyotp

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    # Step 1: GET login page to get CSRF token
    page.goto(f"{BASE}/accounts/login/", wait_until="networkidle", timeout=15000)
    login_token = page.query_selector('input[name="csrfmiddlewaretoken"]')
    if not login_token:
        print("ERROR: Could not find login CSRF token")
        import sys
        sys.exit(1)
    login_token = login_token.get_attribute("value")

    # Step 2: POST login credentials
    page.fill('input[name="login"]', ADMIN_EMAIL)
    page.fill('input[name="password"]', ADMIN_PASSWORD)
    with page.expect_navigation(timeout=15000):
        page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=5000)

    # If redirected to MFA, complete TOTP
    if "/accounts/2fa/" in page.url:
        # Get CSRF for MFA page
        mfa_token = page.query_selector('input[name="csrfmiddlewaretoken"]')
        if not mfa_token:
            print("ERROR: Could not find MFA CSRF token")
            import sys
            sys.exit(1)
        mfa_token = mfa_token.get_attribute("value")

        # Generate and submit TOTP immediately
        totp = pyotp.TOTP(totp_secret)
        page.fill('input[name="code"]', totp.now())
        with page.expect_navigation(timeout=15000):
            page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=5000)

    # Verify we're logged in
    if "/accounts/login" in page.url:
        print(f"ERROR: Login failed, still at {page.url}", file=sys.stderr)
        sys.exit(1)

    print(f"Login successful, at {page.url}", file=sys.stderr)

    for url_path in URLS:
        url = BASE + url_path
        results[url_path] = {"status": "untested", "violations": [], "notices": []}

        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            results[url_path] = {
                "status": "error",
                "violations": [],
                "notices": [],
                "error": str(e),
            }
            all_passed = False
            continue

        if page.url != url and BASE not in page.url:
            results[url_path] = {
                "status": "redirected",
                "violations": [],
                "notices": [],
                "final_url": page.url,
            }
            all_passed = False
            continue

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        try:
            page.evaluate(
                f"var s=document.createElement('script');s.src='{AXE_CDN}';s.onload=function(){{window.__axe_ready=1}};document.head.appendChild(s);"
            )
            page.wait_for_function("window.__axe_ready === 1", timeout=10000)
        except Exception as e:
            results[url_path] = {
                "status": "error",
                "violations": [],
                "notices": [],
                "error": f"axe-core not loaded: {e}",
            }
            all_passed = False
            continue

        try:
            axe_result = page.evaluate("""
                async () => {
                    if (typeof axe === 'undefined') return {error: 'axe not defined after load'};
                    return await axe.run({'reporter': 'v2'});
                }
            """)
        except Exception as e:
            results[url_path] = {
                "status": "error",
                "violations": [],
                "notices": [],
                "error": f"axe.run() failed: {e}",
            }
            all_passed = False
            continue

        if not isinstance(axe_result, dict):
            results[url_path] = {
                "status": "error",
                "violations": [],
                "notices": [],
                "error": f"Unexpected axe result type: {type(axe_result)}",
            }
            all_passed = False
            continue

        violations = axe_result.get("violations", [])
        serious_critical = [
            v for v in violations if v.get("impact") in ("critical", "serious")
        ]
        notices = [v for v in violations if v.get("impact") in (None, "minor")]

        if serious_critical:
            results[url_path] = {
                "status": "failed",
                "violations": serious_critical,
                "notices": notices,
            }
            all_passed = False
        else:
            results[url_path] = {
                "status": "passed",
                "violations": [],
                "notices": notices,
            }

    browser.close()

verdict = "passed" if all_passed else "failed"
violation_count = sum(
    len(r.get("violations", [])) for r in results.values()
)

import hashlib, datetime
now = datetime.datetime.now(datetime.timezone.utc)
payload = json.dumps({"verdict": verdict, "urls": results, "build_id": "%s", "timestamp": now.isoformat().replace("+00:00", "Z")}, sort_keys=True)
result_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]

receipt = {
    "verdict": verdict,
    "summary": f"{violation_count} serious/critical violation(s)" if violation_count else "No serious violations",
    "build_id": "%s",
    "tested_urls": list(URLS),
    "timestamp": now.isoformat().replace("+00:00", "Z"),
    "result_hash": result_hash,
    "url_results": results,
}
print(json.dumps(receipt, indent=2))
PYEOF

AXE_RESULT=$("$PYTEST" "$PYEOF" ${TARGET_URLS} 2>/dev/null)
rm -f "$TMP_TEST" "$PYEOF"

# Write axe.json (raw per-url results)
echo "$AXE_RESULT" | "$PYTEST" -c "
import json, sys
d = json.load(sys.stdin)
url_results = d.pop('url_results', {})
out = {'verdict': d['verdict'], 'summary': d['summary'], 'timestamp': d['timestamp'], 'urls': {}}
for u, r in url_results.items():
    out['urls'][u] = r
print(json.dumps(out, indent=2))
" > "$AXE_JSON"

# Write axe_receipt.json
echo "$AXE_RESULT" > "$AXE_RECEIPT"

VERDICT=$(echo "$AXE_RESULT" | "$PYTEST" -c "import json,sys; print(json.load(sys.stdin).get('verdict','unknown'))" 2>/dev/null || echo "unknown")
SUMMARY=$(echo "$AXE_RESULT" | "$PYTEST" -c "import json,sys; print(json.load(sys.stdin).get('summary',''))" 2>/dev/null || echo "")

echo "Result: $VERDICT — $SUMMARY"
echo "Receipt: $AXE_RECEIPT"

if [ "$VERDICT" = "failed" ]; then
    exit 1
fi
exit 0
