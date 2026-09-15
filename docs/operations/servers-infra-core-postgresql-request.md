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
