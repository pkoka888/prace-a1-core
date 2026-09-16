# Server62 logging claims review — 2026-09-16

Read-only observation at 18:15–18:16 UTC (20:15–20:16 CEST). The installed
logrotate and its scheduler are present. Three named custom logs have no matching
rule in the included configuration. Successful privileged rotation of individual
files remains unverified; the unprivileged debug run failed on access boundaries.
No raw service/authentication log contents, Alertmanager configuration, secrets or
application runtime evidence were read. No rotation, cleanup, restart, privilege
escalation or external notification was performed.

Private metadata and filtered diagnostic receipts are in
`runtime/portal/temporary/logging-claims-review-20260916/`, created exclusively with
directory mode `0700` and files `0600`. This report records a bounded local-server
observation, not fleet logging acceptance.

## Executed checks and their limits

| Check | Result | What it establishes |
|---|---|---|
| Earlier primary-agent bare `logrotate` launch | Reported `FileNotFoundError`; retained as an earlier PATH limitation, not independently rerun here | Does not establish absence of the executable |
| `/usr/sbin/logrotate --help` | Exit 0; debug help explicitly states no actions | Permitted a non-mutating debug check |
| `/usr/sbin/logrotate --version` | Exit 0; version 3.22.0 | Installed executable identity, not operational success |
| Read `/etc/logrotate.conf` and every file in `/etc/logrotate.d/` | All 25 files readable; sole include is `/etc/logrotate.d` | Actual named-file and glob coverage, including commented/empty custom configuration |
| Read `/var/lib/logrotate/status` | `PermissionError`, errno 13 | Last per-file rotation dates cannot be confirmed by this account |
| `/usr/sbin/logrotate --debug /etc/logrotate.conf` | **Exit 1** | Parsed include set and rules; cannot read state, and configured `su` transitions fail under uid 1000. No privileged runtime validation |
| `systemctl show logrotate.timer logrotate.service systemd-journald.service rsyslog.service --no-pager --property=Id,LoadState,ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,LastTriggerUSec,NextElapseUSecRealtime,UnitFileState,FragmentPath` | Exit 0 | Timer active/waiting; latest logrotate service result success and exit status 0; journald and rsyslog active/running |
| `systemctl show logrotate.timer logrotate.service --no-pager --property=Id,ExecStart,ExecMainStartTimestamp,ExecMainExitTimestamp,TimersCalendar,AccuracyUSec,RandomizedDelayUSec,Persistent` | Exit 0 | Actual service command `/usr/sbin/logrotate /etc/logrotate.conf`; daily timer with up to 1h randomized delay; persistent scheduling |
| `Path.stat()` on the nine named logs | All succeed; metadata only | Sizes, modes and modification times; not log correctness, delivery, retention or content sensitivity |

The service last ran 2026-09-16 00:23:01–00:23:03 CEST and reported success.
Next effective timer trigger was 2026-09-17 00:23:46 CEST. An inactive/dead oneshot
service after successful completion is consistent with an active waiting timer;
it is not the same finding as a failed daemon. The debug permission errors must
not be rewritten as either a clean debug pass or a proved root-service failure.

## Coverage of the requested files

Sizes are the 18:15:37 UTC metadata snapshot. Configuration coverage below follows
the main include and evaluates matching patterns, not merely literal filename
searches. Debug could not enter the nginx, PostgreSQL or journal-tail `su` contexts;
their coverage is established by readable selected configuration, not successful
per-file debug execution.

| Named log | Bytes / mode | Selected rule | Remaining evidence |
|---|---|---|---|
| `/var/log/systemd.journal.log` | 113,201,777 / `0644` | `systemd-journal-tail`: `size 64M`, 4 rotations, copytruncate, compression, delaycompress, date extension, `su root adm` | Current size exceeds 64 MiB. The threshold is evaluated at timer runs, not continuously; this alone does not prove rotation failure. Read state and inspect privileged operation through the infrastructure owner |
| `/var/log/syslog` | 17,907,989 / `0640` | `rsyslog`: weekly, 4 rotations, compression, delaycompress | Historical rotation and reopen behavior unverified |
| `/var/log/auth.log` | 3,010,071 / `0640` | Same `rsyslog` stanza | Historical rotation and access appropriateness unverified |
| `/var/log/servers-infra-sync.log` | 7,588,455 / `0640` | **No matching rule in inspected include set** | Owner must establish another existing retention mechanism or add managed rotation |
| `/var/log/loki-disk-watch.jsonl` | 2,628,733 / `0644` | **No matching rule in inspected include set** | Same retention gap; review world-readable mode against actual data class |
| `/var/log/ssh-security-monitor.log` | 3,175,279 / `0644` | **No matching rule in inspected include set** | `ssh-monitoring` file contains only comments; its name is not coverage of this custom log. Review retention and mode |
| `/var/log/postgresql/postgresql-18-main.log` | 49,901 / `0640` | `postgresql-common`: `/var/log/postgresql/*.log`, weekly, 10 rotations, copytruncate, compression, delaycompress | Actual privileged run, file preservation and retention unverified |
| `/var/log/nginx/error.log` | 1,503 / `0640` | `nginx`: `/var/log/nginx/*.log`, daily, 14 rotations, compression, delaycompress, create `0640`, `su www-data adm` | Actual privileged rotation/reopen unverified |
| `/var/log/nginx/access.log` | 550 / `0640` | Same nginx glob | Same operational limitation |

Do not infer that a `.journal.log` filename is the native journald binary store.
This inspected file has an explicit text-log rotation rule. Native journal disk
usage, retention configuration, forwarding duplication and stored event contents
were outside this check. `0644` permits reads by other local users; no claim that
these files contain PII follows from metadata alone. Apply the actual data
classification before changing permissions or retention.

## Correct the Alertmanager claim

“Grouping/inhibition prevents false alarms” is too strong. Grouping combines
related alerts into fewer notifications; inhibition suppresses matching target
notifications while a matching source alert exists. Neither determines whether an
underlying observed condition is true. [Alertmanager concepts](https://prometheus.io/docs/alerting/latest/alertmanager/).

Inhibition requires source/target matchers and equal label values. Missing and
empty labels are treated alike, so incorrectly scoped equality conditions can
silence unrelated targets. `group_wait` delays the first notification and can avoid
notifying an alert that resolves during that wait. `group_interval` and
`repeat_interval` govern subsequent/repeated notifications; their tuning changes
noise and detection latency, not metric correctness. [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/).

Prometheus `for` requires a condition to persist before firing. `keep_firing_for`
can reduce firing/resolution flapping or false resolution during brief data loss.
These mechanisms still depend on the expression, evaluation timing, data quality
and missing-series behavior. [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/).

Suggested replacement: “Grouping, notification timing and scoped inhibition can
reduce duplicate or transient notifications. False-positive control requires
validated metric conditions, missing-data handling and tested rules; observed
notification behavior remains separate evidence.” This is a recommendation;
effective Prometheus/Alertmanager configuration was not inspected here.

A running service proves process state. It does not prove scrape success, fresh
samples, expected label coverage, rule evaluation, notification routing or receiver
delivery. Next infrastructure-owned acceptance should record those layers
separately, test source/target inhibition with synthetic label sets, test recovery
and absent-series behavior, then verify a controlled notification only within an
explicitly authorized receiver scope. No notification was sent by this review.

## Next bounded work

Infrastructure owns the missing custom-log rotation/retention decision and the
privileged state review. Prepare source-managed changes and a synthetic temporary
log demonstration before host apply. Preserve active logs and prove permissions,
rotation/reopen, bounded retention and reader continuity; no forced rotation or
deletion is authorized by this report. Keep monitoring rule tests and actual
receiver delivery separate from service health. The parent delivery plan tracks
host-wide follow-up; this document introduces no additional top-level plan.
