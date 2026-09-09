# Handoff to the Práce v Německu application agent

Updated 2026-09-07 by infrastructure. **First batch deployed: public/private routing separation and exact `.env` permissions.** OCR fallback is also installed and tested; private runtime and complete operational acceptance remain open. See the rollout receipt (infrastructure source reference: `../audits/2026-09-07-prace-first-batch-rollout.md`; not bundled). This does not clear application public deployment, migration, A1 promotion or real-data activation.

## Agreed division of work

Keep OS installation, Ansible, systemd/process supervision, service identities, host permissions, network/public/private routing, certificates, host logging/rotation, Prometheus/Loki/alerts and backup/restore jobs in infrastructure repositories/branches. Core coordinates governance and proof; existing operational implementation stays in the infra operational repository until explicitly migrated. Do not create competing server scripts/backup timers or perform package installs in the application repository.

The application keeps Python requirements and code, settings interfaces, migration logic, health/readiness semantics, protected document behavior, tenant authorization, synthetic functional tests, and its roadmap/approval gates. Return nonsecret requirements to infrastructure; infrastructure provisions and operates the approved release.

## Verified findings relevant to your current plans

- Private synthetic review should use the declared loopback SSH tunnel, or separately approved internal HTTPS. The public apex has been separated from Django: holding page200, private paths404 through s61 HTTPS with valid TLS. The private loopback8000 service remains absent.
- Static nginx `/ready` is now explicitly public-placeholder liveness, not application readiness. Provide the separate application readiness contract and synthetic journey.
- Core's earlier metadata check found root development DB through0007 and synthetic-review DB through0005. That was an earlier observation: the newer application runtime manifest reports synthetic-review0006–0009 applied, but infrastructure has not independently rechecked that persistent DB. Select the target settings/DB explicitly and supply transition evidence, including earlier0006 where needed. Bare default `manage.py migrate` is not a deployment contract.
- Required Python/OCR packages are installed and `pip check` passes. Prior offline core suite passed75 tests; that is not web acceptance. Tesseract/MCP/Redis installation is not required by the selected RapidOCR/ORM-broker architecture.
- Capacity is substantially better than the old93% root baseline:49% used/95G free at observation. Measured workload/concurrency and retained-file growth remain to be budgeted.
- Infrastructure changed only `.env` mode0664 to0600, retaining pavel:www-data, inode/link count/size, and removing effective group/other access. No contents were read/copied; no recursive directory change. Actual second Ansible convergence changed0.
- s62 backup service succeeded. Actual encrypted project coverage and isolated restore remain unproven; current recovery tooling needs repair. This does not block synthetic implementation, but §12 real-data activation remains closed.

Detailed infrastructure plan: DevOps readiness (infrastructure source reference: `../plans/2026-09-07-prace-devops-readiness.md`; not bundled). Evidence comes from three bounded reviews and full core validation; it does not certify the entire application or fleet.

## What infrastructure needs from the application

Provide one small, nonsecret runtime manifest in your normal planning/deployment documentation, with these fields. Do not copy private input trees or secrets into the handoff.

| Required field | What to provide |
|---|---|
| Release | Approved clean commit/release identifier; required source paths and build/static asset procedure; clarify any uncommitted feature dependencies |
| Runtime | Python/package lock location; WSGI/ASGI entrypoint or explicit synthetic command; settings module; required environment variable names only |
| Persistence | Exact synthetic DB path/backend, current/target schema, forward-transition tests and prior-release compatibility; future production DB interface separately |
| Paths and identity | Required read/write directories and temp/cache/model-asset paths; no real filename lists; how to keep synthetic and protected data separate |
| Access | Loopback tunnel acceptance; if private HTTPS is needed, proposed private hostname and authorized user scope; no public exposure inferred |
| Proxy contract | Host/CSRF/secure-header expectations, upload byte/page/pixel bounds, request/job timeouts, static asset route; trusted proxy handling |
| Jobs and OCR | Inline versus separately supervised worker requirement; selected ORM broker; local model assets and no-network functional check; retries/timeout expectations |
| Health and logs | Liveness/readiness behavior, non-PII failure codes/correlation markers; synthetic login/review/upload journey; expected negative responses |
| Recovery | Coherent DB/files snapshot boundary, schema/query/file assertions using synthetic fixtures; migration compatibility for restoration |
| Activation-only inputs | Scanner callable/configuration contract, numeric RPO/RTO and retention agreement, backup-key custodian and alert recipient through approved private channels |

Continue J4/ENG-001 and other synthetic roadmap work while this is prepared. Keep existing real-data/A1 approval rules unchanged. Infrastructure will not repair application business logic by changing host packages or weakening gates.

## Current acceptance receipt and remaining gates

Infrastructure fills this with exact evidence, never an assumed PASS:

| Gate | Current status | Required returned proof |
|---|---|---|
| Public/private separation | PASSED, bounded s61-edge proof | Reviewed scoped IaC snapshot; public200, seven private paths404, TLS verifies; second convergence0. External Internet and reboot proof remain outside this receipt |
| Supervised synthetic runtime | OPEN | After separation: unit/release/settings identity, loopback listener, authorized private access success, controlled failure/restart and persistence evidence |
| Runtime compatibility | OPEN | App-owned migration transition acceptance plus actual selected DB schema and synthetic journey through deployed service |
| Permissions and limits | PARTIAL | Exact `.env`0600 correction and unchanged identity/ownership verified. Future service identity, write paths and upload/temp/concurrency limits remain open |
| Logging/monitoring | OPEN | Non-PII marker query, failure/recovery signal, rotation evidence, authorized notification delivery; certificate/private route checks as applicable |
| Rollback | OPEN | Isolated tested service/config/release rollback; no implied reverse migration or live data overwrite |
| Recovery | OPEN, activation gate | Scope manifest, encryption/custody reference, fresh archive, integrity and actual isolated schema/file restore with RPO/RTO measurement |
| Real-data deployment | NOT AUTHORIZED BY THIS HANDOFF | Separate operational and application activation evidence required by real-data-rules |

For each completed row return: UTC timestamp, infrastructure revision, host/service identity, exact command, exit/status interpretation, artifact path and owning authority. Record remaining limitations explicitly. Update PLAN-INFRA references with received proof; do not mark ENG-001, REV-002, REV-003 or business acceptance complete merely because infrastructure is healthy.

## OCR fallback and database follow-up (2026-09-07)

See the OCR research (infrastructure source reference: `../audits/2026-09-07-prace-ocr-research.md`; not bundled), [fresh host readiness](HOST-READINESS.md), and [SOPS/database migration contract](SECRETS-DATABASE.md). Installation and synthetic execution receipts are reported separately from application integration.

The application benchmark currently records engines as unproven without executing them. Add RapidOCR as the baseline and execute real adapters against synthetic ground truth; keep field-quality acceptance and human confirmation application-owned. Do not infer that an installed Tesseract executable enables automatic fallback. The application must select failure/low-quality triggers, preserve provenance, bound retries, and test review behavior.

Infrastructure owns the optional OCR package capability and model/worker environment. For secrets, use controller-side SOPS decryption and scoped delivery to the selected runtime identity, not private-key propagation across hosts. Database/schema migration and a SQLite-to-PostgreSQL data move are separate rehearsed operations; provide the release/settings/database manifest before either.

Tesseract is now installed with `ces/deu/eng/osd`; both engines passed bounded offline synthetic execution. Read the [OCR rollout receipt](OCR-ROLLOUT.md) for measured errors, resource use, repaired APT trust and exact remaining integration gates. No application fallback adapter has been wired.

## Application contract refresh and local validation

The new `docs/operations/runtime-manifest.md` was reviewed on s62. It documents `/health/` as constant synthetic liveness and `/readiness/` as database/all-app migration checks, with storage/model/release/timeouts still pending. Ten isolated readiness tests passed again through the existing project venv with networking disabled and PostgreSQL test variables unset. Playwright1.62/Chromium launched and rendered a synthetic in-memory page offline; authenticated application journeys have not been run by infrastructure.

The manifest states no configured Q_CLUSTER/worker dispatch; an installed django-q2 dependency is not a running ORM queue. Source is still dirty and includes untracked delivery dependencies. No complete production settings/WSGI/ASGI/static-delivery contract exists. Do not start a durable service from HEAD alone.

Application review must correct `scripts/playwright_smoke.py`: urllib follows redirects and the script accepts anonymous review200 as success. Require an observed redirect to the expected login URL and absence of protected content; cover an intentionally open page as a negative fixture. Review the Node smoke test's raw console/page-error output before testing any authenticated journey.

Use the [application review prompt](PROMPT.md). A self-contained, nonsecret copy of the prompt and selected receipts is delivered inside the s62 project; it is an infrastructure receipt snapshot, not a second application source of truth.
