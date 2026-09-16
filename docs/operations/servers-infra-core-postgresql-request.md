# servers-infra-core PostgreSQL request — supervised synthetic Jan portal

**Version:** 1.0
**Status:** request — awaiting infrastructure response
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

This is a concrete infrastructure work request, not an executed or approved host
change. The existing contract version 1.0 and owner remain authoritative. Return
the selected implementation and the evidence below with that contract; do not
send secrets or infer authorization from an agent's operator label. Reuse exact
applicable authorization already granted; otherwise present the completed change
packet to the infrastructure operator before applying it.

### Measured problem and required outcome

The primary's `runtime-followup-4952a52f6c91` receipts show that the `www-data`
account can read
`/var/www/prace-v-nemecku.tvoje.info/.runtime-config/gunicorn.env`: the boolean
`sudo -n -u www-data test -r` probe returned 0 without opening the payload.
The account has supplementary `prace-synthetic` GID 981 membership; the containing
directory is 0750 and file 0640, both `root:prace-synthetic`. The two htmx/Tailwind
static MIME/library checks pass through both loopback 8001 and internal nginx
8098; five account/MFA JavaScript assets return nginx HTTP 403. Preserve the two
working assets and restore the five failed assets while removing the nginx worker
account's secret-reading access.
Running nginx workers 205419, 205420, 205421 and 205422 were also observed with
groups 4, 33 and 981; account changes alone will not remove their inherited access.
See the [corrected triage](s62-operator-triage-report-2026-09-16.md).

Required result: for this application's delivery, grant nginx workers traversal
only on the runtime root and read/traversal only on the reviewed static tree,
with no `prace-synthetic` membership or equivalent ACL path to the EnvironmentFile.
Workers must not traverse the configuration namespace. Systemd keeps
its service configuration access; the application keeps its private data and
service ownership. This work order does not claim confinement against host root.

### Reviewable change packet

The preferred minimal correction preserves the currently served static bytes
and nginx alias. Add narrowly scoped POSIX named-user ACLs for UID 33, remove
`www-data` from `prace-synthetic`, and transition the actual nginx workers. This
permission-only repair does not need a new approved application build or asset
move. Record the current declared build as an observation; do not repin it.

Infrastructure fills in: operational source revision; applying owner and exact
authorization reference; current alias and static-only path manifest; original
ownership/mode/ACL metadata; affected worker/service scope; worker start identities
and drain deadline; secure rollback; and verification commands/native results.
Preserve current static bytes and capture only their nonsecret identities plus
permission metadata. Do not read or copy configuration or private document data.

The primary verified `/usr/bin/getfacl`, `/usr/bin/setfacl` and `/usr/bin/gpasswd`
are installed. Seven explicit paths (configuration directory/file, runtime root,
static, static/portal and both shipped assets) have only owner/group/other ACL
entries, with no named or default entries. Runtime root/static/static/portal are
UID 992/GID 981 mode 0750; both assets are UID 992/GID 981 mode 0640. The primary's
same-filesystem synthetic ACL test exited 0, accepted a named UID 33 entry and
removed its fixture. A bounded traversal check with proposed UID 33/groups 4,33
confirmed access through `/var`, `/var/www`, the repository root, `runtime` and
`runtime/portal`, while `.runtime-config` remained denied. These measured
preflight checks passed; recheck the relevant metadata and proposed identity
immediately before apply, since observations do not freeze host state.

The complete static-only metadata inventory has 13 entries and no symlinks or
unsafe entries, recorded in the private receipt
`runtime/portal/temporary/runtime-followup-4952a52f6c91/static-permission-manifest.json`.
Four additional directories, `static/account`, `static/account/js`, `static/mfa`
and `static/mfa/js`, are mode 0700 and need named-user read/traversal ACLs.
Their five JavaScript files are mode 0644 and already have file-level read access;
they need parent traversal, not file ACL changes. nginx GETs returned HTTP 403
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

These are the reviewable ACL operations for the nine exact delivery paths,
not commands executed or newly authorized by this document:

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

Apply through the canonical infrastructure workflow after checking other consumers
of this shared Unix account. Reconcile desired state so a later deployment does
not re-add the membership or erase the narrow ACLs. Coordinate nginx syntax
validation and the reviewed worker transition: account changes leave existing
process groups unchanged, and reload alone does not prove old workers exited.
Account for every old worker by PID/start identity within the selected deadline;
do not kill historical PIDs or restart Gunicorn for this access repair.

If ACLs are unsupported or this bounded path cannot preserve static delivery,
prepare a separately reviewed immutable static-only publication outside private
runtime/configuration. That alternative requires its final path and source/build
selection, static manifest, nginx alias and rollback before apply; it is not a
prerequisite for the minimal existing-byte ACL correction. Never copy the whole
runtime or checkout to publish assets, and do not describe `collectstatic` as read-only.

### Exact refusal and preservation probes

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

### Rollback and closure

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

Closure requires the before/after refusal results, actual worker group/retirement
evidence, passing static assertions for all seven assets, unchanged intended app ownership/target and
the exact applied source/authorization references. Record a separate owner decision
on possible past exposure and any credential rotation; the boolean audit neither
read the payload nor proved that earlier access never occurred. Return outstanding
PG identity, approved-build/readiness, core journey, restart, restore and Jan
acceptance gaps independently. None is closed by this work request alone.
