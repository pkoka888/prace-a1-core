#!/usr/bin/env bash
# fix_nginx_static_alias.sh
# Idempotent fix for G-3: updates the nginx /static/ alias to point to
# STATIC_ROOT (runtime/portal/supervised-synthetic/static/).
#
# Usage:
#   scripts/fix_nginx_static_alias.sh            # apply fix
#   scripts/fix_nginx_static_alias.sh --dry-run  # show diff only
#
# Exit codes:
#   0 - fix applied (or already correct)
#   1 - fix failed
#   2 - usage error
set -euo pipefail

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
fi

NGINX_CONF="/etc/nginx/sites-enabled/prace-v-nemecku.expc.cz.conf"
EXPECTED_ALIAS="/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/"
CURRENT_ALIAS=$(grep -F 'alias /' "$NGINX_CONF" 2>/dev/null | grep 'location /static/' -A1 | tail -1 | sed 's/.*alias //; s/;.*//' || true)

if [ "$CURRENT_ALIAS" = "$EXPECTED_ALIAS" ]; then
    echo "G-3 nginx alias already correct: $EXPECTED_ALIAS"
    exit 0
fi

echo "G-3 nginx alias mismatch detected"
echo "  Current:  $CURRENT_ALIAS"
echo "  Expected: $EXPECTED_ALIAS"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "Dry-run: would update $NGINX_CONF"
    echo "Diff:"
    sudo sed "s|alias .*/static/;|alias $EXPECTED_ALIAS;|" "$NGINX_CONF" | diff -u "$NGINX_CONF" - || true
    exit 0
fi

# Apply fix
if ! sudo sed -i "s|alias .*/static/;|alias $EXPECTED_ALIAS;|" "$NGINX_CONF"; then
    echo "ERROR: failed to update $NGINX_CONF" >&2
    exit 1
fi

# Verify syntax
if ! sudo nginx -t 2>&1; then
    echo "ERROR: nginx syntax check failed — rolling back" >&2
    sudo git checkout -- "$NGINX_CONF" 2>/dev/null || true
    exit 1
fi

# Reload
if ! sudo systemctl reload nginx 2>&1; then
    echo "ERROR: nginx reload failed" >&2
    exit 1
fi

echo "G-3 fix applied: nginx alias updated to $EXPECTED_ALIAS"
echo "Verify: curl -I http://127.0.0.1/static/portal/htmx-1.9.10.min.js"
exit 0
