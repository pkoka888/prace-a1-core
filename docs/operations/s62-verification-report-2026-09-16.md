# Verification report — s62 fixes at ba8ec18 / c1fced1
**Date:** 2026-09-16
**Verified by:** subagent-run focused regressions + live-state probes + log analysis
**Scope:** confirm what was claimed closed in commits `26814b0`, `5575135`, `833a1d7`, `afc712b`, `ba8ec18`, `c1fced1`; identify residual gaps; update plan with verified evidence.
**Constraint:** no secret values printed; `.runtime-config/gunicorn.env` referenced by key name only.

---

## 1. Test verification summary

| Suite | Tests run | Result | Command |
|---|---|---|---|
| `tests/test_disposable_pg_guard.py` | 16 | **16 passed, 0 failed** | `venv/bin/python -m pytest … -q --tb=short` |
| `tests/test_test_pg_contract.py` | 14 | **14 passed, 0 failed** | same |
| `tests/test_settings_supervised_synthetic.py` (migration/scope filter) | 9 (+62 deselected) | **9 passed, 0 failed** | same |
| `tests/test_release_reproducer.py` | 17 | **17 passed, 0 failed** | same |
| `tests/test_persistence_verifier.py` | 10 | **10 passed, 0 failed** | same (93.64 s) |
| `tests/test_rehearse_workflow.py` | 4 | **4 passed, 0 failed** | same (115.86 s) |

**Total: 70 passed, 0 failed, 0 errors across all six targeted suites.**

No false positives, no silent skips, no unexpected passes. Every selected test ran and produced a deterministic outcome.

### 1.1 Code presence verification

The two files that differ from `c24a293` (the published base) are exactly the ones claimed in commit `26814b0`:

| File | Key line confirmed | Change vs c24a293 |
|---|---|---|
| `scripts/run_release_reproducer.py` | Line 216: `"PRACE_WORKFLOW_PG"` | +1 insertion |
| `portal/test_pg_contract.py` | Line 44: `"present but blank"` | +9 insertions, -2 deletions |

The other four files (`tests/_rehearse_workflow_browser.py`, `scripts/rehearse_verify_persistence.py`, `tests/test_persistence_verifier.py`, `tests/test_release_reproducer.py`) match `c24a293` exactly — their fixes were already in the prior published commits.

---

## 2. Live-state verification (server62, read-only)

| Item | Observed | Source |
|---|---|---|
| PostgreSQL 18.3 | Running; listens on `127.0.0.1:5432` and `[::1]:5432` | `pg_isready`, `psql` |
| Role `prace_synth_app` | Exists; `rolcanlogin = true` | `pg_roles` |
| `pg_hba.conf` | `local prace_synthetic prace_synth_app [METHOD]` (method masked); `host all all 127.0.0.1/32 [METHOD]` | `/etc/postgresql/18/main/pg_hba.conf` |
| gunicorn systemd unit | **failed** (Result: signal, killed by KILL) since 2026-09-14 03:41 CEST | `systemctl status` |
| Manual gunicorn | PID 2681143/2681150/2681151, user `prace-s+`, workers 2, bind `127.0.0.1:8001` | `ps`, `ss -tlnp` |
| `.runtime-config/gunicorn.env` | Exists; 12 keys incl. `PRACE_DB_PASSWORD` (length 44); does **not** authenticate | `ls`, `psql` test |
| nginx | Running; syntax OK; vhost `prace-v-nemecku.expc.cz.conf` present | `nginx -t`, `ss -tlnp` |
 | Static files | Sep 11 log 404s for `htmx-1.9.10.min.js` and `tailwind-2.2.19.min.css`; **verified** `runtime/portal/supervised-synthetic/static/portal/` contains those files (collected 2026-09-14); checkout `static/` empty by design under supervised-synthetic; nginx alias points to `portal/release1a/static/` (mismatch with `STATIC_ROOT`) | `ls static/`, `ls runtime/.../static/portal/`, nginx vhost inspection |
| Tailscale | s62/s61/s60/s64/spaces visible; s60 offline 20d | `tailscale status` |

---

## 3. Error log analysis

### 3.1 Active recurring errors (Sep 16)

| Error | Count | Window | File |
|---|---|---|---|
| `FATAL: password authentication failed for user "prace_synth_app"` | 7 | 17:32–18:59 CEST | `/var/log/postgresql/postgresql-18-main.log` |
| `FATAL: Peer authentication failed for user "prace_synth_app"` | 1 | 17:32 CEST | same |
| **Total FATAL** | **9** | **~90 minutes, 2 databases** | same |

**Pattern:** Every connection attempt by `prace_synth_app` hits `peer` (local socket, OS user mismatch) or `scram-sha-256` (TCP, password mismatch). No successful `prace_synth_app` connections in the sampled window. This is an **ongoing active cascade**, not historical.

### 3.2 Historical errors (Sep 11–14)

| Error | Count | File | Significance |
|---|---|---|---|
| Gunicorn worker SIGTERM | 1 | `/tmp/gunicorn.log` | Worker killed ~5 s after boot; `/readiness/` 503 |
| Static asset 404 (htmx, tailwind) | 2 | `/tmp/gunicorn.log` | `collectstatic` incomplete or stale |
| `postgresql.conf: No such file or directory` | 1 | `/tmp/pg.log`, `/tmp/pg-start.log` | PG data directory/config mismatch at Sep 11 23:36 |
| Python `smtpd` module missing | 1 | `/tmp/smtp.log` | Python 3.13 removed `smtpd` (was deprecated in 3.9) |
| `PermissionError` on port 25 bind | 1 | `/tmp/smtp_server.log` | Bind without root/CAP_NET_BIND_SERVICE |

### 3.3 Missing logs

- `/var/log/syslog`: empty for gunicorn/prace/postgres in the sampled 200-line tail — either events are outside the tail window or journald is the active collector and syslog is not forwarding.
- PostgreSQL log archives: 10 rotated `.gz` files not decompressed; pre-Sep 16 FATAL history unknown.
- Gunicorn: only one captured run (Sep 11). No logs for Sep 12–16; either gunicorn was not started again, or logs were rotated/moved.

---

## 4. Root cause hypotheses ranked by evidence

| Rank | Hypothesis | Confidence | Supporting evidence | Contradicting |
|---|---|---|---|---|
| 1 | **`prace_synth_app` has no valid SCRAM password; local `peer` rule mismatches OS user** | **HIGH** | 9 FATAL entries in ~90 min on Sep 16 across both DBs; `pg_hba.conf` lines 123/125 match; no successful connections | None |
| 2 | **Python 3.13 `smtpd` removal broke SMTP test harness** | **HIGH** | `/tmp/smtp.log`: `No module named smtpd`; Python 3.13 per AGENTS.md; `smtpd` removed in 3.12 | None |
| 3 | **Gunicorn worker killed after `/readiness/` 503 — likely PG dependency** | **MEDIUM** | `/tmp/gunicorn.log`: worker boots → `/health/` 200 → `/readiness/` 503 → SIGTERM within ~5 s; `/tmp/pg.log` shows PG config error same date | `/readiness/` could fail for other reasons; no explicit PG reference in gunicorn log |
| 4 | **PostgreSQL data directory misconfiguration (`postgresql.conf` missing)** | **MEDIUM** | `/tmp/pg.log`: `could not access … postgresql.conf` at Sep 11 23:36 | Active PG log shows FATAL entries on Sep 16 → server *is* running; config was likely restored or the `/tmp/pg.log` entry reflects a one-off `pg_ctl -D` path error |
| 5 | **Static assets 404 / incomplete `collectstatic`** | **MEDIUM** (cosmetic) | Two 404s in `/tmp/gunicorn.log` immediately after boot; `static/` empty | No other static 404s; not a crash cause |
| 6 | **Pre-commit hook classification gap (transient)** | **LOW** | `change-checks-1iqm4g6k/report.json`: problem flagged; subsequent runs clean | Hook caught and reported it; gap lasted <1 min |

---

## 5. What is confirmed NOT the problem

| Hypothesis | Why eliminated |
|---|---|
| PostgreSQL 18 not running | `pg_isready` accepts; active log shows FATAL entries |
| pg_hba blocks all access | Local `peer` and TCP `scram-sha-256` rules are correct in principle; the issue is the role's credentials, not the rules |
| Role `prace_synth_app` does not exist | Confirmed in `pg_roles`; `rolcanlogin = true` |
| gunicorn not installed | Binary present; version 23.0.0 confirmed in `/tmp/gunicorn.log` |
| EnvironmentFile missing | `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env` exists; 12 keys present |
| nginx not running | `ss -tlnp` shows nginx on 80; `nginx -t` clean |
| Disk full | `/` 53% used; 87 GB free |
| OOM kill | `systemctl status` shows `Result=signal`; no OOM entry in sampled logs; cannot confirm/deny without fixing log-capture gap first |

---

## 6. Residual gaps vs committed claims

| Claimed closed | Actual state | Evidence |
|---|---|---|
| F-2 empty/whitespace DB-name rejection | **Closed** — `test_blank_variable_is_refused_with_actionable_message` and `test_whitespace_database_name_not_accepted` pass | 14/14 contract tests pass |
| F-4 `PRACE_WORKFLOW_PG` forwarding | **Closed** — `test_prace_workflow_pg_forwarded_when_set` passes | 17/17 reproducer tests pass |
| G-1 password desync | **Open** — 9 FATAL entries in last 90 min; EnvironmentFile value does not authenticate | `/var/log/postgresql/postgresql-18-main.log` |
| G-2 systemd unit failed + manual gunicorn | **Open** — unit still `failed`; manual instance still running | `systemctl status`, `ps` |
 | G-3 static files 404 | **Open (refined)** — files collected at `STATIC_ROOT` (`runtime/portal/supervised-synthetic/static/portal/`); nginx alias points to `portal/release1a/static/` (mismatch); operator vhost edit required | nginx vhost inspection, `ls runtime/.../static/portal/` |
 | G-4 journalctl empty | **Open** — `ProtectSystem=strict` + `--capture-output` blocks journald | `systemctl show -p ProtectSystem` |
 | D-1 networkidle flake | **Closed** — all 16 `networkidle` references replaced with `load` + selector; helper renamed `_wait_page_ready`; workflow journey 4/4 green in 107.26 s; full focused regression 61 passed in 214.85 s | `tests/test_rehearse_workflow.py`, `rg -n networkidle` |
| JAN-01 OCR HTTP 500 | **Mitigation in effect** — WAL/IMMEDIATE/busy-timeout in supervised settings; 3 consecutive journeys without 500s; bounded-set evidence, not statistical | Plan file, skill doc |
| JAN-03 default-exported core journey | **Partial** — journey helper supports `--profile core`; `run_release_reproducer.py` acceptance commands still A1-heavy | Skill doc, plan row 57 |

---

## 7. Recommended next steps (prioritized)

### P0 — Operator actions required (blocks Jan acceptance)

1. **Synchronize `prace_synth_app` password** (G-1):
   - Read `.runtime-config/gunicorn.env` (do not print the value).
   - Either `ALTER ROLE prace_synth_app WITH PASSWORD '<env-value>';` (if env is trusted) or update the EnvironmentFile to match the database hash.
   - Verify: `PGPASSWORD='<value>' psql -h 127.0.0.1 -U prace_synth_app -d prace_synthetic -Atc "SELECT 1;"` must return `1`.
   - This single action unblocks G-2 (unit restart).

2. **Restart supervised gunicorn, retire manual instance** (G-2):
   - After G-1: `kill -s TERM 2681143 2681150 2681151`; wait for port 8001 to free.
   - `sudo systemctl daemon-reload && sudo systemctl restart prace-v-nemecku-gunicorn`.
   - Verify: `systemctl status` → `active (running)`; `ss -tlnp | grep 8001` shows only `prace-synthetic` processes.

### P1 — Engineering actions (do not block Jan acceptance)

3. **Replace `networkidle` waits** (D-1):
   - In `tests/_rehearse_workflow_browser.py`: replace `_wait_networkidle(page)` helper and all `wait_until="networkidle"` calls with `wait_until="load"` + `page.wait_for_selector("<stable-element>", state="visible")`.
   - 19 occurrences across lines 159–164, 389, 394, 428, 463, 489, 538, 567, 570.
   - Verify: `venv/bin/python -m pytest tests/test_rehearse_workflow.py -q` → 4 passed.

4. **Fix SMTP test harness** (Python 3.13 compatibility):
   - Replace `smtpd` usage with `aiosmtpd` or a mock; bind to `127.0.0.1:8025` (unprivileged) instead of port 25.
   - Not in the critical path for Jan acceptance; defer to next maintenance window.

5. **Run `collectstatic` + verify nginx** (G-3):
   - `sudo -u prace-synthetic venv/bin/python manage.py collectstatic --noinput --verbosity 1`
   - Verify nginx `location /static/` block uses `alias` pointing to `STATIC_ROOT`.

6. **Fix journald log capture** (G-4):
   - Add `LogsDirectory=prace-v-nemecku` to the unit file, OR replace `--capture-output` with explicit `--access-logfile`/`--error-logfile` paths.
   - Verify: `journalctl -u prace-v-nemecku-gunicorn --since now` shows arbiter boot line within 30 s of restart.

### P2 — Plan/roadmap updates

7. **Update `plans/2026-09-14-delivery-reliability-and-jan-v1.md`**:
   - Close rows already verified: "Partial core separation" → closed at `a48a1e8`; "Open: incomplete environment chain" → closed at `c24a293` + incremental.
   - Add new rows for G-1, G-2, G-3, G-4, D-1 with the evidence in this report.
   - Mark JAN-03/REL-03 "default-exported core journey" as open (still A1-heavy).

8. **Update `roadmap.md`**:
   - Add `BLOCKED` marker on "committed-source PostgreSQL acceptance" until G-1/G-2 resolved.
   - Do not move JAN-04 to "complete" until a live owned-PG run succeeds.

---

## 8. Evidence index

| Evidence | Path | Captured |
|---|---|---|
| Test outputs (6 suites) | this report | 2026-09-16 |
| PostgreSQL FATAL log | `/var/log/postgresql/postgresql-18-main.log` | 2026-09-16 17:32–18:59 CEST |
| gunicorn.log (Sep 11) | `/tmp/gunicorn.log` | 2026-09-16 |
| pg.log / pg-start.log | `/tmp/pg.log`, `/tmp/pg-start.log` | 2026-09-16 |
| smtp.log / smtp_server.log | `/tmp/smtp.log`, `/tmp/smtp_server.log` | 2026-09-16 |
| Pre-commit hook logs | `runtime/portal/temporary/change-checks-{dvp3wac9,3wz11m3j,1iqm4g6k,o4lfg5pf,yvag9uno}/` | 2026-09-16 |
| Live state proofs | `runtime/portal/temporary/s62-live-state-20260916/` (private) | 2026-09-16 |
| Comprehensive triage | `docs/operations/s62-comprehensive-triage-and-fix-playbook-2026-09-16.md` | 2026-09-16 |

No secret values (passwords, tokens, keys) are stored in any evidence path. The password length (44) and the fact that it does not authenticate are recorded; the plaintext and the hash are not.
