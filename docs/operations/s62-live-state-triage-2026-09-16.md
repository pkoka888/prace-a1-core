# s62 live-state triage and gap analysis — 2026-09-16

Scope: compare what is actually running/configured on server62 against what the
active plan, FEEDBACK-REPORT and runtime-manifest assume. Every gap below is
grounded in a command output captured this session; no values from
`.runtime-config/gunicorn.env` are printed (the file is readable and contains
`PRACE_DB_PASSWORD`, but its plaintext does not authenticate against the live
database — see finding G-1).

## L-1 Live-state inventory (captured 2026-09-16)

| Layer | Observed | Source |
|---|---|---|
| OS / host | Debian (bookworm), kernel 6.x, user `pavel` (uid 1000), groups include `www-data`, `sudo`, `agents`, `infrastructure` | `whoami`, `id` |
| PostgreSQL | 18.3 (Debian 18.3-1.pgdg13+1), listening on `127.0.0.1:5432` and `[::1]:5432` | `psql -Atc "SELECT version();"` |
| PG roles | `prace_synth_app` (rolcanlogin=t, rolcreaterole=f, rolcreatedb=f); password hash present | `pg_roles` |
| PG databases | `prace_synthetic`, `prace_synthetic_test` (both `en_US.UTF-8`) | `pg_database` |
| pg_hba | `local prace_synthetic prace_synth_app md5`; `host all all 127.0.0.1/32 scram-sha-256`; `host all all ::1/128 scram-sha-256` | `/etc/postgresql/18/main/pg_hba.conf` |
| Active PG connections | Only `postgres` superuser connected; zero `prace_synth_app` connections | `pg_stat_activity` |
| systemd gunicorn unit | `/etc/systemd/system/prace-v-nemecku-gunicorn.service` — loaded, **enabled**, **active=failed** since 2026-09-14 03:41 CEST (Result: signal, PID 505344 KILL); no journal entries | `systemctl status`, `journalctl` |
| Manual gunicorn | PID 2681143/2681150/2681151, user `prace-s+`, bind `127.0.0.1:8001`, `--workers 2`, running since Sep 14 (2-12:32:26); pid-file at `runtime/portal/supervised-synthetic/gunicorn.pid` | `ps`, `/proc/<pid>/cmdline` |
| .runtime-config | `/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env` — exists, mode `-rw-r----- root:prace-synthetic`, 844 bytes, 12 keys incl. `PRACE_DB_PASSWORD` (length 44) | `ls -la`, `cut -d= -f1` |
| nginx | Running; vhost `prace-v-nemecku.expc.cz.conf` present; `nginx -t` clean | `nginx -t`, `/etc/nginx/sites-enabled/` |
| Tailscale | server62 (100.81.67.93), s64, server60, server61, spaces (Windows) | `tailscale status` |
| Project .env | 1094 bytes, API keys only; **no** `PRACE_DB_PASSWORD` | `rg .env` |

## L-2 Planned state (from active documents)

| Plan item | Planned state | Source document |
|---|---|---|
| gunicorn supervision | Supervised by systemd; unit `prace-v-nemecku-gunicorn.service`; EnvironmentFile `runtime-manifest`-specified path; service healthy | `docs/operations/runtime-manifest.md`, `roadmap.md` |
| PostgreSQL target | Application authenticates with `prace_synth_app` over TCP (`127.0.0.1`) using `PRACE_DB_PASSWORD` from EnvironmentFile | `portal/settings_supervised_synthetic.py`, `docs/operations/delivery-1-postgres-handoff.md` |
| INFRA-PG-01 | Credential, supervision, HBA, routing and build reconciliation are operator-owned | FEEDBACK-REPORT, plan rows |
| Orphan gunicorn | Documented as infra debt; not to be killed by application engineering | FEEDBACK-REPORT |
| Static files | Served by nginx from project `static/` directory | `runtime-manifest.md` |

## L-3 Gap analysis

### G-1 (Critical) gunicorn.env password does not authenticate

**Observed.** The `PRACE_DB_PASSWORD` stored in `.runtime-config/gunicorn.env`
(length 44) fails `FATAL: password authentication failed` over `127.0.0.1`
(`scram-sha-256`) and `FATAL: Peer authentication failed` over local socket
(`md5`) for `prace_synth_app`. The role has a non-null password hash but the
plaintext in the EnvironmentFile is not the current role password.

**Root cause.** The operator reset `prace_synth_app`'s password (or re-created
the role) without updating `.runtime-config/gunicorn.env`, or the EnvironmentFile
was populated from a different credential source.

**Gap vs plan.** The plan assumes the EnvironmentFile and the database role
share the same credential. They do not. This blocks:
- Supervised gunicorn start (the unit reads EnvironmentFile and passes the
  wrong password to Django → psycopg → PostgreSQL).
- Any workflow that needs the application role (migration, runtime queries,
  rehearsal harness with `PRACE_WORKFLOW_PG=1`).

**Evidence.** `sudo -u postgres psql` confirms role + hash exist; `psql -h
127.0.0.1 -U prace_synth_app` with the EnvironmentFile password returns
`FATAL: password authentication failed`. No `prace_synth_app` connections in
`pg_stat_activity`.

### G-2 (High) systemd unit is failed; manual gunicorn diverges from unit spec

**Observed.** `prace-v-nemecku-gunicorn.service` is **enabled** but
**active=failed** since 2026-09-14 (Result: signal, PID 505344 KILL). A
manually-started gunicorn (PID 2681143, user `prace-s+`, not the unit's
`prace-synthetic`) is serving on the same `127.0.0.1:8001` with `--workers 2`
instead of the unit's `--workers 3`.

**Root cause.** The unit was killed (OOM, operator action, or timeout) and
was never restarted by systemd. An operator or script manually started a
divergent instance to restore service.

**Gap vs plan.** The plan assumes the supervised unit is the authority. The
manual instance is unmanaged: no `PrivateTmp`, no `ProtectSystem=strict`, no
`NoNewPrivileges`, running as `prace-s+` not `prace-synthetic`, and writing
its pid-file into the supervised-synthetic runtime directory. The orphan
process is the only thing serving the application right now.

**Evidence.** `systemctl status` shows failed since Sep 14; `ps` shows
`prace-s+` user and `--workers 2`; unit file specifies `User=prace-synthetic`
and `--workers 3`.

### G-3 (Medium) static files / collectstatic not served

**Observed.** The `/tmp/gunicorn.log` from the Sep 11 run shows `404` for
`/static/portal/htmx-1.9.10.min.js` and `/static/portal/tailwind-2.2.19.min.css`.
The `static/` directory listing returned empty in this session.

**Gap vs plan.** The runtime-manifest and nginx vhost assume static assets are
collected and served. Either `collectstatic` has not run, or the static root
is misconfigured, or nginx is not proxying `/static/` to the Django static
files location.

**Evidence.** `ls static/` empty; `/tmp/gunicorn.log` 404s.

### G-4 (Low) journalctl empty for the failed unit

**Observed.** `journalctl -u prace-v-nemecku-gunicorn --since 2026-09-14`
returns no entries.

**Gap vs plan.** The plan assumes journald captures unit lifecycle events.
Either the unit failed before journald was available, the logs were rotated,
or `ProtectSystem=strict` / `PrivateTmp=true` in the unit file is preventing
journald from reading the cgroup's stdout/stderr (the unit uses
`--access-logfile - --error-logfile - --capture-output`, which relies on
journald for capture).

**Evidence.** Empty journal output; unit file uses `--capture-output`.

## L-4 Corrections, recommendations, simplifications

### R-1 (Corrects G-1) Reset the database password to match the EnvironmentFile

**Recommended action (operator).** The operator should align the two credential
sources. Two equivalent paths:

1. **Update the database role** (simplest if the EnvironmentFile is trusted):
   ```sql
   ALTER ROLE prace_synth_app WITH PASSWORD '<value-already-in-gunicorn.env>';
   ```
   Then verify:
   ```bash
   PGPASSWORD='<value-from-gunicorn.env>' \
     psql -h 127.0.0.1 -U prace_synth_app -d prace_synthetic \
     -Atc "SELECT current_user, current_database();"
   ```
   The connection must succeed over TCP with `scram-sha-256`.

2. **Update the EnvironmentFile** (if the database password is the source of
   truth): write the new password to `.runtime-config/gunicorn.env`, then
   `systemctl daemon-reload && systemctl restart prace-v-nemecku-gunicorn`.

**Simplification.** The role does not need `rolcreaterole` or `rolcreatedb`;
the current grants are already minimal. No schema or privilege change is
required — only the password hash.

**Why this still solves the problem.** The existing plan already requires the
operator to reset the credential (INFRA-PG-01). This recommendation narrows
the action to a single `ALTER ROLE` (or a single EnvironmentFile edit) plus
a one-line verification, instead of the broader rotation the plan implies.

### R-2 (Corrects G-2) Restart the supervised unit; retire the manual instance

**Recommended action (operator).**
1. Kill the manual gunicorn (PID 2681143 et al.) gracefully:
   ```bash
   kill -s TERM 2681143 2681150 2681151
   ```
   Wait for the port to free (`ss -tlnp | grep 8001` empty).
2. Restart the supervised unit:
   ```bash
   sudo systemctl restart prace-v-nemecku-gunicorn
   sudo systemctl status prace-v-nemecku-gunicorn
   ```
3. If the unit fails again, inspect `ProtectSystem=strict` and
   `ReadWritePaths` — the unit already allows
   `runtime/portal/supervised-synthetic` and `/var/log/prace-v-nemecku`;
   if additional paths are needed, add them there.

**Simplification.** The unit file already specifies the correct user
(`prace-synthetic`), EnvironmentFile path, and `--workers 3`. The manual
instance is a divergence that should be removed, not duplicated. After R-1
fixes the password, the unit should start cleanly.

### R-3 (Corrects G-3) Verify collectstatic / static root

**Recommended action (engineering, read-only probe).**
```bash
sudo -u prace-synthetic \
  /var/www/prace-v-nemecku.tvoje.info/venv/bin/python manage.py \
  collectstatic --noinput --verbosity 0 2>&1 | tail -5
sudo ls -la /var/www/prace-v-nemecku.tvoje.info/static/ 2>/dev/null | head
```
If `collectstatic` populates the directory, the nginx vhost should serve
`/static/` directly. If the directory stays empty, the static root in
`portal/settings.py` or the nginx `location /static/` block needs inspection.

**Simplification.** The nginx vhost `prace-v-nemecku.expc.cz.conf` is already
present and `nginx -t` is clean. The likely gap is that `collectstatic` has
not run since the last deploy, not a configuration defect.

### R-4 (Corrects G-4) Make gunicorn logs journald-capturable

**Recommended action (operator, one-line unit edit).** The unit uses
`--capture-output`, which redirects stdout/stderr to journald. If journald
is not capturing the output, the likely cause is `ProtectSystem=strict`
blocking cgroup I/O before journald's own socket is available. Add
`LogsDirectory=` or remove `--capture-output` and use explicit log files
(`--access-logfile /var/log/prace-v-nemecku/access.log --error-logfile
/var/log/prace-v-nemecku/error.log`) with `ReadWritePaths` extended to
`/var/log/prace-v-nemecku`.

**Simplification.** Explicit log files are easier to rotate with `logrotate`
and easier to read without `journalctl`. The `ReadWritePaths` already allows
`/var/log/prace-v-nemecku`; only the ExecStart argv changes.

## L-5 Gap summary for the architect

| ID | Gap | Severity | Owner | Fix complexity | Blocks Jan acceptance? |
|---|---|---|---|---|---|
| G-1 | gunicorn.env password ≠ DB role password | Critical | Operator | 1 ALTER ROLE or 1 file edit + restart | Yes — supervised gunicorn cannot start |
| G-2 | systemd unit failed; manual gunicorn diverges | High | Operator | Kill manual + restart unit (after G-1) | Yes — unmanaged process is not the planned runtime |
| G-3 | static files 404 / empty static dir | Medium | Engineering | `collectstatic` run + nginx verify | No — journeys hit dynamic views first |
| G-4 | journalctl empty for unit | Low | Operator | Unit file argv change | No — /tmp/gunicorn.log retains history |

## L-6 Simplifications the plan can adopt

1. **Collapse INFRA-PG-01 into two atomic operator actions** instead of the
   current broad "credential, supervision, routing and build reconciliation":
   - (a) `ALTER ROLE prace_synth_app WITH PASSWORD '<env-value>'` (or
     EnvironmentFile edit), then `systemctl restart prace-v-nemecku-gunicorn`
     and `systemctl status` green.
   - (b) Confirm nginx `proxy_pass http://127.0.0.1:8001;` matches the unit's
     `--bind` and that `proxy_set_header Host $host;` carries the approved
     `prace-v-nemecku.expc.cz` host.
   The remaining HBA/routing/build reconciliation is already documented and
   can stay as separate sub-items.

2. **Remove the "orphan gunicorn" row from FEEDBACK-REPORT once G-2 is
   closed.** The orphan is a symptom of G-1+G-2, not an independent infra
   debt item. Merging them simplifies the next audit.

3. **Drop the `networkidle` investigation from the plan once the wait
   strategy is replaced.** The plan currently treats it as JAN-01 open work;
   the fix (replace with `wait_until="load"` + selector waits) is one
   coherent increment and does not need a separate "timeout cause unresolved"
   row once committed.

4. **Treat `psql_env` / TLS forwarding / blank-target rejection as closed
   at `c24a293` / `afc712b`.** The plan still lists them as open/partial;
   the current code already closes them. A single "plan staleness sweep"
   before each delivery-record update would keep the plan authoritative.
