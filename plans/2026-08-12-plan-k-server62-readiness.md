# Plan K — server62 Production Readiness

**Status:** active
**Milestone:** M0–M5
**Owner:** server sysadmin; product engineering verifies application requirements
**Last verified:** 2026-08-13

## Objective and authority

Make s62 and the s61→s62 delivery path safe for the Jan pilot, while preserving
tenant data and producing reproducible as-built evidence. Host remediation and
synthetic readiness may proceed now. Portal scaffolding, PostgreSQL activation for
the portal, and deployment remain blocked until Plan E accepts ADR-001.

The repository-safe snapshot is
[`docs/operations/sysadmin-readiness-2026-08-12.md`](../docs/operations/sysadmin-readiness-2026-08-12.md).
Re-probe volatile facts before every mutation. Cross-host/hypervisor procedures
remain in `/workspace/servers-infra/plans/2026-08-11-proxmox-recovery-backup-resize.md`.

## Corrected observed baseline

- `/` is about 93% full with about 6.7 GiB free; VG free space is insufficient
  for an online guest-only extension. Required gate: at least 15 GiB **and** 15%
  free on `/` and `/var/lib/docker`.
- The earlier unbounded root `du` probe blocked in kernel I/O wait and was
  terminated. Never repeat `du -x -d1 /`; probe bounded target paths separately.
- `prace-v-nemecku.tvoje.info` already resolves to `89.203.173.196`; only
  `portal.prace-v-nemecku.tvoje.info` is absent.
- s61 Traefik is the public edge. The existing s61→s62 `tvoje.info` chain is
  down: nginx fails because `/run/nginx/nginx.pid` has no matching
  `RuntimeDirectory`, PM2 has no apps, and nothing listens on 3010/8097.
- PostgreSQL 18 is installed and cluster `18/main` exists but is down. Do not
  reinstall, upgrade, or drop it.
- Alertmanager is active on port 1062 but Prometheus has no Alertmanager target.
  Rules exist in `/etc/prometheus/` while the configured glob points to a missing
  rules directory. SMTP points at dead localhost:25. Blackbox exporter is active
  on `127.0.0.1:9115`.
- Borg is installed and `/var/backups/borg/s62` on s60 is a working encrypted
  repository. Backup activation is mandatory before real portal data.

## Execution phases

### K0 — Freeze, prove identity, and capacity

1. Capture `prove-state.py` baseline and exact VM identity from Proxmox/MAC
   evidence; do not rely on generic guest DMI.
2. Use bounded probes only:

   ```bash
   scripts/ssh62 'df -hT / /var/lib/docker; df -i / /var/lib/docker'
   scripts/ssh62 'sudo journalctl --disk-usage; sudo docker system df -v'
   scripts/ssh62 'for p in /var/lib/docker /opt /var/www /home/pavel; do sudo timeout 45s du -sxh "$p" 2>&1 || printf "UNPROVEN %s rc=%s\n" "$p" "$?"; done'
   scripts/ssh62 'sudo lsof +L1'
   ```

3. Reclaim only owner-approved caches, dangling images, logs, or proven orphan
   data. Never remove unknown tenant data. Journald is already bounded; retain or
   tighten it. Configure bounded Docker logging, noting daemon defaults apply to
   newly created containers.
4. Acceptance: both paths meet 15 GiB/15%, projected pilot growth fits the
   margin, logrotate debug passes, and a disk alert fires and resolves.

### K1 — Repair and prove the shared `tvoje.info` chain

1. Preserve pre-change hashes and unit/drop-in/PM2/Traefik state.
2. Keep `/run/nginx/nginx.pid` and add a managed nginx systemd drop-in with
   `RuntimeDirectory=nginx` and `RuntimeDirectoryMode=0755`; keep nginx `pid` and
   unit `PIDFile` identical.
3. Migrate the existing Next app from PM2 fork mode to a dedicated non-login
   systemd identity. Use an absolute runtime path, root-owned environment file,
   restart bounds, and narrow writable directories. Do not reuse its ports for
   the Django portal.
4. Validate in order:

   ```bash
   systemd-analyze verify nginx.service
   sudo nginx -t
   curl --max-time 5 http://127.0.0.1:3010/ready
   curl --max-time 5 -H 'Host: tvoje.info' http://192.168.1.62:8097/ready
   nc -zvw5 192.168.1.62 8097
   ans/scripts/diagnostics/traefik-trace.sh tvoje.info
   ```

5. Repeat after a controlled reboot. Router registration alone is not proof.

For any new reusable readiness script, accept `--check`/dry-run where meaningful,
bound every SSH/network/filesystem probe, and use exit codes `0=pass`,
`1=confirmed failure`, `2=unproven`. End output with a JSON `next_actions` array
containing `when`, `command`, `purpose`, and `severity`; a HARD failure must say
not to auto-fix. Store regenerable live output in ignored operational/live-state
paths, print the output path, and test the intended `git check-ignore` behavior.

### K2 — Monitoring and alert delivery

1. Fix Prometheus rule loading by aligning `rule_files` with the existing files;
   configure the existing Alertmanager as a target.
2. Configure Telegram using SOPS-managed `bot_token_file` and numeric `chat_id`.
   Alertmanager 0.27 does not support `chat_id_file`. Restrict its all-interface
   bind to the required LAN/Tailscale surface.
3. Validate with `promtool check config`, `promtool check rules`,
   `amtool check-config`, health/ready endpoints, and controlled firing/resolution
   of disk, service, TLS, and backup-staleness alerts. Human receipt is required.

### K3 — Mandatory backup and restore gate

1. Before any real portal data, define protected paths, RPO/RTO, retention, key
   custody, and alert ownership. Create an application-consistent PostgreSQL
   logical dump plus a protected-file manifest, then archive to s60.
2. Installed Borg uses positional repository syntax:

   ```bash
   scripts/ssh60 'sudo bash -lc '\''set -a; . /etc/default/borgmatic-passphrase; set +a; borg info /var/backups/borg/s62'\'''
   scripts/ssh60 'sudo bash -lc '\''set -a; . /etc/default/borgmatic-passphrase; set +a; borg check /var/backups/borg/s62'\'''
   scripts/ssh60 'sudo bash -lc '\''set -a; . /etc/default/borgmatic-passphrase; set +a; borg extract --dry-run "/var/backups/borg/s62::ARCHIVE_NAME"'\'''
   ```

   Load the existing passphrase environment without printing it. `borg check
   --repair`, pruning, deletion, and compaction require separate approval.
3. Perform an isolated actual restore into temporary paths/database, run schema
   and application queries, record elapsed time against RTO, then remove the test
   restore only after approval.
4. Acceptance: fresh archive, integrity check, isolated file/DB restore,
   application-level validation, and failure/staleness alert all pass. This proof
   is referenced by `docs/security/real-data-rules.md`.

### K4 — PostgreSQL and portal commissioning after ADR-001 acceptance

1. Inspect `pg_lsclusters`, `start.conf`, configuration, and logs; start the
   existing 18/main cluster through Debian systemd/`pg_ctlcluster`.
2. Bind loopback only. Use a NOLOGIN owner, a migration LOGIN role able to set
   role for DDL, and a restricted runtime LOGIN role. Explicitly deny superuser,
   createdb, createrole, replication, and bypass-RLS.
3. Deploy Django and the worker under dedicated systemd identities with a new
   loopback app port and separate LAN nginx port. Keep TLS termination on s61 and
   firewall the backend to s61 only.
4. Acceptance: cluster online and boot-persistent, listeners local-only,
   unrelated logins denied, migration and CRUD smoke pass, service restart/reboot
   pass, and rollback preserves the data directory. Never use `pg_dropcluster`.

### K5 — Portal DNS/TLS after backend health

1. Leave the existing apex record unchanged. Add GoDaddy A record
   `portal.prace-v-nemecku` → `89.203.173.196` only after the private route passes.
2. Add a separate s61 Traefik Host router and service with the existing ACME
   resolver and a real readiness health check.
3. Acceptance: authoritative and recursive DNS agree; HTTP redirects; certificate
   SAN exactly includes the portal name; public health/application/static routes
   pass; restart preserves ACME and routing state.

## Rollback and exit gate

- Restore exact previous app release, nginx unit/config pair, and Traefik file;
  validate before reload. Preserve PostgreSQL data and backup repositories.
- Required exit evidence: capacity, chain/reboot proof, alert delivery,
  backup/restore proof, permissions, bindings, TLS, service versions, rollback
  references, and remaining risks—without credentials.
- New real-data uploads remain disabled until the sole activation gate in
  `docs/security/real-data-rules.md` passes, including mandatory restore proof.
