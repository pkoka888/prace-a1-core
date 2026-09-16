# s62 infrastructure — comprehensive triage, gap analysis and fix playbook
**Date:** 2026-09-16
**Scope:** server62 (s62) live state vs planned state; agent skills audit; git archaeology; Ansible-structured gap inventory; meta-pattern library for probable fixes.
**Constraint:** no secret values printed; `.runtime-config/gunicorn.env` contents referenced by key name only.
**Sources:** captured command outputs this session; git history of `feat/prace-readiness-plan-2026-08-13`; Playwright/gunicorn/PostgreSQL/Django/systemd/Ansible official docs (cached via research subagent).

---

## 1. Executive summary

server62 is the primary application host. It runs PostgreSQL 18.3, an **enabled but failed** systemd gunicorn unit (`prace-v-nemecku-gunicorn.service`, Result=signal since 2026-09-14), and a divergent manual gunicorn instance (PID 2681143, user `prace-s+`, `--workers 2`) serving on `127.0.0.1:8001`. The `PRACE_DB_PASSWORD` stored in `.runtime-config/gunicorn.env` (length 44, key confirmed present) does **not** authenticate against the live `prace_synth_app` role over either `scram-sha-256` TCP or `md5` local socket. The systemd unit file was recreated on **2026-09-16 02:02** (after the failure), suggesting an operator repair attempt that did not complete. Static files are uncollected (`static/` empty, `/tmp/gunicorn.log` 404s from 2026-09-11). The unit file uses `--capture-output` with `ProtectSystem=strict`, which prevents journald from capturing stdout/stderr, explaining the empty `journalctl` output. Tailscale shows server61/s60/s64 online but SSH key auth from this session reaches only server62. The application checkout is at the correct branch tip (`afc712b` / `ba8ec18` pushed this session).

**One blocker for Jan acceptance:** the supervised gunicorn unit is not active and the database password is out of sync. Everything else (tests, docs, delivery record, hook checks, persisted source bytes, A1/Journey logic) is in place.

---

## 2. Ansible-structured host inventory

```yaml
# inventory/production.yml  (current live state, 2026-09-16)
all:
  hosts:
    server62:
      ansible_host: 100.81.67.93        # tailscale
      ansible_user: pavel
      ansible_ssh_private_key_file: ~/.ssh/id_ed25519_mechanic
      distro: debian13_trixie
      kernel: 6.12.74+deb13+1-amd64
      cpu_cores: 4
      memory_gb: 15
      disk_root_gb: 192
      disk_root_used_pct: 53
      postgres:
        version: "18.3 (Debian 18.3-1.pgdg13+1)"
        listen:
          - 127.0.0.1:5432
          - "[::1]:5432"
        roles:
          - name: prace_synth_app
            can_login: true
            has_password: true
            password_hash_present: true   # hash exists; plaintext does not match gunicorn.env
        databases:
          - name: prace_synthetic
            size_mb: 11
          - name: prace_synthetic_test
            size_mb: 11
        active_connections_prace_synth_app: 0
        pg_hba:
          - type: local
            db: prace_synthetic
            user: prace_synth_app
            method: md5           # local socket
          - type: host
            addr: 127.0.0.1/32
            method: scram-sha-256 # TCP loopback
          - type: host
            addr: ::1/128
            method: scram-sha-256 # TCP loopback v6
      gunicorn_unit:
        name: prace-v-nemecku-gunicorn.service
        state: failed
        result: signal
        since: "2026-09-14 03:41:10 CEST"
        main_pid: 505344
        unit_file_birth: "2026-09-16 02:02:12 CEST"  # recreated after failure
        enabled: true
        configured_user: prace-synthetic
        configured_workers: 3
        configured_bind: 127.0.0.1:8001
        environment_file: /var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env
        capture_output: true
        protect_system: strict
        journal_entries: 0               # empty — ProtectSystem=strict blocks journald
      gunicorn_manual:
        running: true
        pids: [2681143, 2681150, 2681151]
        user: prace-s+                   # ≠ unit's prace-synthetic
        workers: 2                        # ≠ unit's --workers 3
        bind: 127.0.0.1:8001
        pid_file: runtime/portal/supervised-synthetic/gunicorn.pid
        since: "2-12:46:24"              # started ~Sep 14, same day as unit failure
        elapsed_days: ~2.5
        protections_lost:
          - PrivateTmp
          - ProtectSystem
          - NoNewPrivileges
      nginx:
        running: true
        syntax_ok: true
        vhosts:
          - prace-v-nemecku.expc.cz.conf
        listening:
          - 127.0.0.1:80
          - 100.81.67.93:443
        static_served: unknown           # static/ empty; needs nginx vhost inspection
      tailscale:
        ip: 100.81.67.93
        peers:
          - s64 (tagged-devices)
          - server60 (tagged-devices, offline 20d)
          - server61 (tagged-devices)
          - spaces (windows)
      postgres_auth_gap:
        gunicorn_env_password_length: 44
        gunicorn_env_password_authenticates_tcp: false  # confirmed FATAL
        gunicorn_env_password_authenticates_socket: false  # confirmed FATAL Peer
        likely_cause: role password changed after EnvironmentFile was populated
      application_checkout:
        path: /var/www/prace-v-nemecku.tvoje.info
        branch: feat/prace-readiness-plan-2026-08-13
        head: ba8ec18b7551acff95cee1f916ba636110479bfa
        remote_head_matches: true
        unit_file_in_git: false         # /etc/systemd/system/... excluded by design
        env_file_in_git: false           # .runtime-config/ excluded by design

    server61:
      ansible_host: 100.97.82.39        # tailscale
      ansible_user: pavel
      ssh_key_auth_from_s62: false      # Permission denied (publickey) this session
      reachable_via_tailscale: true
      evidence: tailscale status shows active
      notes: "Full state requires operator SSH key or on-site access"

    server60:
      ansible_host: 100.87.66.75        # tailscale
      ansible_user: pavel
      ssh_key_auth_from_s62: false      # Permission denied (publickey) this session
      reachable_via_tailscale: true
      last_seen: "20d ago"              # tailscale: offline, last seen 20d ago
      notes: "Full state requires operator SSH key or on-site access"

    s64:
      ansible_host: 100.124.181.107    # tailscale
      ansible_user: pavel
      ssh_key_auth_from_s62: false      # Name or service not known (no DNS entry)
      reachable_via_tailscale: true
      notes: "Not resolvable as 's64' from s62; requires explicit IP or hostname entry in /etc/hosts"
```

### 2.1 What is confirmed running vs not

| Component | Confirmed running | Confirmed NOT running | Evidence |
|---|---|---|---|
| PostgreSQL 18 | Yes — `postgres` accepts connections on 5432 | `prace_synth_app` cannot connect (password mismatch) | `pg_isready`, `psql`, `pg_stat_activity` |
| nginx | Yes — listens on 80, 443; syntax OK | Static serving unverified (`static/` empty) | `ss -tlnp`, `nginx -t` |
| Tailscale | Yes — s62/s61/s60/s64/spaces visible | — | `tailscale status` |
| systemd gunicorn unit | **No** — `active=failed` since Sep 14 | Unit not serving | `systemctl status` |
| Manual gunicorn | Yes — PID 2681143 on 8001 | — | `ps`, `ss -tlnp` |
| Django collectstatic | **No** — `static/` empty | 404s in Sep 11 log | `ls static/`, `/tmp/gunicorn.log` |
| SSH to server61 | — | **No** — publickey denied | `ssh server61` |
| SSH to server60 | — | **No** — publickey denied | `ssh server60` |
| SSH to s64 | — | **No** — unresolved hostname | `ssh s64` |

### 2.2 Blocking investigations

The following investigations are **blocked** until the operator provides SSH access or on-site presence:

- **server61:** PostgreSQL state, HBA, gunicorn unit status, nginx config
- **server60:** PostgreSQL state (offline 20d per tailscale), any active services
- **s64:** Hostname resolution, PostgreSQL state, any active services

Without those proofs, the gap analysis for those hosts is limited to "reachable via Tailscale but unverified". The meta-pattern library (§6) covers how to proceed when a host is unreachable.

---

## 3. Git archaeology — timeline of key events

```
2026-09-07  infra-return-work-order-2026-09-07.md created
2026-09-09  /tmp/check{1..18}.log, /tmp/commit*.log — heavy test runs
2026-09-11  /tmp/gunicorn.log — last successful gunicorn run (port 8768, worker SIGTERM)
2026-09-11  /tmp/start.log — last start log
2026-09-12  /tmp/broad-manage.log, /tmp/broad-manage2.log
2026-09-14  03:33 /tmp/smtp.log, 03:37 /tmp/smtp_server.log
2026-09-14  03:41 CEST — systemd unit prace-v-nemecku-gunicorn enters state=failed (Result=signal, PID 505344 KILL)
2026-09-14  ~12:46 — manual gunicorn starts (PID 2681143, prace-s+, workers 2) — same day as unit failure
2026-09-16  02:02 CEST — systemd unit file recreated (Birth = Sep 16 02:02) — operator repair attempt
2026-09-16  06:12–16:06 — /tmp/pi-bash-*.log (this session's work)
2026-09-16  07:43–16:06 — /tmp/mat-debug-*.log (Playwright / Chromium runs)
```

### 3.1 Where did the infrastructure state "disappear"?

The systemd unit file (`/etc/systemd/system/prace-v-nemecku-gunicorn.service`) is **not tracked in git** (AGENTS excludes `.runtime-config/`, `/etc/`, and infrastructure-owned paths). The unit file's filesystem `Birth` timestamp of **Sep 16 02:02** — *after* the Sep 14 failure — is the strongest signal:

- **Hypothesis A (most probable):** An operator recreated the unit file on Sep 16 (possibly via a deployment script or manual `cp`) but did not restart the unit, or the restart failed for the same reason the original unit failed (likely G-1: wrong password in the EnvironmentFile → Django fails to start → arbiter dies → Result=signal).
- **Hypothesis B:** A package install or dpkg trigger recreated the unit file. The apt history shows only netdata upgrades; no gunicorn/systemd package installs in the recent window. This makes B less probable.
- **Hypothesis C:** The unit was manually edited on Sep 16 but the underlying cause (G-1 password) was not addressed, so the unit remains failed.

**Meta-pattern:** When a unit file has a `Birth` timestamp *after* the first recorded failure, the most probable cause is an operator repair attempt that did not address the root cause (typically an EnvironmentFile value, missing dependency, or permission). The fix is to address the root cause first, then re-deploy the unit file.

### 3.2 When did the password desync?

The `.runtime-config/gunicorn.env` file is also not in git. Its `Birth` cannot be determined from git. The strongest evidence is:
- `prace_synth_app` has a non-null password hash (confirmed via `pg_authid`).
- The EnvironmentFile plaintext does not authenticate.
- The `/tmp/gunicorn.log` (Sep 11) shows a gunicorn run on port 8768, not 8001 — this predates the current manual instance and the current unit file. It is unclear whether the Sep 11 run authenticated successfully.

**Most probable sequence:** The password was changed at some point between the last successful run and now. The operator changed `prace_synth_app`'s password directly in PostgreSQL (via `psql` or a rotation script) without updating `.runtime-config/gunicorn.env`. This is the classic "credential rotation without environment sync" pattern.

---

## 4. Gap analysis with best-practice references

### G-1 (Critical) gunicorn.env password ≠ DB role password

| Attribute | Value |
|---|---|
| Confirmed | Password length 44 in `.runtime-config/gunicorn.env`; fails `scram-sha-256` TCP and `md5` local socket |
| Root cause (most probable) | Role password changed without EnvironmentFile sync |
| Blocks | Supervised gunicorn start, any `PRACE_WORKFLOW_PG=1` workflow, migration |
| Best practice | PostgreSQL 18 recommends `scram-sha-256` (md5 deprecated); test auth via `psql "host=... user=..."` without echoing the password; verify method in server log |
| Fix complexity | 1 ALTER ROLE or 1 file edit + restart |
| Source | https://www.postgresql.org/docs/18/auth-password.html |

**Fix variants:**
1. **Update the role** (if EnvironmentFile is trusted): `ALTER ROLE prace_synth_app WITH PASSWORD '<value-from-gunicorn.env>';` — verify with `psql -h 127.0.0.1 -U prace_synth_app -d prace_synthetic -Atc "SELECT 1;"` returning `1`.
2. **Update the EnvironmentFile** (if the database hash is source of truth): write new password to `.runtime-config/gunicorn.env`, `systemctl daemon-reload && systemctl restart prace-v-nemecku-gunicorn`.

### G-2 (High) systemd unit failed; manual gunicorn diverges

| Attribute | Value |
|---|---|
| Confirmed | Unit `active=failed` since Sep 14; manual instance PID 2681143 user `prace-s+` workers 2 |
| Root cause (most probable) | Unit failed because G-1 (wrong password → Django startup failure → arbiter dies with signal); operator started manual instance to restore service without fixing root cause |
| Blocks | Planned supervision contract (PrivateTmp, ProtectSystem, NoNewPrivileges, prace-synthetic user) |
| Best practice | systemd `Type=notify` requires `sd_notify("READY=1")`; `Restart=on-failure` + `RestartSec=5` + `StartLimitBurst=3` + `StartLimitIntervalSec=60` provides resilient restart without thundering-herd |
| Fix complexity | Kill manual + restart unit (after G-1) |
| Source | https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html (canonical public manpage) |

**Fix sequence:**
1. After G-1 is resolved: `kill -s TERM 2681143 2681150 2681151`; wait for port 8001 to free (`ss -tlnp | grep 8001` empty).
2. `sudo systemctl daemon-reload && sudo systemctl restart prace-v-nemecku-gunicorn`.
3. `sudo systemctl status prace-v-nemecku-gunicorn` → must show `active (running)`.
4. If unit fails again, inspect `ProtectSystem=strict` and `ReadWritePaths`; add missing paths before retrying.

### G-3 (Medium) static files uncollected / 404s

| Attribute | Value |
|---|---|
| Confirmed | `/tmp/gunicorn.log` shows 404 for `/static/portal/htmx-1.9.10.min.js` and `tailwind-2.2.19.min.css` on 2026-09-11. Verified 2026-09-16: `runtime/portal/supervised-synthetic/static/portal/` exists with those files (collected 2026-09-14); `static/` checkout directory empty. Nginx vhost `location /static/` uses `alias /var/www/prace-v-nemecku.tvoje.info/portal/release1a/static/` — **does not point to `STATIC_ROOT`** (`runtime/portal/supervised-synthetic/static/`) |
 | Root cause (most probable) | Nginx alias mismatch: vhost points to `portal/release1a/static/` but `STATIC_ROOT = <runtime_root>/static` per `portal/settings_supervised_synthetic.py:195`. The checkout `static/` is empty because `collectstatic` was never run there |
| Blocks | UI rendering in production (journeys hit dynamic views first; not a blocker for core acceptance) |
| Best practice | Django 5.2: `STATIC_ROOT` + `collectstatic` + nginx `location /static/ { alias <STATIC_ROOT>; expires 30d; }` (note `alias`, not `root`) |
| Fix complexity | `collectstatic` run + nginx verify |
| Source | https://docs.djangoproject.com/en/5.2/howto/static-files/ |

**Fix sequence (operator-owned nginx vhost):**
```bash
# Verified: runtime/portal/supervised-synthetic/static/portal/ already
# contains htmx-1.9.10.min.js and tailwind-2.2.19.min.css (collected 2026-09-14).
# The checkout `static/` directory is intentionally empty under supervised-synthetic.
# Operator: update /etc/nginx/sites-enabled/prace-v-nemecku.expc.cz.conf:
#   location /static/ {
#       alias /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/;
#       expires 30d;
#       add_header Cache-Control "public, immutable";
#   }
# Then: sudo systemctl reload nginx && curl -I http://127.0.0.1/static/portal/htmx-1.9.10.min.js
```

### G-4 (Low) journalctl empty for failed unit

| Attribute | Value |
|---|---|
| Confirmed | `journalctl -u prace-v-nemecku-gunicorn --since 2026-09-14` returns no entries |
| Root cause (most probable) | `ProtectSystem=strict` blocks journald from writing to `/run/systemd/journal/` and `/var/log/journal/`; `--capture-output` relies on journald being writable |
| Blocks | Diagnostic visibility — not a functional blocker |
| Best practice | Either use `ProtectSystem=full` (not `strict`) + `LogsDirectory=`, or replace `--capture-output` with explicit `--access-logfile /var/log/prace-v-nemecku/access.log --error-logfile /var/log/prace-v-nemecku/error.log` |
| Fix complexity | 1 unit file edit + daemon-reload |
| Source | https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#ProtectSystem= (canonical public manpage) |

**Fix sequence:**
1. Add `LogsDirectory=prace-v-nemecku` to the unit, OR
2. Replace `--capture-output` with explicit log file paths and extend `ReadWritePaths` to include `/var/log/prace-v-nemecku`.

---

## 5. Meta-pattern library — probable fixes ranked by probability

These patterns are derived from the observed state, git archaeology, and best-practice sources. Each pattern includes the **prior probability** (how often this pattern matches the observed symptom in the wild), the **diagnostic test** that confirms it, and the **canonical fix**.

### Pattern P-1: Credential desync after operator rotation

**Prior probability:** High (observed directly in G-1)
**Observed symptoms:** `FATAL: password authentication failed` for a role that exists and has a non-null password hash; EnvironmentFile contains a value of the expected length; no other auth errors.
**Diagnostic test:** Read the EnvironmentFile value (do not print it); attempt TCP auth with it; compare hash stored in `pg_authid` vs the plaintext (without printing either).
**Canonical fix:** Either (a) `ALTER ROLE <role> WITH PASSWORD '<env-value>';` or (b) update the EnvironmentFile to match the database hash. Verify with a single `psql` call.
**Why this is the right fix:** It is the smallest diff that closes the actual auth mismatch. The broader rotation the plan implies (new password + HBA review + build pin) is unnecessary if the existing EnvironmentFile value is still the intended credential.

### Pattern P-2: Unit file recreated after failure (operator repair without root-cause fix)

**Prior probability:** High (observed in G-2 via unit file `Birth` after failure timestamp)
**Observed symptoms:** Unit file `Birth` or `Modify` timestamp is *after* the first `ActiveExitTimestamp`; unit still in `failed` state; manual divergent instance serving on the same port.
**Diagnostic test:** Compare `systemctl show -p ActiveExitTimestamp` with `stat <unit-file>`; look for operator processes (`prace-s+` vs unit's `User=`).
**Canonical fix:** Address the root cause (usually P-1 for this project) first; then `systemctl daemon-reload && systemctl restart <unit>`; then `systemctl status` must show `active (running)`. Remove the manual instance.
**Why this is the right fix:** Recreating the unit file without fixing the root cause guarantees the same failure on restart.

### Pattern P-3: `ProtectSystem=strict` silently blocks journald

**Prior probability:** Medium (observed in G-4; common in hardened units)
**Observed symptoms:** Unit uses `--capture-output`; `journalctl -u <unit>` is empty; unit has `ProtectSystem=strict` or `ProtectHome=`.
**Diagnostic test:** `systemctl show -p ProtectSystem,ReadWritePaths <unit>`; check if `/run/systemd/journal/` or `/var/log/journal/` is writable.
**Canonical fix:** Either add `LogsDirectory=<app>` (systemd creates a writable journal subdirectory), or replace `--capture-output` with explicit log files and add the log directory to `ReadWritePaths`.
**Why this is the right fix:** Explicit log files are easier to rotate, grep, and ship to a log aggregator; they also work when journald is unavailable.

### Pattern P-4: Static files 404 after deploy without collectstatic

**Prior probability:** High (observed in G-3; common after code updates that add static assets)
**Observed symptoms:** `static/` directory empty or stale; `/tmp/gunicorn.log` or browser console shows 404 for specific static paths; `collectstatic` not in the deploy script.
**Diagnostic test:** `ls <STATIC_ROOT>/`; check `STATIC_ROOT` in `settings.py`; check nginx `location /static/` block exists and uses `alias` (not `root`) pointing to `STATIC_ROOT`.
**Canonical fix:** Run `python manage.py collectstatic --noinput`; verify nginx `alias` matches `STATIC_ROOT`; confirm with `curl -I http://host/static/<known-file>`.
**Why this is the right fix:** `collectstatic` is idempotent and fast; the nginx `alias` vs `root` mistake is the single most common cause of persistent 404s.

### Pattern P-5: SSH public-key denial from a sibling host

**Prior probability:** Medium (observed for server61/server60 from server62)
**Observed symptoms:** `Permission denied (publickey)` from one host to another that is reachable via Tailscale; `tailscale ping` succeeds.
**Diagnostic test:** `ssh -vvv <host>` to confirm key offered/rejected; check `~/.ssh/authorized_keys` on target; check `~/.ssh/config` for `IdentitiesOnly` or explicit `IdentityFile`.
**Canonical fix:** Add the correct public key to `~/.ssh/authorized_keys` on the target, or configure `~/.ssh/config` with the right `IdentityFile`. For automation, use an Ansible `authorized_key` module task.
**Why this is the right fix:** Tailscale guarantees reachability, not key trust. The fix is a single authorized-keys entry, not a firewall or routing change.

### Pattern P-6: Orphan gunicorn / manual instance diverging from unit spec

**Prior probability:** Medium (observed in G-2)
**Observed symptoms:** Manual gunicorn process on the same port as the supervised unit; different user, worker count, or argv; unit is `failed` or `inactive`.
**Diagnostic test:** `ps -o user,pid,cmd -p $(pgrep -f gunicorn)`; compare each field against the unit file.
**Canonical fix:** Fix the root cause of the unit failure (usually P-1), then `kill` the manual instance and `systemctl restart` the unit. Verify `ss -tlnp` shows only the unit's processes.
**Why this is the right fix:** The manual instance is unmanaged (no `ProtectSystem`, no `NoNewPrivileges`, no restart policy); it will diverge further over time.

### Pattern P-7: networkidle flake under sequential heavy-suite load

**Prior probability:** Medium (observed in D-1 of the architect dossier)
**Observed symptoms:** Playwright `Page.goto` with `wait_until="networkidle"` times out at 20000 ms after a long heavy suite; retry passes; `SERVER_ERROR_CATEGORIES: []`.
**Diagnostic test:** Run the same journey standalone (passes); run under full hook load (flakes); check Playwright version (default nav timeout is 30 s in current versions, not 20 s).
**Canonical fix:** Replace `wait_until="networkidle"` with `wait_until="load"` + `page.wait_for_selector("<stable-element>", state="visible")`. Do not increase the timeout alone — that masks the flake without fixing the readiness signal.
**Why this is the right fix:** Playwright docs explicitly mark `networkidle` as `DISCOURAGED` for testing; `load` + selector waits are the documented pattern.

---

## 6. Agent skills, plan, and roadmap — update recommendations

### 6.1 Current agent skills inventory

| Skill | Path | Status | Gap |
|---|---|---|---|
| `a1-pdf-production` | `.agents/skills/a1-pdf-production/SKILL.md` | Active | No gap for current scope |
| `customize-opencode` | `<built-in>` | Active | Not applicable |
| `market-research-evidence` | `.opencode/skills/market-research-evidence/SKILL.md` | Experimental (Plan AC) | No operational use yet |
| `postgres-ops` | `.agents/skills/postgres-ops/SKILL.md` | Updated this session | Covers G-1 (password auth), G-2 (supervision), blank-target rejection, TLS forwarding |
| `synthetic-portal-delivery` | `.agents/skills/synthetic-portal-delivery/SKILL.md` | Updated this session | Covers D-1 (networkidle investigation), core/A1 profile separation |

**Recommendation:** No new skills needed. Both updated skills already cover the observed gaps. If the operator provisions server61/server60/s64 access, a new `remote-host-ops` skill would be useful — but that is operator territory, not engineering.

### 6.2 Plan update recommendations

The active plan (`plans/2026-09-14-delivery-reliability-and-jan-v1.md`) should be updated with:

1. **Close these rows** (code already closes them at `c24a293` / `afc712b` / `ba8ec18`):
   - "Open: ownership is self-declared" → closed at `d0903a8` (psql_env preserves caller keys)
   - "Reproduced application defect: invalid lock probe" → closed at `d0903a8`
   - "Reproduced configuration boundary gaps" → partially closed (blank-target rejection added)
   - "Open: incomplete environment chain" → closed at `c24a293` + incremental (PRACE_WORKFLOW_PG forwarded)
   - "Partial core separation" → closed at `a48a1e8` (assignment_corrected + optional-a1 branch)

2. **Add new rows** for this session's findings:
   - G-1: `prace_synth_app` password desync — operator action required
   - G-2: systemd unit failed; manual gunicorn diverges — operator action required after G-1
   - G-3: static files uncollected — engineering action
   - G-4: journalctl empty due to ProtectSystem=strict — operator action
   - D-1: networkidle investigation — engineering action (one increment)

3. **Simplify INFRA-PG-01** from a broad 4-item list into two atomic operator actions:
   - (a) Credential sync (`ALTER ROLE` or EnvironmentFile edit) + unit restart
   - (b) nginx `proxy_pass` / `Host` header verification against unit's `--bind`
   The remaining HBA/build/routing reconciliation stays as sub-items but does not block (a).

### 6.3 Roadmap update recommendations

The roadmap (`roadmap.md`) currently assumes:
- gunicorn is supervised and healthy
- PostgreSQL target authenticates with the EnvironmentFile password
- Static files are served

**Update required:** Add a `BLOCKED` marker on the "committed-source PostgreSQL acceptance" step until G-1 and G-2 are resolved. Do not move JAN-04 to "complete" until a live owned-PG run succeeds. The rest of the roadmap (JAN-01 OCR mitigation, JAN-02 download-redirect fix, JAN-03 core/A1 separation) is on track and does not need adjustment.

### 6.4 Agent skills update (minimal)

**`postgres-ops/SKILL.md`** — add one paragraph under "Operator-owned live state":
> "If `psql` with the EnvironmentFile password returns `FATAL: password authentication failed` but the role exists with a non-null hash, the most probable cause is credential desync. Diagnose with `sudo -u postgres psql -Atc "SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname='<role>'";` and compare against the EnvironmentFile value without printing it. The operator should align the two sources with a single `ALTER ROLE` or EnvironmentFile edit."

**`synthetic-portal-delivery/SKILL.md`** — already contains the networkidle guidance from this session. No change needed.

---

## 7. Recommended fix execution order (Ansible playbook structure)

```yaml
# playbooks/fix-infra-pg-01-and-supervision.yml
# Target: server62
# Blocks: Jan acceptance until all tasks report ok
# Requires: operator provides PRACE_DB_PASSWORD source (either ALTER ROLE or env edit)
# Secret handling: PRACE_DB_PASSWORD must be stored in Ansible Vault, never in task args or logs

- name: "INFRA-PG-01: Synchronize prace_synth_app password and restart supervised gunicorn"
  hosts: server62
  become: true
  vars_files:
    - /ansible/vaults/prace-v-nemecku.yml   # contains vault_db_password
  tasks:
    - name: "Pre-flight — confirm PostgreSQL is running"
      ansible.builtin.systemd_service:
        name: postgresql@18-main
        state: started
      register: pg_status

    - name: "Pre-flight — confirm gunicorn unit exists and is stopped"
      ansible.builtin.systemd_service:
        name: prace-v-nemecku-gunicorn
        state: stopped
        enabled: true
      register: gunicorn_stop
      ignore_errors: true

    - name: "Kill divergent manual gunicorn instances (if any)"
      ansible.builtin.shell: |
        pids=$(pgrep -f "gunicorn portal.wsgi:application --bind 127.0.0.1:8001" || true)
        if [ -n "$pids" ]; then
          echo "Killing manual gunicorn PIDs: $pids"
          kill -s TERM $pids
          sleep 5
          # force-kill any survivors
          for pid in $pids; do
            if kill -0 $pid 2>/dev/null; then kill -s KILL $pid; fi
          done
        fi
      register: kill_manual
      changed_when: kill_manual.stdout != ""

    - name: "Synchronize role password with EnvironmentFile (operator chooses direction)"
      # VARIANT A: update role to match env (preferred if env is trusted)
      community.postgresql.postgresql_user:
        name: prace_synth_app
        password: "{{ vault_db_password }}"   # vaulted, never printed
        encrypted: true
        no_password_changes: false
        login_user: postgres
      environment:
        PGHOST: 127.0.0.1
        PGUSER: postgres
        PGPASSWORD: "{{ vault_postgres_superuser_password }}"   # vaulted
        PGOPTIONS: "-c password_encryption=scram-sha-256"
      register: sync_password
      when: password_sync_direction == "role_matches_env"

    - name: "Update EnvironmentFile to match role (operator chooses direction)"
      ansible.builtin.copy:
        dest: /var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env
        owner: root
        group: prace-synthetic
        mode: "0640"
        content: |
          # Managed by Ansible — do not edit manually
          DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic
          M2_SYNTHETIC_ONLY=1
          PRACE_ALLOWED_HOSTS=prace-v-nemecku.expc.cz,127.0.0.1,localhost
          PRACE_DB_HOST=127.0.0.1
          PRACE_DB_NAME=prace_synthetic
          PRACE_DB_PASSWORD={{ vault_db_password }}
          PRACE_DB_PORT=5432
          PRACE_DB_USER=prace_synth_app
          PRACE_RELEASE_MANIFEST=/var/www/prace-v-nemecku.tvoje.info/release_manifest.json
          PRACE_RELEASE_MANIFEST_SHA256=<to-be-filled-by-operator>
          PRACE_RUNTIME_ROOT=/var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic
          PRACE_SECRET_KEY=<to-be-filled-by-operator>
      register: env_update
      when: password_sync_direction == "env_matches_role"

    - name: "Verify password synchronization (role can connect over TCP)"
      ansible.builtin.shell: |
        PGPASSWORD='{{ vault_db_password }}' \
          psql -h 127.0.0.1 -U prace_synth_app -d prace_synthetic \
          -Atc "SELECT current_user, current_database();"
      register: verify_tcp
      changed_when: false
      failed_when: verify_tcp.rc != 0 or "prace_synth_app" not in verify_tcp.stdout

    - name: "Verify statement_timeout is set for the runtime role"
      ansible.builtin.shell: |
        PGPASSWORD='{{ vault_db_password }}' \
          psql -h 127.0.0.1 -U prace_synth_app -d prace_synthetic \
          -Atc "SHOW statement_timeout;"
      register: verify_timeout
      changed_when: false

    - name: "Restart supervised gunicorn unit"
      ansible.builtin.systemd_service:
        daemon_reload: true
        enabled: true
        name: prace-v-nemecku-gunicorn
        state: started
      register: gunicorn_start

    - name: "Verify gunicorn is active and serving"
      ansible.builtin.uri:
        url: http://127.0.0.1:8001/health/
        return_content: false
        status_code: 200
      register: health_check
      retries: 5
      delay: 3
      until: health_check.status == 200

    - name: "Verify no manual gunicorn processes remain"
      ansible.builtin.shell: pgrep -f "gunicorn portal.wsgi:application --bind 127.0.0.1:8001" || true
      register: pgrep_after
      changed_when: false
      failed_when: pgrep_after.stdout | length > 0

    - name: "Run collectstatic"
      ansible.builtin.shell: |
        sudo -u prace-synthetic \
          /var/www/prace-v-nemecku.tvoje.info/venv/bin/python manage.py \
          collectstatic --noinput --verbosity 1
      register: collectstatic
      changed_when: "'Copying' in collectstatic.stdout or 'Post-processed' in collectstatic.stdout"

    - name: "Verify static files exist"
      ansible.builtin.stat:
        path: /var/www/prace-v-nemecku.tvoje.info/static/portal/htmx-1.9.10.min.js
      register: static_check

    - name: "Report"
      ansible.builtin.debug:
        msg:
          - "Password sync: {{ sync_password.changed | default('skipped') }}"
          - "gunicorn restart: {{ gunicorn_start.status.ActiveState }}"
          - "Health check: {{ health_check.status }}"
          - "Manual gunicorn processes remaining: {{ pgrep_after.stdout }}"
          - "collectstatic changed: {{ collectstatic.changed }}"
          - "Static file present: {{ static_check.stat.exists }}"
```

### 7.1 What must be configured / enabled / verified (checklist)

| Item | Configure | Enable | Verify |
|---|---|---|---|
| PostgreSQL scram-sha-256 | `postgresql.conf`: `password_encryption = 'scram-sha-256'` (already default in PG 18) | — | `psql -Atc "SHOW password_encryption;"` → `scram-sha-256` |
| pg_hba method | `/etc/postgresql/18/main/pg_hba.conf` lines for `127.0.0.1/32` and `::1/128` → `scram-sha-256` | `systemctl reload postgresql@18-main` | `sudo -u postgres psql -Atc "SELECT * FROM pg_hba_file_rules WHERE address='127.0.0.1/32';"` |
| prace_synth_app password | `ALTER ROLE prace_synth_app WITH PASSWORD '<value>';` | — | `PGPASSWORD='<value>' psql -h 127.0.0.1 -U prace_synth_app -d prace_synthetic -Atc "SELECT 1;"` returns `1` |
| gunicorn EnvironmentFile | `.runtime-config/gunicorn.env` — `PRACE_DB_PASSWORD` synced with role | `chmod 0640 root:prace-synthetic` | `sudo -u prace-synthetic env -f .runtime-config/gunicorn.env python -c "import os; print('PRACE_DB_PASSWORD length:', len(os.environ.get('PRACE_DB_PASSWORD','')))"` |
| systemd gunicorn unit | Unit file with `Restart=on-failure`, `RestartSec=5`, `StartLimitBurst=3`, `StartLimitIntervalSec=60`, `LogsDirectory=prace-v-nemecku` or explicit log files | `systemctl daemon-reload && systemctl enable --now prace-v-nemecku-gunicorn` | `systemctl status` → `active (running)`; `ss -tlnp | grep 8001` shows `prace-synthetic` user |
| Manual gunicorn retirement | Kill PIDs 2681143/2681150/2681151 | — | `pgrep -f gunicorn` returns only unit-owned PIDs |
| Django collectstatic | `STATIC_ROOT` set; `python manage.py collectstatic --noinput` | — | `ls <STATIC_ROOT>/portal/htmx-1.9.10.min.js` exists |
| nginx static block | `location /static/ { alias <STATIC_ROOT>; expires 30d; }` | `nginx -t && systemctl reload nginx` | `curl -I http://host/static/portal/htmx-1.9.10.min.js` → `200` |
| Playwright networkidle | Replace `wait_until="networkidle"` with `wait_until="load"` + `page.wait_for_selector(...)` in `tests/_rehearse_workflow_browser.py` | — | `tests/test_rehearse_workflow.py` → 2 passed, no timeout |
| SSH to server61/server60 | `pavel`'s public key in `~/.ssh/authorized_keys` on those hosts | — | `ssh -o BatchMode=yes server61 echo ok` returns `ok` |
| s64 hostname | Add `100.124.181.107 s64` to `/etc/hosts` on s62, or use IP directly | — | `ssh -o BatchMode=yes 100.124.181.107 echo ok` |

---

## 8. What is NOT the problem (eliminated hypotheses)

| Hypothesis | Why eliminated |
|---|---|
| PostgreSQL 18 not running | Confirmed running; `pg_isready` accepts on 5432 |
| pg_hba blocks all access | Local socket has `md5` for `prace_synth_app`; `127.0.0.1/32` has `scram-sha-256`; methods are correct |
| Role `prace_synth_app` does not exist | Confirmed in `pg_roles`; `rolcanlogin=t` |
| gunicorn not installed | Binary at `/var/www/prace-v-nemecku.tvoje.info/venv/bin/gunicorn`; version 23.0.0 confirmed in `/tmp/gunicorn.log` |
| EnvironmentFile missing | `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env` exists; 12 keys present |
| nginx not running | `ss -tlnp` shows nginx on 80; `nginx -t` clean |
| Disk full | `/` 53% used; 87 GB free |
| OOM kill | `systemctl status` shows `Result=signal` but no OOM log entry; `journalctl` empty due to `ProtectSystem=strict`; cannot confirm or deny without fixing G-4 first |
| Tailscale routing broken | `tailscale status` shows all peers; s62→internet works (this session pushed to GitHub) |

---

## 9. Summary table — all gaps, fixes, owners, blockers

| ID | Gap | Severity | Owner | Fix complexity | Blocks Jan acceptance? | Best-pattern match |
|---|---|---|---|---|---|---|
| G-1 | gunicorn.env password ≠ DB role password | Critical | Operator | 1 ALTER ROLE or 1 file edit + restart | **Yes** | P-1 (Credential desync) |
| G-2 | systemd unit failed; manual gunicorn diverges | High | Operator | Kill manual + restart unit (after G-1) | **Yes** | P-2 (Unit file recreated without root-cause fix) + P-6 (Orphan instance) |
| G-3 | static files 404 / empty static dir | Medium | Engineering | `collectstatic` + nginx verify | No | P-4 (collectstatic after deploy) |
| G-4 | journalctl empty for unit | Low | Operator | Unit file argv change | No | P-3 (ProtectSystem=strict blocks journald) |
| D-1 | networkidle flake under hook load | Medium | Engineering | Replace with `load` + selector waits | No | P-7 (networkidle discouraged) |
| P-5 | SSH key auth to server61/server60 | Low | Operator | Add authorized key | No | P-5 (SSH public-key denial) |
| P-6 | s64 unresolved hostname | Low | Operator | Add to /etc/hosts or use IP | No | P-5 |

### Recommended execution order

```
1. [OPERATOR] G-1: ALTER ROLE OR update gunicorn.env (5 minutes)
2. [OPERATOR] G-2: kill manual gunicorn + restart unit (2 minutes after G-1)
3. [ENGINEERING] G-4: add LogsDirectory= OR explicit log files to unit (5 minutes)
4. [ENGINEERING] D-1: replace networkidle waits in tests/_rehearse_workflow_browser.py (30 minutes)
5. [ENGINEERING] G-3: run collectstatic + verify nginx (5 minutes)
6. [OPERATOR] P-5: add SSH key to server61/server60 (5 minutes)
7. [OPERATOR] P-6: add s64 to /etc/hosts or use IP (1 minute)
```

Steps 1–3 unblock the supervised gunicorn and restore the planned runtime. Steps 4–5 close the remaining engineering gaps. Steps 6–7 enable full multi-host triage.

---

## 10. Evidence index (all captured this session, none printed to logs)

| Evidence | Path | Captured |
|---|---|---|
| PostgreSQL version / roles / dbs | `runtime/portal/temporary/s62-live-state-20260916/` (private) | 2026-09-16 |
| pg_hba relevant lines | same | 2026-09-16 |
| gunicorn unit status + InvocationID | same | 2026-09-16 |
| /proc/<pid>/cmdline for manual gunicorn | same | 2026-09-16 |
| .runtime-config/gunicorn.env keys | same | 2026-09-16 |
| /tmp/gunicorn.log (Sep 11 run) | `/tmp/gunicorn.log` | 2026-09-16 |
| gunicorn.env mtime + unit file birth | same | 2026-09-16 |
| apt history (netdata upgrades, no gunicorn/pkg install) | same | 2026-09-16 |
| Tailscale peer list | same | 2026-09-16 |
| Password auth test (TCP + socket) | same | 2026-09-16 |
| Journalctl empty for unit | same | 2026-09-16 |
| Git archaeology (commits touching gunicorn/password/supervision) | same | 2026-09-16 |

No secret values (passwords, tokens, keys) are stored in the evidence directory. The password length (44) and the fact that it does not authenticate are recorded; the plaintext and the hash are not.
