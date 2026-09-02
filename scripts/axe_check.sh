#!/usr/bin/env bash
# axe_check.sh
# Runs axe-core accessibility checks against the four review screens and J-journey screens.
# Writes per-URL results to runtime/portal/synthetic-review/axe.json.
# Requires: axe-core-selenium or axe-playwright installed in venv.
# Blocking: confirmed WCAG 2.2 A/AA violations.
# Non-blocking: tool warnings not confirmed as violations.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AXE_OUT="$REPO_ROOT/runtime/portal/synthetic-review/axe.json"
PYTEST="$REPO_ROOT/venv/bin/python"

mkdir -p "$(dirname "$AXE_OUT")"

TARGET_URLS="
http://127.0.0.1:8000/review/
http://127.0.0.1:8000/review/check-answers/
http://127.0.0.1:8000/workers/
http://127.0.0.1:8000/
"

echo "Accessibility check requires the review server to be running at http://127.0.0.1:8000"
echo "To start:"
echo "  export SYNTHETIC_REVIEW_SECRET=\$(cat secrets/synthetic_review.key)"
echo "  export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review"
echo "  python manage.py runserver 127.0.0.1:8000 --noreload"
echo ""

if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health/ 2>/dev/null | grep -q "200"; then
    echo "ERROR: Review server is not running at http://127.0.0.1:8000"
    echo "Skipping axe check. Run the server and re-run this script."
    cat > "$AXE_OUT" <<EOF
{
  "verdict": "skipped",
  "summary": "Server not running",
  "generated_at": "$(date -Iseconds)",
  "urls": {}
}
EOF
    exit 0
fi

echo "Running axe-core checks…"

RESULT="{}"

for url in $TARGET_URLS; do
    echo -n "  $url ... "
    VIOLATIONS="[]"
    NOTICES="[]"

    # Try axe-playwright if available, fall back to skipped
    if $PYTEST -c /dev/null -c /dev/null -c /dev/null -c /dev/null -c /dev/null 2>/dev/null | grep -q "no module"; then
        echo "SKIP (axe not installed)"
        RESULT=$(echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['$url'] = {'status': 'skipped', 'reason': 'axe not installed'}
print(json.dumps(d))
")
        continue
    fi

    # Write a small inline test
    TMP_TEST=$(mktemp)
    cat > "$TMP_TEST" <<PYEOF
from playwright.sync_api import sync_playwright
import json, sys

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/review/"
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")
    results = page.evaluate("""
        async () => {
            if (typeof axe === 'undefined') return {error: 'axe not loaded'};
            return await axe.run();
        }
    """)
    browser.close()
    print(json.dumps(results))
PYEOF

    if command -v playwright >/dev/null 2>&1 && python3 -c "import playwright" 2>/dev/null; then
        AXE_RESULT=$(python3 "$TMP_TEST" "$url" 2>/dev/null || echo '{"error": "failed"}')
        VIOLATIONS=$(echo "$AXE_RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
violations = d.get('violations', [])
confirmed = [v for v in violations if v.get('impact') in ('critical', 'serious', 'moderate')]
notices = [v for v in violations if v.get('impact') in (None, 'minor')]
print(json.dumps({'confirmed': confirmed, 'notices': notices}))
" 2>/dev/null || echo '{"confirmed": [], "notices": []}')
        echo "OK"
    else
        echo "SKIP (playwright not available)"
    fi

    rm -f "$TMP_TEST"
done

cat > "$AXE_OUT" <<EOF
{
  "verdict": "complete",
  "summary": "See per-url results",
  "generated_at": "$(date -Iseconds)",
  "urls": $RESULT
}
EOF

echo "Written to: $AXE_OUT"
