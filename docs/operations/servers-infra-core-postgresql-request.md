# servers-infra-core PostgreSQL request — supervised synthetic Jan portal

**Version:** 1.0
**Status:** PostgreSQL request awaiting infrastructure response; scoped s62 static/access repair applied and verified 2026-09-17
**Owner:** application team (forwarding to servers-infra-core)
**Forwarding instruction:** Do not send automatically. Deliver this document to the infrastructure team through the agreed channel; the application team does not provision host services.

---

## Requested outcome

Provide a private PostgreSQL target for the supervised synthetic Jan portal, with protected credentials, recoverable storage and a documented operating owner. Provisioning does not authorize real-data activation.

The portal runs under `portal.settings_supervised_synthetic` in supervised synthetic mode. It never activates real-data operations without a separately approved §14 gate. The PostgreSQL target is consumed through documented configuration; the application team does not select hosts, ports, versions or routing.

## Infrastructure decisions requested

Ask the infrastructure agents to:

1. **Inspect before changing.** Review current inventory, deployed configuration and live service health before making any change.

2. **Select the PostgreSQL target.** Choose a currently supported PostgreSQL version from the existing fleet, compatible with Django 5.2 (PostgreSQL 14+). Return the version, transport, endpoint, database name, schema name and access roles. [Django database documentation](https://docs.djangoproject.com/en/5.2/ref/databases/)

3. **Restrict access.** Limit access to the intended application identities and network paths. The application runtime does not require superuser, role-creation or database-creation privileges.

4. **Separate migration access from test-database creation.** Provide migration access through one mechanism. Automated tests must use an explicitly isolated disposable target; test runs must never point database-creation or teardown at the operator database.

5. **Deliver credentials through secret management.** Return references (e.g., secret-store paths, vault keys), never secret values.

6. **Choose service supervision and routing.** Configure supervision for both the WSGI application and the sequential OCR worker. Start with one OCR consumer. Do not supervise the same process through both systemd and the rehearsal launcher simultaneously.

7. **Configure monitoring.** Use existing infrastructure tooling for basic service, storage, connection and backup-failure monitoring.

8. **Define backup and recovery.** Specify backup frequency, retention, recovery objectives and restore ownership. Return measured restore evidence for a disposable target. Backups must use a PostgreSQL-consistent method and account for the application's protected document files. An ordinary live data-directory copy is insufficient; infrastructure chooses the appropriate database backup mechanism and coordinates document-file storage. [PostgreSQL backup documentation](https://www.postgresql.org/docs/current/backup-file.html)

Do not prescribe memory/WAL tuning, replication, an additional cluster or a new monitoring stack without measured need. Replication-lag monitoring applies only if replication is actually selected.

## Corrections to historical instructions

The following earlier prescriptions are explicitly superseded. Infrastructure agents determine the safe repair and record their reasoning; the application team does not reissue host-level commands.

- Fixed host, database port and HTTP port assignments.
- Routing from s61 to s61's loopback as though it reached s62.
- Broad `adm` membership as the preferred logging repair.
- Changing only a child directory when parent traversal is denied.
- Inferring that databases are absent because a stopped cluster cannot answer.
- Treating the rehearsal as a "production mode."
- Backing up a running PostgreSQL data directory through ordinary file copying.

## Required response template

Complete and return this YAML. Missing values remain explicitly unknown.

```yaml
contract_version: "1.0"
status: proposed | provisioned | verified | blocked
observed_at:
infrastructure_revision:
owner:

postgresql:
  version:
  host_or_socket:
  port:
  database:
  schema:
  runtime_role:
  migration_access:
  disposable_test_target:
  tls_mode:
  ca_reference:
  secret_reference:
  connection_budget:

application:
  execution_host:
  service_identity:
  runtime_directory:
  private_upstream:
  operator_url:
  proxy_contract:
  web_supervision:
  ocr_worker_supervision:

operations:
  monitoring_reference:
  backup_method:
  database_file_consistency_method:
  frequency_and_retention:
  recovery_objectives:
  restore_evidence:
  recovery_owner:

verification:
  commands_and_exit_codes:
  authenticated_database_identity:
  privilege_checks:
  access_restriction_checks:
  log_references:
  remaining_gaps:
```

`provisioned` does not mean application acceptance has passed. The application team validates compatibility, runs migration checks and executes the core workflow against the returned target before claiming acceptance.

## nginx/static isolation follow-up — 2026-09-17

The user explicitly approved this exact s62 change packet with “Schválit tento
zásah na server62”: nine specified ACL changes, removal of `www-data`
supplementary `prace-synthetic` membership and a controlled native nginx worker
transition. The primary applied it and verified the scoped result below. The
existing PostgreSQL contract version 1.0 and owner remain authoritative; the
broader infrastructure response is still outstanding. This record preserves the
work order, authorization, before/after evidence and rollback; it does not grant
additional host-change scope or permission to repeat the change against later
state. Do not send secrets or infer authorization from an agent's operator label.

### Measured problem before repair and required outcome

The primary's pre-change `runtime-followup-4952a52f6c91` receipts showed that the `www-data`
account could read
`/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`: the boolean
`sudo -n -u www-data test -r` probe returned 0 without opening the payload.
The account had supplementary `prace-synthetic` GID 981 membership; the containing
directory was 0750 and file 0640, both `root:prace-synthetic`. The two htmx/Tailwind
static MIME/library checks passed through both loopback 8001 and internal nginx
8098; five account/MFA JavaScript assets returned nginx HTTP 403. The required
correction preserved the two working assets and restored the five failed assets
while removing the nginx worker account's secret-reading access.
Running nginx workers 205419, 205420, 205421 and 205422 were also observed with
groups 4, 33 and 981; account changes alone could not remove their inherited access.
See the [corrected triage](s62-operator-triage-report-2026-09-16.md).

Required result: for this application's delivery, grant nginx workers traversal
only on the runtime root and read/traversal only on the reviewed static tree,
with no `prace-synthetic` membership or equivalent ACL path to the EnvironmentFile.
Workers must not traverse the configuration namespace. Systemd keeps
its service configuration access; the application keeps its private data and
service ownership. This work order does not claim confinement against host root.

### Approved change packet and retained procedure

The applied minimal correction preserved the served static bytes and nginx alias.
It added narrowly scoped POSIX named-user ACLs for UID 33, removed `www-data` from
`prace-synthetic`, and transitioned the actual nginx workers. This permission-only
repair required no new application build or asset move. The declared build remains
an observation; it was not repinned or approved by this change.

The primary's `host-apply-preflight.json`, `host-apply.json` and
`host-apply-verification.json` in the private receipt directory bind the concrete
preflight, applied commands and native verification results to this repair.
Infrastructure must still reconcile its operational source revision and desired
state so subsequent deployments preserve this boundary. The retained procedure
requires exact applicable authorization, alias/path manifest, original permission
metadata, affected worker scope, PID/start identities, drain deadline and secure
rollback. Capture only static nonsecret identities and permission metadata;
do not read or copy configuration or private document data.

The primary verified `/usr/bin/getfacl`, `/usr/bin/setfacl` and `/usr/bin/gpasswd`
were installed. Seven explicit paths (configuration directory/file, runtime root,
static, static/portal and both shipped assets) had only owner/group/other ACL
entries, with no named or default entries. Runtime root/static/static/portal were
UID 992/GID 981 mode 0750; both assets were UID 992/GID 981 mode 0640. The primary's
same-filesystem synthetic ACL test exited 0, accepted a named UID 33 entry and
removed its fixture. A bounded traversal check with proposed UID 33/groups 4,33
confirmed access through `/var`, `/var/www`, the repository root, `runtime` and
`runtime/portal`, while `.runtime-config` remained denied. These measured
preflight checks passed, with the fresh apply preflight recorded separately.
Any future use requires fresh relevant metadata and identity checks because these
observations do not freeze host state.

The complete static-only metadata inventory has 13 entries and no symlinks or
unsafe entries, recorded in the private receipt
`runtime/portal/temporary/runtime-followup-4952a52f6c91/static-permission-manifest.json`.
Four additional directories, `static/account`, `static/account/js`, `static/mfa`
and `static/mfa/js`, were mode 0700 and required named-user read/traversal ACLs.
Their five JavaScript files were mode 0644 and already had file-level read access;
they required parent traversal, not file ACL changes. nginx GETs returned HTTP 403
with `text/html` for `account/js/onload.js`, `account/js/account.js`,
`mfa/js/recovery_codes.js`, `mfa/js/webauthn-json.js` and `mfa/js/webauthn.js`.
The private `account-static-route-checks.json` receipt records these failures;
the earlier successful htmx/Tailwind checks do not cover them.

Inventory only the selected static tree, reject symlinks and private/unclassified
files, and return an explicit approved path list. Snapshot metadata only for the
paths to be changed. No recursive ACL operation over the private runtime is
permitted; storage/media/cache/tmp/logs/inbox and `.runtime-config` get no ACL
writes. Preserve application ownership/GID 981, runtime-root mode 0750 and existing
owning-group access. For the four mode-0700 directories, preserve `group::---`;
adding the named-user entry and `mask::r-x` changes the displayed group mode bits
to reflect the ACL mask without granting the owning group access. The other masks
match the observed group permissions. Any different current metadata requires
reconciliation before applying this packet.

These are the nine exact ACL operations and group removal approved by the user
and executed by the primary; every command returned 0. This retained command
record is not an instruction to rerun them:

```bash
/usr/bin/setfacl -m 'u:33:--x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic
/usr/bin/setfacl -m 'u:33:r-x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static
/usr/bin/setfacl -m 'u:33:r-x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/portal
/usr/bin/setfacl -m 'u:33:r-x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/account
/usr/bin/setfacl -m 'u:33:r-x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/account/js
/usr/bin/setfacl -m 'u:33:r-x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/mfa
/usr/bin/setfacl -m 'u:33:r-x,m::r-x' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/mfa/js
/usr/bin/setfacl -m 'u:33:r--,m::r--' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/portal/htmx-1.9.10.min.js
/usr/bin/setfacl -m 'u:33:r--,m::r--' /var/www/prace-v-nemecku.tvoje.info/runtime/portal/supervised-synthetic/static/portal/tailwind-2.2.19.min.css
/usr/bin/gpasswd -d www-data prace-synthetic
```

The primary also ran `systemctl reload nginx`, returning 0, with `nginx -t`
returning 0 before and after. Other observed `www-data` consumers (PHP-FPM)
already had groups 4,33 and remained unchanged. All four old nginx workers were
verified retired by PID/start identity; a successful reload alone would not have
proved that. No historical PID was killed and Gunicorn was not restarted for
this repair. Reconcile the canonical infrastructure desired state so a later
deployment does not re-add the membership or erase the narrow ACLs.

If ACLs are unsupported or this bounded path cannot preserve static delivery,
prepare a separately reviewed immutable static-only publication outside private
runtime/configuration. That alternative requires its final path and source/build
selection, static manifest, nginx alias and rollback before apply; it is not a
prerequisite for the minimal existing-byte ACL correction. Never copy the whole
runtime or checkout to publish assets, and do not describe `collectstatic` as read-only.

### Retained refusal and preservation probes

Run these non-payload probes before and after the authorized change, recording
each native result separately. First prove that the identity switch works:

```bash
sudo -n -u www-data id -u
sudo -n -u www-data id -G
sudo -n -u www-data test -r /var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env
sudo -n -u www-data test -x /var/www/prace-v-nemecku.tvoje.info/.runtime-config
```

The identity probe must return UID 33 successfully. Before the repair, file
readability returned 0 and group 981 was present. Afterward, both `test` commands
must return 1, group 981 must be absent, and privilege-invocation errors must not
be misclassified as denied file access. Do not print or hash file contents.
Independently inspect numeric GID/Groups for every current nginx worker process;
the account-level `sudo` probe alone does not prove existing workers dropped
their previous supplementary groups. No old worker retaining that group may
remain at acceptance. Review any ACL granting an equivalent access path.

For the selected nginx route, verify configuration URLs return a denial without
requesting their content:

```bash
curl --silent --show-error --head --max-time 2 --max-redirs 0 \
  --header 'Host: prace-v-nemecku.expc.cz' --output /dev/null \
  --write-out '%{http_code}\n' \
  http://192.168.1.62:8098/.runtime-config/gunicorn.env
```

Expected native curl exit is 0 with HTTP 403 or 404; timeout, transport failure,
redirect or HTTP 200 does not prove denial. Do not follow redirects or issue a
GET to that configuration path. This URL probe supplements filesystem refusal;
it does not replace it.

Repeat the shipped htmx/Tailwind GET checks with the selected Host on both
`http://127.0.0.1:8001` and `http://192.168.1.62:8098`: require HTTP 200, correct
MIME and expected library marker, and compare bytes against the pre-change static
manifest. Also verify all five reviewed JavaScript files beneath `static/account`
and `static/mfa` through both routes against their expected MIME and pre-change
byte identities; require HTTP 200 after the repair and preserve their before
results separately. Record unit/cgroup/listener identity, declared
build and health before/after. Preserve the selected application's runtime and
DB target; no reseeding, schema changes, credential payload change or release
repinning is included in this static isolation operation. The measured readiness
HTTP 503/deadline result, error-body capture limitation and approved-build
reconciliation remain separate reported outcomes.

### Verified scoped closure

The primary recorded these outcomes in `host-apply-verification.json` after the
authorized apply. They close the measured s62 static/access defects in this
receipt window, not the full PostgreSQL request or whole-host/fleet acceptance.

| Required result | Observed result |
|---|---|
| Actual nginx workers lose secret-group access | Original workers 205419–205422 retired with PID/start identity verified. New workers 512081–512084 are UID/GID 33 with groups 4,33 only. Main nginx PID 205418 remains unchanged |
| Account-level configuration refusal | Identity switch succeeded as UID 33, groups 33,4. EnvironmentFile `test -r` and configuration-directory `test -x` returned 1 with empty stderr; HEAD on the protected URL returned HTTP 403 |
| All seven assets remain byte-identical and available | All seven assets returned HTTP 200, correct MIME and exact pre-change SHA/byte identities on both 8001 and 8098: 14/14 passed; the five former account/MFA HTTP 403 failures are resolved |
| Selected application remains in place | Gunicorn PID 269606, start identity and cgroup are unchanged. Health remains HTTP 200 with declared commit `00786f74fb5321900f9f293f989447e5d7bd8016`; build approval is still separate |
| Other consumers remain unchanged | Observed PHP-FPM processes already carried groups 4,33 and remained unchanged; no other workers were changed |
| Readiness outcome remains explicit | Both routes still return HTTP 503, `deadline_exceeded`, at 2204/2206 ms with the reported 2000 ms budget |

This repair did not read or change the configuration payload, restart the
application, run a live database command or activate real data. The exact ACL
commands, static bytes and alias were preserved as the bounded scope; no new
application build was deployed. Infrastructure desired-state reconciliation is
still required to prevent group/ACL regression. The separate owner decision on
possible prior credential exposure and any rotation also remains outstanding;
current denial cannot prove that no earlier access occurred.

### Retained rollback and outstanding work

If ACL application, asset delivery or worker transition fails, stop the sequence
and reconcile the recorded partial effects. Restore only the selected permission
metadata when safe, or repair the narrow static ACLs within the authorized packet.
Keep the existing alias/bytes for the preferred operation. Once removed, never
restore `www-data` membership in the secret-reading group; retain configuration
directory/file refusal. Do not broaden private-runtime/configuration permissions
to recover static delivery. If reverting the ACL metadata would make assets
unavailable, retain the denied secret boundary and use the operator-selected
unavailable/maintenance response while repairing delivery. The separately reviewed
publication alternative has its own static-only rollback. Preserve application
data and secret custody; this rollback authorizes no credential rollback/rotation.

Keep the before/after refusal results, worker retirement evidence, all-seven-asset
assertions and exact authorization with the applied command receipts. Return
infrastructure desired-state reconciliation and outstanding PG identity,
approved-build/readiness, live core journey, restart, restore and Jan acceptance
gaps independently. None is closed by this scoped repair alone.
