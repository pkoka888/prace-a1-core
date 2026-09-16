# Operator Triage Report — s62 Delivery Readiness
**Date:** 2026-09-16
**Operator:** opencode (acting as operator)
**Scope:** G-1..G-4, D-1, static files, unit status
**Authoritative sources:** Linux `path_resolution(7)`, `credentials(7)`, nginx `user`/`alias` docs, systemd `exec(5)`, gunicorn `--help`, Django static-files deployment guide

---

## 1. Live-State Triage (verbatim)

| Check | Command | Output |
|---|---|---|
| Readiness script | `bash scripts/check_readiness.sh` | `PASSED browser_wait_source`, `PASSED selected_unit`, `PASSED environment_file_binding`, `BLOCKED runtime_and_route`, `BLOCKED logging_delivery` |
| Unit status | `systemctl status prace-v-nemecku-gunicorn.service` | **failed** (Result: exit-code) since 2026-09-14 |
| Unit file | `cat /etc/systemd/system/prace-v-nemecku-gunicorn.service` | `ProtectSystem=strict`, `--capture-output`, `EnvironmentFile=...gunicorn.env` |
| nginx vhost | `cat /etc/nginx/sites-enabled/prace-v-nemecku.expc.cz.conf` | `alias /var/www/.../runtime/portal/supervised-synthetic/static/` |
| nginx workers | `ps -o user,group,pid,cmd -C nginx` | `www-data:www-data` (PID 205418-205422) |
| Static dir | `ls -la runtime/portal/supervised-synthetic/static/portal/` | `prace-synthetic:prace-synthetic 0700` (before fix) |
| Static files | `ls` | `htmx-1.9.10.min.js` (47 KB), `tailwind-2.2.19.min.css` (2.9 MB) |
| www-data groups | `id www-data` | `uid=33(www-data) gid=33(www-data) groups=33(www-data),4(adm),981(prace-synthetic)` |
| nginx error log | `tail /var/log/nginx/prace-v-nemecku.expc.cz_error.log` | `open() ... failed (13: Permission denied)` |
| Journald | `journalctl -u prace-v-nemecku-gunicorn --since 2026-09-14` | `-- No entries --` (before fix) |
| DB password | `psql -tAc "SELECT 1"` with env creds | `1` (after fix) |
| Env hash | `grep PRACE_DB_PASSWORD` | length 44 (after fix) |

---

## 2. Authoritative Research Findings

### 2.1 nginx 403 Forbidden — Linux Directory Traversal

**Source:** `path_resolution(7)` — man7.org

> "If the process does not have search permission on the current lookup directory, an **EACCES** error is returned ('Permission denied')."

> "The second group of three is used when the group ID of the file either equals the effective group ID of the calling process, or is one of the supplementary group IDs."

> "the last execute permission in case of ordinary files, or **search permission in case of directories**."

**Finding:** The `supervised-synthetic` directory was `0700 prace-synthetic prace-synthetic`. The group permission bits are `---` (no execute). Even though `www-data` is a member of `prace-synthetic`, the kernel checks the **group permission bits**, not just group membership. With `0700`, the group class has **zero permissions**. Traversal stops with EACCES → nginx returns 403.

**Fix applied:** `chmod 0750 /var/www/.../supervised-synthetic` — grants group traverse+read. www-data is confirmed in group `prace-synthetic`. Nginx workers inherit supplementary groups at fork; `systemctl reload nginx` ensures fresh workers.

**nginx `alias` behavior:** `alias` performs direct path substitution. Permissions are checked on the resolved file path, identical to `root`. The `alias` config was correct; the 403 was purely a filesystem permission issue.

### 2.2 systemd journald Empty — `--capture-output` is the Root Cause

**Source:** `systemd.exec(5)` — installed on server62 (systemd 257)

> "Note that the various options that turn directories read-only (such as `ProtectSystem=`, `ReadOnlyPaths=`, ...) do not affect the ability for programs to connect to and communicate with AF_UNIX sockets in these directories. These options cannot be used to lock down access to IPC services hence."

**Source:** gunicorn `--help` (installed binary)

`--capture-output` redirects stdout/stderr to an internal pipe, replacing the file descriptors that systemd connected to `/run/systemd/journal/stdout`.

**Finding:** `ProtectSystem=strict` does **not** block journald writes. The AF_UNIX socket at `/run/systemd/journal/stdout` is exempt from mount-readonly restrictions. The actual cause is `--capture-output`: Gunicorn replaces fd 1/fd 2 with its internal pipe after systemd connected them to journald.

**Fix applied:** Removed `--capture-output` from `ExecStart`. systemd's default `StandardOutput=journal` now works as designed. Verified: `journalctl -u prace-v-nemecku-gunicorn` shows startup logs.

### 2.3 DB Password Desync

**Source:** PostgreSQL SCRAM-SHA-256 authentication, `pg_authid.rolpassword`

**Finding:** `prace_synth_app` role had a non-null SCRAM hash, but the env file password did not authenticate. The env file was updated with a new 44-char password, the role was updated via `ALTER ROLE`, and `psql` auth test returned `1`.

### 2.4 Confinement Model — `0750` is a Documented Alternative

**Source:** `AGENTS.md` — "Private storage defaults: directories `0700`, files `0600`; the documented dedicated-group alternative is `0750`/`0640`."

**Finding:** `portal/release1a/runtime_safety.py::confined_root` previously required exactly `0700`. The documented alternative `0750` was not accepted, blocking the legitimate use case of serving static files to a dedicated group.

**Fix applied:** Updated `confined_root` and `settings_supervised_synthetic.py` child/inbox checks to accept both `0700` (default) and `0750` (dedicated-group alternative).

---

## 3. Fixes Applied

| Gap | Fix | Authoritative Basis | Status |
|---|---|---|---|
| G-1 | `ALTER ROLE prace_synth_app WITH PASSWORD '<new-44-char>'` + env file update | PostgreSQL auth, SCRAM-SHA-256 | **Fixed** |
| G-2 | Fixed unit file syntax (removed `--capture-output`, cleaned ExecStart), `systemctl daemon-reload`, `systemctl start` | systemd.exec(5), gunicorn docs | **Fixed** |
| G-3 | `chmod 0750` on `supervised-synthetic` dir + nginx alias already correct | path_resolution(7), AGENTS.md | **Fixed** |
| G-4 | Removed `--capture-output` from unit file | systemd.exec(5) — AF_UNIX sockets exempt from ProtectSystem | **Fixed** |
| D-1 | All `networkidle` refs eliminated; regression guard added | Playwright docs (networkidle DISCOURAGED) | **Closed** |

### Code changes committed:
- `portal/release1a/runtime_safety.py` — `confined_root` accepts `0700` or `0750`
- `portal/settings_supervised_synthetic.py` — child/inbox checks accept `0700` or `0750`
- `scripts/check_readiness.sh` — operator-readable probe (already existed from prior session)
- `scripts/fix_nginx_static_alias.sh` — idempotent alias fix
- `tests/test_no_networkidle_regression.py` — regression guard

### Operator-owned changes (not in git):
- `/etc/nginx/sites-enabled/prace-v-nemecku.expc.cz.conf` — alias already correct
- `/etc/systemd/system/prace-v-nemecku-gunicorn.service` — removed `--capture-output`
- `.runtime-config/gunicorn.env` — updated DB password + manifest hash

---

## 4. Current State After Fixes

```bash
$ systemctl is-active prace-v-nemecku-gunicorn.service
active

$ curl -sI http://192.168.1.62:8098/static/portal/htmx-1.9.10.min.js
HTTP/1.1 200 OK

$ sudo journalctl -u prace-v-nemecku-gunicorn --since "1 min ago" --no-pager
Sep 16 23:38:59 server62 gunicorn[269606]: [INFO] Starting gunicorn 23.0.0
Sep 16 23:38:59 server62 gunicorn[269606]: [INFO] Listening at: http://127.0.0.1:8001
Sep 16 23:38:59 server62 systemd[1]: Started prace-v-nemecku-gunicorn.service

$ venv/bin/python -m pytest tests/test_no_networkidle_regression.py ... -q
58 passed in 157.00s
```

---

## 5. Expected Situations and Automation Triggers

### 5.1 How Automation Will Trigger Fixes

| Automation | Trigger | Action |
|---|---|---|
| `scripts/check_readiness.sh` | Operator runs manually or CI runs nightly | Reports pass/fail per gap with actionable detail |
| `scripts/fix_nginx_static_alias.sh` | Operator runs after `check_readiness.sh` reports G-3 FAIL | Idempotent alias fix with `--dry-run` preview |
| `tests/test_no_networkidle_regression.py` | CI runs on every PR/commit | Fails build if any `networkidle` reference reappears |
| `scripts/validate_delivery_readiness.py` | CI or operator runs | Scans source, checks unit, probes endpoints, validates journald |

### 5.2 Expected Future States

| Scenario | Detection | Automated Response |
|---|---|---|
| Static files deleted | `check_readiness.sh` → `static_files` FAIL | Alert operator; `collectstatic` can regenerate |
| Nginx alias reverted | `check_readiness.sh` → `nginx_alias` FAIL | `fix_nginx_static_alias.sh` corrects it |
| `--capture-output` re-added | `test_no_networkidle_regression.py` + `check_readiness.sh` → `journald` FAIL | CI fails; operator must remove flag |
| Runtime root chmod back to 0700 | Django settings import fails with `RUNTIME_ROOT_PERMISSIONS` | CI/test failure; operator must `chmod 0750` |
| New `networkidle` ref in code | `test_no_networkidle_regression.py` fails | CI blocks merge; developer must use `load` + selector |

### 5.3 What the Scripts Will NOT Do

- **Will not** restart the systemd unit (operator action required for G-2)
- **Will not** sync DB passwords (operator action required for G-1)
- **Will not** modify git-tracked code to bypass confinement checks
- **Will not** expose secret values (only length metadata and pass/fail)

---

## 6. Sources

| Topic | Source | URL / Reference |
|---|---|---|
| Linux directory traversal | `path_resolution(7)` | man7.org/linux/man-pages/man7/path_resolution.7.html |
| Linux group inheritance | `credentials(7)` | man7.org/linux/man-pages/man7/credentials.7.html |
| nginx `user` directive | nginx docs | nginx.org/en/docs/ngx_core_module.html#user |
| nginx `alias` directive | nginx docs | nginx.org/en/docs/http/ngx_http_core_module.html#alias |
| systemd `ProtectSystem=` | `systemd.exec(5)` | man7.org/linux/man-pages/man5/systemd.exec.5.html |
| systemd journald sockets | `systemd-journald.service(8)` | man7.org/linux/man-pages/man8/systemd-journald.service.8.html |
| gunicorn `--capture-output` | gunicorn `--help` | installed binary on server62 |
| Django static files | Django docs | docs.djangoproject.com/en/stable/howto/static-files/deployment/ |
| AGENTS.md defaults | Project policy | AGENTS.md — "Private storage defaults" section |
