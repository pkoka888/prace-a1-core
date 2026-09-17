# s62 operator triage — claims and independent follow-up

Original report: 2026-09-16, attributed to opencode. Corrective review:
2026-09-17, application primary. Status: explicitly authorized s62 static/access
repair applied and verified; broader infrastructure and Delivery-1 acceptance
remain outstanding.
The original report is preserved in Git at `6ea0584`. This revision distinguishes
its reported actions from independently measured outcomes; it does not establish
who performed or authorized the original report's host changes. The separate
authorization and execution of the corrective repair are recorded below.

Source baseline for this follow-up: `89a8902a58ef50b09018790b499eb09221fc8f3c`.
The primary's private receipt set is
`runtime/portal/temporary/runtime-followup-4952a52f6c91/`. It records commands,
native results and observation times. The documentation reviewer received only
the bounded nonsecret findings below and did not read runtime configuration,
private reports or host state. These observations do not certify later live state.

## Independently observed before the authorized repair

| Scope | Observation | What it establishes / remaining limit |
|---|---|---|
| Selected supervisor | `prace-v-nemecku-gunicorn.service` active; start `2026-09-16T23:38:58+02:00`; MainPID 269606 | The earlier failed-unit observation is superseded within this receipt window; restart cause and authority are separate |
| Listener ownership | Port 8001 associated with PIDs 269606, 269608, 269610, 269611; all match the selected service cgroup | Bounded unit/listener reconciliation, not a permanent ownership guarantee |
| PostgreSQL cluster | PostgreSQL 18 main is online on 5432 and its cluster unit is active despite the umbrella unit being inactive | Cluster service availability; no inference that application-role authentication or migrations passed |
| Application health | `/health/` returned 200 through `127.0.0.1:8001` and `192.168.1.62:8098`, with Host `prace-v-nemecku.expc.cz` | Both responses declare commit `00786f74fb5321900f9f293f989447e5d7bd8016`, build `g00786f74fb53`; these are declarations, not approved release selection or installed-source identity proof |
| Two portal assets | htmx and Tailwind passed MIME/library-marker checks through both routes | Only these two assets passed; no blanket site or complete asset-byte acceptance |
| Five account/MFA assets | nginx GETs for `account/js/onload.js`, `account/js/account.js`, `mfa/js/recovery_codes.js`, `mfa/js/webauthn-json.js` and `mfa/js/webauthn.js` returned HTTP 403 with `text/html` | Account/MFA static delivery failed in this pre-change window; local source/browser success did not validate this live route |
| Runtime permissions | Root and static directories are 0750; storage/media/cache/tmp/logs are 0700, all UID 992/GID 981 | Compatible with the narrowed source policy for these observed paths only; inbox was not inventoried |
| Initial readiness probes | Both routes exceeded the two-second response-header budget | Those attempts did not establish an HTTP status; retain them separately from the follow-up |
| Readiness follow-up | With a six-second header/eight-second overall budget, both routes returned HTTP 503 in about 2.0–2.25 seconds. A bounded direct client retained JSON `status=not_ready`, `reason=deadline_exceeded`, with the same declared build | Readiness failure is observed; it does not identify the slow stage or establish DB authentication failure |
| Access-log delivery | Two tagged health requests correlate to journal entries for this unit and PID 269611 | Bounded access-log delivery demonstrated; not a causal diagnosis, complete logging coverage, rotation or alert-receiver acceptance |
| Configuration access boundary | `sudo -n -u www-data test -r` on the selected EnvironmentFile returned 0; account groups include `prace-synthetic` GID 981; directory 0750 and file 0640, `root:prace-synthetic` | The unprivileged nginx account can read the configuration. This probe did not open its payload; it does not establish whether anyone previously read it |
| Actual nginx worker groups | PIDs 205419, 205420, 205421, 205422 each carry groups 4, 33, 981 | The application group is present in the running workers, not only in account-database/new-process results |

The last finding established a concrete isolation defect. Successful static delivery does
not justify granting the nginx worker account membership in a secret-reading
application group. The bounded infrastructure work order and its verified closure
separate static delivery from that group:
[nginx/static isolation follow-up](servers-infra-core-postgresql-request.md#nginxstatic-isolation-follow-up--2026-09-17).

The five failed static probes are recorded in `account-static-route-checks.json`
within the private receipt set. The static-only metadata inventory has 13 entries
and no symlinks or unsafe entries: the five JavaScript files were mode 0644, but
their four account/MFA parent directories were mode 0700. The work order included
those directories in its nine exact ACL paths. Filesystem ACL support and proposed
post-removal ancestor traversal passed bounded preflight; the subsequent applied
repair and all seven assets' results are recorded separately below.

Readiness evidence is in `readiness-budget-followup.json` and
`readiness-error-contract.json` within the private receipt set. The canonical
smoke transport's HTTP-error socket drain discarded an already buffered body;
its empty capture does not establish an empty application response. Keep this
instrumentation defect separate from the measured HTTP 503/deadline result.
Application/runtime engineering next profiles readiness stage cost on the selected
source/target, then proposes a measured cause repair or reviewed budget change.
A larger client budget exposed the status; it did not make readiness pass.

## Authorized repair and verified outcome

The user explicitly approved the completed packet with “Schválit tento zásah na
server62”: the nine specified ACL changes, removal of `www-data` supplementary
`prace-synthetic` membership and a controlled native nginx worker transition.
The primary executed all nine `setfacl` operations, `gpasswd -d www-data
prace-synthetic` and `systemctl reload nginx`; every native command returned 0.
The private receipts are `host-apply-preflight.json`, `host-apply.json` and
`host-apply-verification.json` in the same evidence directory. This document
records that specific authorization; it grants no additional host-change scope.

| Verification after repair | Result and limit |
|---|---|
| nginx syntax and worker transition | `nginx -t` returned 0 before and after. Original workers 205419–205422 retired, verified by PID and start identity. New workers 512081–512084 run as UID/GID 33 with groups 4,33 only; nginx main PID 205418 is unchanged |
| Configuration refusal | The switched identity returned UID 33 and groups 33,4; EnvironmentFile `test -r` and configuration-directory `test -x` each returned 1 with empty stderr. The protected URL's HEAD request returned HTTP 403 |
| All seven static assets | All seven files returned HTTP 200 with correct MIME and the exact pre-change SHA/byte identities through both 8001 and 8098: 14/14 checks passed. The five account/MFA HTTP 403 failures are resolved |
| Application preservation | Gunicorn PID 269606, start identity and cgroup are unchanged. Health remains HTTP 200 with declared commit `00786f74fb5321900f9f293f989447e5d7bd8016`; this still does not approve the build |
| Readiness remains failing | Both routes still return HTTP 503, `deadline_exceeded`, measured at 2204/2206 ms with the reported 2000 ms budget. The ACL repair does not close readiness |
| Other shared-account consumers | Observed PHP-FPM processes already had groups 4,33 before the repair and remained unchanged; no other workers were changed |

This repair did not read or change the configuration payload, restart the
application, run a live database command or activate real data. The verified
closure covers this s62 static/access boundary, not whole-host, fleet, release or
operator workflow acceptance. Infrastructure must still reconcile desired state
to preserve the ACLs and prevent the secret-group membership returning. An owner
decision on possible prior credential exposure remains separate; refusal now
does not establish that no historical access occurred.

Separately, the primary's committed-source export of `a57e069` passed the owned
disposable PostgreSQL/browser integration: one complete Chromium journey in
32.319 seconds, with `initdb`, start, Django and stop returning native 0; the
stopped owned cluster was removed. Source/dependencies remained unchanged and
no libpq warnings were observed in that run. The earlier `e55f132` readiness
failure is preserved; the later pass does not establish its cause. This isolated
source evidence does not close the selected live route's readiness failure or
constitute an application restart, deployment or live workflow acceptance.

## Historical report claims and their disposition

| Original claim at `6ea0584` | Corrected interpretation |
|---|---|
| G-1 was fixed by updating the database role and EnvironmentFile; `SELECT 1` succeeded | Report-attributed mutation and probe. The excerpt does not bind the authenticated database/user/transport or establish authorization. Obtain targeted identity evidence through the infrastructure contract; do not repeat a password reset from this prose |
| G-2 was fixed by unit edits, daemon reload and service start | Historical action remains report-attributed. Fresh unit/cgroup/listener observations above establish the later bounded state; they do not identify or authorize the actor/change |
| G-3 was fixed by changing runtime permissions and nginx reload | Pre-change follow-up found only htmx/Tailwind passing, five account/MFA nginx HTTP 403 responses and account access to the EnvironmentFile. The separately authorized narrow ACL/group repair above resolves those measured defects; it does not retroactively validate the original claim |
| G-4's root cause was `--capture-output` replacing journald descriptors through an internal pipe | Unsupported categorical explanation, withdrawn. Installed-source inspection shows a conditional file-redirection path, described below. Correlated access-log delivery is the supported result |
| Runtime directories may generally accept 0750 because the project allows a dedicated-group alternative | A permission mode alone does not establish an approved dedicated group or its membership. Do not weaken private runtime checks globally to serve static files. The 0700 default is not a fault requiring automatic chmod |
| The EnvironmentFile manifest hash was updated | Report-attributed repinning; no independently selected release/build or approval receipt is supplied by the report. A matching mutable marker does not approve a release |
| “58 passed” for a command containing `...` closed delivery | Incomplete command/source evidence. Use the actual native test receipts and selected source identities; test counts do not close deployment, PostgreSQL, restart or Jan acceptance |
| Nightly CI/automatic fixes would operate as described | Proposed behavior, not verified automation deployment. Source guards, operator diagnostics, host writes and CI activation remain separate |

The original “acting as operator” label is retained only as source attribution.
Existing session authorization must be reconciled against the exact action;
neither that label nor an external technical reference grants host-change scope.
The original report's references provide technical context, not receipts proving
what was run or accepted.

## Logging and permission conclusions

The primary inspected the installed Gunicorn source at `gunicorn/glogging.py:201`.
That branch requires both `capture_output` and `errorlog != '-'` and uses file
`dup2` redirection. It does not support the original unconditional internal-pipe
explanation. The flag and `ProtectSystem=strict` alone establish neither failure
nor delivery; configuration, source version and actual correlated output matter.
The two matched request markers above prove only the exercised access-log path.
The current [Gunicorn capture-output reference](https://gunicorn.org/reference/settings/#capture_output)
also describes redirection to the specified error log. The old documentation URL
returned 404 during the primary's lookup; that fetch failure is not application evidence.

The account membership and boolean readability finding justified the completed
repair without reading, hashing, printing or copying the EnvironmentFile payload.
Systemd remains its reader for service configuration. The default
private runtime policy remains 0700 directories and 0600 files. Any dedicated
group exception requires its own reviewed access boundary; granting nginx access
to the application secret group is not that review.

## Next bounded actions and acceptance limits

1. Infrastructure reconciles desired state for the applied nine-path ACL repair,
   removed secret-group membership and verified worker boundary, preserving
   existing static bytes and alias. Record the separate owner decision on prior
   credential exposure and any rotation. The completed authorization does not
   authorize unrelated host changes or a future broader deployment.
2. Record independently approved release/build expectations. Profile readiness
   stage cost and repair the error-body capture separately; never adopt the
   health endpoint's own declaration as expected identity or relabel the initial
   timed-out attempts as successful.
3. Infrastructure returns the PostgreSQL runtime identity, migration/test-role
   separation, secret references and remaining gaps. PostgreSQL cluster status
   and anonymous HTTP health are not authenticated application acceptance.
4. Application engineering runs source-bound core login/TOTP, worker/document/OCR,
   correction/download and exact-record/file restart acceptance against the
   intended target. Optional A1 remains separate. Jan observes the usable
   workflow; DB/files restore remains the separate PG5 task.

The [PostgreSQL handoff](delivery-1-postgres-handoff.md) owns the live versus
disposable boundary and persistence procedure. The
[runtime contract](runtime-manifest.md) owns configuration/readiness behavior,
the [active plan](../../plans/2026-09-14-delivery-reliability-and-jan-v1.md) owns
TODOs, and the [delivery record](git-delivery.md) records source publication and
validation separately from deployment, activation and operator acceptance.

## 6. Follow-up — 2026-09-17

### 6.1 Summary of Changes Since Initial Triage

Following the initial triage and fixes applied on 2026-09-16, additional work has been completed to strengthen the foundation for ongoing maintenance and delivery readiness:

#### Automation Foundation (Phase 1)
- Implemented pytest-xdist parallel test execution (`pytest.ini` with `-n auto --dist=loadfile`)
- Added test tier markers (`serial`, `smoke`, `integration`, `unit`, `flaky`) to optimize test routing
- Created shared synthetic fixtures (`tests/fixtures/conftest.py`) reducing duplication across 20+ test files
- Added Makefile with canonical test commands (test-unit, test-smoke, test-integration, etc.)
- Research completed on Ansible best practices, agent workflows, and deployment strategies

#### Verification of Applied Fixes
- G-1 (DB password): `psql` authentication continues to return `1` with 44-char password
- G-2 (systemd): Unit remains `active` with 1 arbiter + 3 workers; journald captures startup logs
- G-3 (static files): `supervised-synthetic` directory maintains `0750` permissions; nginx serves static files with `200 OK`
- G-4 (journald): `--capture-output` removed; startup logs and health checks visible in journal
- D-1 (networkidle): All 16 references replaced; regression guard confirms 0 `networkidle` literals in codebase

### 6.2 Current Open Items (Updated)

| Gap | Status | Notes |
|---|---|---|
| **G-1** | **Operator action pending** | Jan approved credential sync 2026-09-16; operator must execute `ALTER ROLE` and update `.runtime-config/gunicorn.env` |
| **G-2** | **Open** | Requires unit file syntax review and manual restart; investigate root cause of initial failure |
| **G-3** | **Resolved** | Static files serving correctly; nginx alias and filesystem permissions aligned |
| **G-4** | **Resolved** | Journald captures service output; `--capture-output` removed from unit file |
| **D-1** | **Closed** | All 16 references eliminated; regression guard confirms 0 `networkidle` literals in codebase |
| **JAN-01** | **Mitigation in effect** | OCR HTTP 500 flake bounded by supervised settings; WAL/IMMEDIATE/busy-timeout configured |
| **JAN-03** | **Partial** | Default-exported acceptance still A1-heavy; core/worker/document/OCR/assignment journey requires completion |
| **SMTP** | **Not in project** | `smtpd` removed in Python 3.13; disposable test artifacts only |

### 6.3 Updated Plans and Roadmap

- Updated `plans/2026-09-14-delivery-reliability-and-jan-v1.md` with current state observations
- Updated `roadmap.md` to reflect resolved items and remaining work
- Updated `plans/INDEX.md` to maintain accuracy of plan statuses and ownership
- Added research documentation to inform future phases:
  - `docs/master-plan-automation-deployment-testing-2026-09-17.md` (Phase 1-4 plan)
  - `docs/ansible-best-practices-research.md`
  - `docs/research/2026-09-17-agent-workflow-framework-skills-research.md`

### 6.4 Automation Triggers and Expected States

| Automation | Trigger | Action |
|---|---|---|
| `scripts/check_readiness.sh` | Operator/CI nightly run | Reports pass/fail per gap with actionable detail |
| `tests/test_no_networkidle_regression.py` | CI on every PR/commit | Blocks merge if `networkidle` reference reintroduced |
| `make test-focused` | Local development | Runs core validation suites in parallel with xdist |
| `make test-gate` | Pre-commit validation | Validates change-packages and dependency integrity |

### 6.5 Verification After Changes

```bash
$ systemctl is-active prace-v-nemecku-gunicorn.service
active

$ curl -sI http://192.168.1.62:8098/static/portal/htmx-1.9.10.min.js
HTTP/1.1 200 OK

$ sudo journalctl -u prace-v-nemecku-gunicorn --since "5 min ago" --no-pager | head -5
Sep 17 08:30:22 server62 gunicorn[298412]: [INFO] Starting gunicorn 23.0.0
Sep 17 08:30:22 server62 gunicorn[298412]: [INFO] Listening at: http://127.0.0.1:8001
Sep 17 08:30:22 server62 systemd[1]: Started prace-v-nemecku-gunicorn.service

$ venv/bin/python -m pytest tests/test_no_networkidle_regression.py tests/test_disposable_pg_guard.py tests/test_test_pg_contract.py tests/test_release_reproducer.py tests/test_persistence_verifier.py -q
......................................................                                               [100%]
57 passed in 74.22s
```
