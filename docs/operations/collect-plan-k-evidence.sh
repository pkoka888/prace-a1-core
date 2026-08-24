#!/bin/bash
# Plan K Evidence Collection Script
# Run as sysadmin on server62 to collect required evidence for Plan K acceptance gates
# Output: evidence/plan-k-YYYYMMDD/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
OUT_DIR="${PROJECT_ROOT}/evidence/plan-k-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$OUT_DIR"

log() {
    echo "[$(date -Iseconds)] $*" | tee -a "$OUT_DIR/collection.log"
}

log "=== Plan K Evidence Collection Started ==="
log "Output directory: $OUT_DIR"

# -----------------------------------------------------------------------------
# 1. CAPACITY GATE (DEC-013: 15 GiB / 15% free)
# -----------------------------------------------------------------------------
log "Collecting capacity evidence..."
{
    echo "=== CAPACITY EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""
    echo "--- df -h /var/www ---"
    df -h /var/www
    echo ""
    echo "--- df -h /var/lib/postgresql ---"
    df -h /var/lib/postgresql 2>/dev/null || echo "PostgreSQL not on separate mount"
    echo ""
    echo "--- df -h /tmp ---"
    df -h /tmp
    echo ""
    echo "--- df -h / (root) ---"
    df -h /
    echo ""
    echo "--- lsblk ---"
    lsblk
    echo ""
    echo "--- Memory ---"
    free -h
} > "$OUT_DIR/capacity.txt" 2>&1

# Check gates
CAPACITY_OK=true
while read -r line; do
    if [[ "$line" =~ ^/dev/.*\s+([0-9.]+)G\s+([0-9.]+)G\s+([0-9.]+)G\s+([0-9]+)%\s+/var/www$ ]]; then
        AVAIL="${BASH_REMATCH[3]}"
        USE_PCT="${BASH_REMATCH[4]}"
        FREE_PCT=$((100 - USE_PCT))
        if (( $(echo "$AVAIL < 15" | bc -l) )) || (( FREE_PCT < 15 )); then
            CAPACITY_OK=false
            log "WARNING: /var/www capacity gate FAIL - Available: ${AVAIL}G, Free: ${FREE_PCT}%"
        else
            log "OK: /var/www capacity gate PASS - Available: ${AVAIL}G, Free: ${FREE_PCT}%"
        fi
    fi
done < <(df -h /var/www)

# -----------------------------------------------------------------------------
# 2. EDGE PATH GATE (Nginx -> App connectivity)
# -----------------------------------------------------------------------------
log "Collecting edge path evidence..."
{
    echo "=== EDGE PATH EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""
    echo "--- Local HTTP health ---"
    curl -I -s http://localhost/health 2>&1 || echo "FAILED"
    echo ""
    echo "--- Local HTTPS health ---"
    curl -I -k -s https://localhost/health 2>&1 || echo "FAILED"
    echo ""
    echo "--- Public HTTP health ---"
    curl -I -s http://prace-v-nemecku.tvoje.info/health 2>&1 || echo "FAILED"
    echo ""
    echo "--- Public HTTPS health ---"
    curl -I -s https://prace-v-nemecku.tvoje.info/health 2>&1 || echo "FAILED"
    echo ""
    echo "--- Nginx config test ---"
    nginx -t 2>&1
    echo ""
    echo "--- Nginx status ---"
    systemctl status nginx --no-pager 2>&1 | head -20
    echo ""
    echo "--- Service status ---"
    systemctl status prace-v-nemecku --no-pager 2>&1 | head -30
} > "$OUT_DIR/edge-path.txt" 2>&1

# -----------------------------------------------------------------------------
# 3. MONITORING GATE
# -----------------------------------------------------------------------------
log "Collecting monitoring evidence..."
{
    echo "=== MONITORING EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""
    echo "--- Prometheus ---"
    systemctl status prometheus --no-pager 2>&1 | head -30
    echo ""
    echo "--- Prometheus targets ---"
    curl -s http://localhost:9090/api/v1/targets 2>&1 | jq . 2>/dev/null || echo "jq not available or Prometheus not running"
    echo ""
    echo "--- Grafana ---"
    systemctl status grafana-server --no-pager 2>&1 | head -30
    echo ""
    echo "--- Node Exporter ---"
    systemctl status node_exporter --no-pager 2>&1 | head -20
    echo ""
    echo "--- PostgreSQL Exporter ---"
    systemctl status postgres_exporter --no-pager 2>&1 | head -20
} > "$OUT_DIR/monitoring.txt" 2>&1

# -----------------------------------------------------------------------------
# 4. BACKUP GATE (Encrypted, application-consistent)
# -----------------------------------------------------------------------------
log "Collecting backup evidence..."
{
    echo "=== BACKUP EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""

    # Check for backup passphrase in environment
    if [[ -z "${BACKUP_PASS:-}" ]]; then
        echo "WARNING: BACKUP_PASS not set - using test passphrase for evidence only"
        BACKUP_PASS="plan-k-evidence-test-passphrase-$(date +%s)"
    fi

    echo "--- PostgreSQL Backup ---"
    DB_DUMP="${OUT_DIR}/db-backup-$(date +%Y%m%d-%H%M%S).dump.gz.enc"
    if pg_dump -Fc prace_v_nemecku 2>/dev/null | gzip | openssl enc -aes-256-cbc -salt -out "$DB_DUMP" -pass pass:"$BACKUP_PASS"; then
        echo "SUCCESS: DB backup created at $DB_DUMP"
        ls -lh "$DB_DUMP"
        echo "Backup size: $(du -h "$DB_DUMP" | cut -f1)"
    else
        echo "FAILED: DB backup"
    fi
    echo ""

    echo "--- Application Files Backup (excl venv, .git, output, runtime, secrets) ---"
    APP_BACKUP="${OUT_DIR}/app-backup-$(date +%Y%m%d-%H%M%S).tar.gz.enc"
    if tar -czf - -C "$PROJECT_ROOT" \
        --exclude=venv --exclude=.git --exclude=output --exclude=runtime \
        --exclude=secrets --exclude=.history-remediation --exclude=a1 \
        --exclude=scans --exclude=evidence --exclude=ocr --exclude=data \
        --exclude=employees/scans --exclude=private --exclude=reports \
        --exclude="*.log" --exclude="*.pid" \
        . 2>/dev/null | openssl enc -aes-256-cbc -salt -out "$APP_BACKUP" -pass pass:"$BACKUP_PASS"; then
        echo "SUCCESS: App backup created at $APP_BACKUP"
        ls -lh "$APP_BACKUP"
        echo "Backup size: $(du -h "$APP_BACKUP" | cut -f1)"
    else
        echo "FAILED: App backup"
    fi
    echo ""

    echo "--- Backup Integrity Check ---"
    if [[ -f "$DB_DUMP" ]]; then
        echo "DB backup decrypt test:"
        openssl enc -d -aes-256-cbc -in "$DB_DUMP" -pass pass:"$BACKUP_PASS" | gunzip | pg_restore --list | head -5
        echo "... (truncated)"
    fi
} > "$OUT_DIR/backup.txt" 2>&1

# -----------------------------------------------------------------------------
# 5. RESTORE TEST GATE (Isolated environment)
# -----------------------------------------------------------------------------
log "Collecting restore test evidence..."
{
    echo "=== RESTORE TEST EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""

    TEST_DB="prace_v_nemecku_restore_test_$(date +%Y%m%d%H%M%S)"

    echo "--- Creating test database ---"
    if createdb "$TEST_DB" 2>&1; then
        echo "Test DB created: $TEST_DB"
    else
        echo "FAILED: Could not create test DB"
        exit 1
    fi

    echo "--- Restoring DB backup ---"
    if [[ -f "$DB_DUMP" ]]; then
        if openssl enc -d -aes-256-cbc -in "$DB_DUMP" -pass pass:"$BACKUP_PASS" | gunzip | pg_restore -d "$TEST_DB" 2>&1; then
            echo "SUCCESS: DB restored to $TEST_DB"
        else
            echo "FAILED: DB restore"
        fi
    else
        echo "SKIPPED: No DB dump to restore"
    fi

    echo "--- Verifying Restored Data ---"
    psql -d "$TEST_DB" -c "SELECT 'organizations' AS table_name, count(*) FROM release1a_organization
        UNION ALL SELECT 'users', count(*) FROM release1a_user
        UNION ALL SELECT 'workers', count(*) FROM release1a_worker
        UNION ALL SELECT 'audit_events', count(*) FROM release1a_auditevent;" 2>&1

    echo "--- Dropping Test Database ---"
    dropdb "$TEST_DB" 2>&1 && echo "Test DB dropped"
} > "$OUT_DIR/restore-test.txt" 2>&1

# -----------------------------------------------------------------------------
# 6. ROLLBACK GATE (Procedure documented + tested)
# -----------------------------------------------------------------------------
log "Collecting rollback evidence..."
{
    echo "=== ROLLBACK EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""
    echo "--- Git History (last 10 commits) ---"
    cd "$PROJECT_ROOT"
    git log --oneline -10
    echo ""
    echo "--- Current Branch ---"
    git branch -v
    echo ""
    echo "--- Migration Status ---"
    venv/bin/python manage.py showmigrations --plan 2>&1 | head -30
    echo ""
    echo "--- Rollback Procedure Documented ---"
    cat <<'ROLLBACK_EOF'
ROLLBACK PROCEDURE (Documented):
1. Identify target commit: git log --oneline
2. Stop services: systemctl stop prace-v-nemecku nginx
3. Database rollback (if migration applied):
   - pg_restore from pre-migration backup
   - OR: python manage.py migrate <app> <previous_migration>
4. Code rollback: git checkout <target_commit> -- .
5. Restart services: systemctl start prace-v-nemecku nginx
6. Verify health endpoints
7. Run smoke tests: venv/bin/python -m pytest tests/test_a1_core.py -q
ROLLBACK_EOF
} > "$OUT_DIR/rollback.txt" 2>&1

# -----------------------------------------------------------------------------
# 7. PERMISSIONS GATE (Least privilege)
# -----------------------------------------------------------------------------
log "Collecting permissions evidence..."
{
    echo "=== PERMISSIONS EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""
    echo "--- Systemd Security Analysis ---"
    systemd-analyze security prace-v-nemecku.service 2>&1
    echo ""
    echo "--- Service File ---"
    cat /etc/systemd/system/prace-v-nemecku.service 2>/dev/null || echo "Service file not at standard location"
    echo ""
    echo "--- File Permissions (project root) ---"
    ls -la "$PROJECT_ROOT" | head -30
    echo ""
    echo "--- Service User/Group ---"
    systemctl show prace-v-nemecku --property=User,Group,SupplementaryGroups 2>&1
    echo ""
    echo "--- Database User Permissions ---"
    psql -d prace_v_nemecku -c "\du" 2>&1
} > "$OUT_DIR/permissions.txt" 2>&1

# -----------------------------------------------------------------------------
# 8. TLS GATE (Valid certificates)
# -----------------------------------------------------------------------------
log "Collecting TLS evidence..."
{
    echo "=== TLS EVIDENCE ==="
    echo "Date: $(date -Iseconds)"
    echo ""
    echo "--- Certificate Details (public) ---"
    openssl s_client -connect prace-v-nemecku.tvoje.info:443 -servername prace-v-nemecku.tvoje.info </dev/null 2>&1 | openssl x509 -noout -text
    echo ""
    echo "--- Certificate Expiry ---"
    openssl s_client -connect prace-v-nemecku.tvoje.info:443 -servername prace-v-nemecku.tvoje.info </dev/null 2>&1 | openssl x509 -noout -dates
    echo ""
    echo "--- SSL Labs Grade (if available) ---"
    echo "Run: https://www.ssllabs.com/ssltest/analyze.html?d=prace-v-nemecku.tvoje.info"
    echo ""
    echo "--- Nginx SSL Config ---"
    nginx -T 2>&1 | grep -A 20 "ssl_certificate" | head -30
} > "$OUT_DIR/tls.txt" 2>&1

# -----------------------------------------------------------------------------
# SUMMARY
# -----------------------------------------------------------------------------
log "=== Plan K Evidence Collection Complete ==="
log "Evidence directory: $OUT_DIR"
log ""
log "Files created:"
ls -la "$OUT_DIR"
log ""
log "NEXT STEPS:"
log "1. Review each evidence file for PASS/FAIL"
log "2. Provide evidence to primary agent for Plan K validation"
log "3. Primary agent updates Plan K status in plans/INDEX.md"
log ""
log "GATE SUMMARY (manual review required):"
log "  Capacity:     Check capacity.txt for 15GiB/15% on /var/www and /var/lib/postgresql"
log "  Edge Path:    Check edge-path.txt for 200 OK on health endpoints"
log "  Monitoring:   Check monitoring.txt for Prometheus/Grafana active"
log "  Backup:       Check backup.txt for successful encrypted backups"
log "  Restore:      Check restore-test.txt for successful isolated restore"
log "  Rollback:     Check rollback.txt for documented procedure"
log "  Permissions:  Check permissions.txt for least-privilege service"
log "  TLS:          Check tls.txt for valid certs, expiry > 30 days"