# Plan K — server62 Production Readiness

**Status:** planned
**Milestone:** M0–M5
**Owner:** server sysadmin; product engineering verifies application requirements

## Objective

Maintain Debian 13 server62 for the Jan pilot and return an as-built report.
Current measured capacity—root filesystem at 92% with about 7.5 GiB free—requires
monitoring and may require expansion as measured usage grows, but it does not block
application scaffolding or synthetic implementation.

The application and protected runtime directories remain under `/var/www/prace-v-nemecku.tvoje.info`; do not relocate the project to `/srv`.

## Requirements for the sysadmin

- Measure source, dependencies, PostgreSQL, uploads, OCR temporary space, and generated artifacts; expand capacity when an agreed operational threshold or measured pilot forecast requires it.
- Normalize protected-directory and file ownership/modes. Current private directories are mode `700`, but some scan/OCR files are mode `664`; real-data readiness requires a documented least-privilege result.
- Create dedicated non-login service identities and least-privilege directories for releases, shared runtime data, configuration, and logs. Add backup staging only if backups are later enabled.
- Confirm native PostgreSQL, Nginx, systemd service layout, local-only bindings, database roles, patching, and restart behavior.
- Configure DNS/TLS for `portal.prace-v-nemecku.tvoje.info`; reserve the apex domain for the later public product. Stage HSTS conservatively and do not preload/include subdomains prematurely.
- Expose only required SSH/HTTP/HTTPS access; keep PostgreSQL, job workers, storage, Admin, and monitoring private.
- Provide application and proxy upload/time limits, temporary-space controls, MIME/content inspection and malware-scanner integration points.
- Provide SMTP relay, health/error monitoring, disk/certificate alerts, log rotation, time synchronization, and incident contacts as they become necessary for the pilot.
- Define host/service monitoring, capacity thresholds, service recovery, release rollback, permissions verification, TLS renewal/failure response, and owners.
- Do not require backups for initial implementation or pilot activation. Record the accepted non-recoverability risk. If backups are later authorized, implement encrypted database/file consistency, retention, failure alerts, and an actual restore test.
- Separate development/staging/production credentials and prevent secrets from entering Git, logs, or agent output.

## As-built report

Record mounts/capacity, owners/modes, active service versions and bindings,
DNS/TLS status, firewall rules, SMTP, malware scanning, monitoring/alerts,
resource budgets, patch schedule, accepted no-backup risk, and remaining risks.
If backups are later introduced, add their target/schedule/retention and restore
result. Do not include credentials.

## Exit gate

- Required TLS, isolation, permissions, and current operational monitoring are demonstrated.
- Capacity is measured and remains within the accepted threshold.
- The controlled Jan pilot may proceed with an explicitly accepted no-backup risk. A later production/public release requires an explicit durability decision and evidence; backup/restore is required only if that decision enables backups.
- Product engineering verifies the application can use the supplied paths/services with least privilege.
- `manage.py check --deploy` and synthetic upload/job/download smoke tests pass after M2 deployment.
- New real-data portal uploads remain disabled until the activation gate in `docs/security/real-data-rules.md` passes.

## Exclusions

No application scaffolding by the sysadmin, no public database/storage consoles, and no assumption that installed packages are configured or active.
