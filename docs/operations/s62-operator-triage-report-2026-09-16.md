# s62 operator triage — claims and independent follow-up

Original report: 2026-09-16, attributed to opencode. Corrective review:
2026-09-17, application primary. Status: bounded observations and outstanding
infrastructure work; not deployment authorization or Delivery-1 acceptance.
The original report is preserved in Git at `6ea0584`. This revision distinguishes
its reported actions from independently measured outcomes; it does not establish
who performed or authorized the historical host changes.

Source baseline for this follow-up: `89a8902a58ef50b09018790b499eb09221fc8f3c`.
The primary's private receipt set is
`runtime/portal/temporary/runtime-followup-4952a52f6c91/`. It records commands,
native results and observation times. The documentation reviewer received only
the bounded nonsecret findings below and did not read runtime configuration,
private reports or host state. These observations do not certify later live state.

## Independently observed in this follow-up

| Scope | Observation | What it establishes / remaining limit |
|---|---|---|
| Selected supervisor | `prace-v-nemecku-gunicorn.service` active; start `2026-09-16T23:38:58+02:00`; MainPID 269606 | The earlier failed-unit observation is superseded within this receipt window; restart cause and authority are separate |
| Listener ownership | Port 8001 associated with PIDs 269606, 269608, 269610, 269611; all match the selected service cgroup | Bounded unit/listener reconciliation, not a permanent ownership guarantee |
| PostgreSQL cluster | PostgreSQL 18 main is online on 5432 and its cluster unit is active despite the umbrella unit being inactive | Cluster service availability; no inference that application-role authentication or migrations passed |
| Application health | `/health/` returned 200 through `127.0.0.1:8001` and `192.168.1.62:8098`, with Host `prace-v-nemecku.expc.cz` | Both responses declare commit `00786f74fb5321900f9f293f989447e5d7bd8016`, build `g00786f74fb53`; these are declarations, not approved release selection or installed-source identity proof |
| Two portal assets | htmx and Tailwind passed MIME/library-marker checks through both routes | Only these two assets passed; no blanket site or complete asset-byte acceptance |
| Five account/MFA assets | nginx GETs for `account/js/onload.js`, `account/js/account.js`, `mfa/js/recovery_codes.js`, `mfa/js/webauthn-json.js` and `mfa/js/webauthn.js` returned HTTP 403 with `text/html` | Current account/MFA static delivery fails; local source/browser success does not validate this live route |
| Runtime permissions | Root and static directories are 0750; storage/media/cache/tmp/logs are 0700, all UID 992/GID 981 | Compatible with the narrowed source policy for these observed paths only; inbox was not inventoried |
| Initial readiness probes | Both routes exceeded the two-second response-header budget | Those attempts did not establish an HTTP status; retain them separately from the follow-up |
| Readiness follow-up | With a six-second header/eight-second overall budget, both routes returned HTTP 503 in about 2.0–2.25 seconds. A bounded direct client retained JSON `status=not_ready`, `reason=deadline_exceeded`, with the same declared build | Readiness failure is observed; it does not identify the slow stage or establish DB authentication failure |
| Access-log delivery | Two tagged health requests correlate to journal entries for this unit and PID 269611 | Bounded access-log delivery demonstrated; not a causal diagnosis, complete logging coverage, rotation or alert-receiver acceptance |
| Configuration access boundary | `sudo -n -u www-data test -r` on the selected EnvironmentFile returned 0; account groups include `prace-synthetic` GID 981; directory 0750 and file 0640, `root:prace-synthetic` | The unprivileged nginx account can read the configuration. This probe did not open its payload; it does not establish whether anyone previously read it |
| Actual nginx worker groups | PIDs 205419, 205420, 205421, 205422 each carry groups 4, 33, 981 | The application group is present in the running workers, not only in account-database/new-process results |

The last finding is a concrete isolation defect. Successful static delivery does
not justify granting the nginx worker account membership in a secret-reading
application group. The next bounded infrastructure work order separates static
delivery from that group and verifies refusal afterward:
[nginx/static isolation follow-up](servers-infra-core-postgresql-request.md#nginxstatic-isolation-follow-up--2026-09-17).

The five failed static probes are recorded in `account-static-route-checks.json`
within the private receipt set. The static-only metadata inventory has 13 entries
and no symlinks or unsafe entries: the five JavaScript files are mode 0644, but
their four account/MFA parent directories are mode 0700. The work order includes
those directories in its nine exact ACL paths and requires all seven assets to
pass after repair. Filesystem ACL support and proposed post-removal ancestor
traversal passed bounded preflight; those observations are not an applied repair.

Readiness evidence is in `readiness-budget-followup.json` and
`readiness-error-contract.json` within the private receipt set. The canonical
smoke transport's HTTP-error socket drain discarded an already buffered body;
its empty capture does not establish an empty application response. Keep this
instrumentation defect separate from the measured HTTP 503/deadline result.
Application/runtime engineering next profiles readiness stage cost on the selected
source/target, then proposes a measured cause repair or reviewed budget change.
A larger client budget exposed the status; it did not make readiness pass.

## Historical report claims and their disposition

| Original claim at `6ea0584` | Corrected interpretation |
|---|---|
| G-1 was fixed by updating the database role and EnvironmentFile; `SELECT 1` succeeded | Report-attributed mutation and probe. The excerpt does not bind the authenticated database/user/transport or establish authorization. Obtain targeted identity evidence through the infrastructure contract; do not repeat a password reset from this prose |
| G-2 was fixed by unit edits, daemon reload and service start | Historical action remains report-attributed. Fresh unit/cgroup/listener observations above establish the later bounded state; they do not identify or authorize the actor/change |
| G-3 was fixed by changing runtime permissions and nginx reload | Only htmx/Tailwind passed through both routes; all five additional account/MFA assets returned nginx HTTP 403. Account access to the EnvironmentFile is also independently observed; broad group-readable runtime changes cannot be accepted as the isolation solution |
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

The account membership and boolean readability finding are enough to require
repair; reading, hashing, printing or copying the EnvironmentFile payload is
unnecessary. Systemd remains its reader for service configuration. The default
private runtime policy remains 0700 directories and 0600 files. Any dedicated
group exception requires its own reviewed access boundary; granting nginx access
to the application secret group is not that review.

## Next bounded actions and acceptance limits

1. Infrastructure prepares the narrow static-only ACL and group-membership
   correction, worker transition and safe rollback specified in the linked work
   order, preserving existing static bytes and alias. Reuse applicable existing authorization; request
   missing authority only for the final concrete change packet. No such host
   change is executed or authorized by this document correction.
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
