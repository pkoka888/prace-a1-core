# Plan E — Architecture Proofs and ADR-001

**Status:** completed
**Milestone:** M1A
**Owner:** product engineering

**Validation checkpoint (2026-08-17):** all eight executable synthetic checks
pass and `run`/`verify` bind their results to the source and fixture hashes in
`docs/architecture/adr-001-evidence/manifest.json`. Production capacity,
encrypted backup/restore, malware operations, deployment, and real data retain
their separate gates; they are not claimed by this proof.

## Objective

Convert the provisional Django direction into a measured, reproducible architecture decision for Jan's private portal.

## Provisional proof baseline

The operational Plan L governance baseline and minimal Plan M catalog are
sufficient to start all synthetic proofs below. Broader Plan L/M exit work does
not block Plan E evidence production. Pavel accepted the architecture direction
and all selected components on 2026-08-17. The measured checks validate those
choices and may reopen a failed choice; approval alone is not authority to
scaffold or deploy the portal.

- Django 5.2 LTS, Python 3.13, PostgreSQL, Django templates with targeted HTMX.
- Shared database/schema with mandatory `Organization` ownership and membership-based authorization.
- Existing A1 engine behind an internal Python service interface, not a network service.
- Preferred server62 topology: systemd, native Nginx and native PostgreSQL.

## Proofs

1. Compare `django-allauth[mfa]` and `django-two-factor-auth` for forced TOTP, recovery, password reset, session invalidation, rate limiting, Czech/German templates, and protected Admin access.
2. Compare `django-q2` using its ORM broker with Celery/Redis for OCR and A1 jobs. Exercise retries, timeouts, duplicate delivery, cancellation, progress, worker crash/restart, and idempotency.
3. Prove encrypted-filesystem document storage using opaque object keys, quarantine, content/MIME/size checks, malware scanning, authorized Nginx `X-Accel-Redirect` delivery, and audited access. Compare one maintained S3-compatible backend only if a documented migration or operations need justifies it.
4. Prove organization isolation at queryset, view, form, task, Admin, and download layers.
5. Compare `django-auditlog` model diffs with required custom append-only `AuditEvent` behavior for authentication, authorization, document access, exports, reviews, and approvals.
6. Wrap one synthetic employee/assignment through A1 validation, generation, preview, failure reporting, and artifact hashing without importing Django into the A1 engine.
7. Measure installation size, steady/peak memory, CPU, disk/temp use, job duration, recovery behavior, and service count on server62-compatible staging.
8. Produce a Release 1A threat model with assets, actors, trust boundaries, abuse cases, mitigations, residual risks, and owners; exercise synthetic authorization, upload, download, task, audit, and data-flow abuse cases.
9. Review dependency versions, maintenance, licenses, security support, and upgrade constraints; define application observability without PII.
10. Prove deployment and application rollback, including migration limits, worker/version skew, artifact compatibility, and safe resume criteria.

## Synthetic proof sprint contract

This section is the implementation-ready plan for the next bounded sprint. The
eight `tests/fixtures/release_1a/` JSON files, schema, manifest, deterministic
upload-sample generator, preflight command, and focused preflight tests are
delivered inputs—not proof evidence. Other paths remain prospective.

### Exact deliverables

| Path | Purpose |
|---|---|
| `prototypes/architecture/adr001/project/settings.py` | Minimal disposable Django settings, isolated from any future production settings |
| `prototypes/architecture/adr001/project/urls.py` | Only the endpoints needed for MFA, authorization, protected download, job, audit, and A1-boundary proofs |
| `prototypes/architecture/adr001/apps/` | Small disposable proof modules outside `portal/`; no production scaffold, migration, or deployment claim |
| `tests/fixtures/release_1a/` | Synthetic organizations, users, documents, assignments, and A1-shaped inputs with an explicit fiction manifest |
| `tests/architecture/test_mfa_proof.py` | Forced MFA, recovery, reset, session invalidation, rate-limit, and Admin cases |
| `tests/architecture/test_tenant_isolation.py` | Queryset/view/form/task/Admin/download cross-organization denial matrix |
| `tests/architecture/test_job_recovery.py` | Retry, timeout, duplicate delivery, cancellation, crash/restart, progress, and idempotency |
| `tests/architecture/test_protected_storage.py` | Quarantine, MIME/content/size checks, opaque keys, authorization, and internal delivery |
| `tests/architecture/test_audit_contract.py` | Required event coverage, immutability, attribution, denial events, and sensitive-payload exclusion |
| `tests/architecture/test_a1_boundary.py` | Django-independent validation/generation boundary, failures, preview/hash, and stale snapshot behavior |
| `tests/architecture/test_transactions.py` | Concurrent review, assignment edit, outbox/audit atomicity, and safe retry |
| `tests/architecture/test_rollback.py` | Previous-version compatibility, migration reversal/forward-fix classification, and worker-version skew |
| `scripts/run_architecture_proofs.py` | Delivered fail-closed preflight and upload-sample generator; measured `run`/`verify` phases remain unproven |
| `docs/architecture/release-1a-threat-model.md` | Assets, actors, trust boundaries, abuse cases, mitigations, residual risks, and owners |
| `docs/architecture/adr-001-dependency-review.md` | Exact versions, upstream support, licenses, vulnerability review, alternatives, and upgrade policy |
| `docs/architecture/adr-001-evidence/manifest.json` | Schema-versioned environment, commit, dependency lock hash, fixture hashes, commands, results, durations, and artifact hashes |
| `docs/architecture/adr-001-proof-report.md` | Scored comparison, sensitivity analysis, failures, operational cost, recommendation, and unresolved risks |
| `docs/decisions/ADR-001-jan-portal-architecture.md` | Accepted direction plus validation status, consequences, and unresolved risks |

Generated evidence contains synthetic measurements and hashes only—never document
contents, credentials, host secrets, real paths outside the project, or PII.

### Sprint sequence

1. **Harness and fixtures:** extend the delivered preflight with proof settings,
   package pins, deterministic clock/IDs, result schema, and explicit proof that
   protected paths and real-data environment variables are neither required nor read.
2. **Security boundary:** implement the organization authorization matrix,
   upload/quarantine checks, opaque protected delivery, MFA candidates, and
   append-only audit contract. Run negative cases before happy paths.
3. **Reliability boundary:** compare queue candidates under duplicate delivery,
   retry, timeout, crash/restart, cancellation, version skew, and outbox/audit
   atomicity. Business commands must be idempotent.
4. **A1 boundary:** pass the J4 synthetic profile through a Django-independent
   interface and prove failure reporting, deterministic hashes, source-change
   staleness, and no prepared/official status confusion.
5. **Operations and rollback:** measure both candidate stacks on one recorded
   server62-compatible synthetic environment; test deploy, migration limits,
   worker skew, rollback/forward-fix, and safe resume.
6. **Validation:** complete the threat model, dependency/license review, weighted
   scoring plus doubled-security and doubled-speed/cost sensitivity runs, then
   update the accepted ADR validation record and reopen only a choice rejected by
   a critical check.

### Commands

Once the named files exist, the sprint must expose these stable commands:

```bash
venv/bin/python -m pytest tests/architecture -q
venv/bin/python scripts/run_architecture_proofs.py preflight --json
venv/bin/python scripts/run_architecture_proofs.py run --candidate all --json
venv/bin/python scripts/run_architecture_proofs.py verify --manifest docs/architecture/adr-001-evidence/manifest.json --json
venv/bin/python scripts/validate_planning.py --json
git diff --check
```

`preflight` and `verify` are non-mutating. `run` refuses undeclared output paths,
protected-data paths, missing fiction markers, an unrecorded environment, and any
candidate outside the exact approved comparison matrix. Exit codes are `0=pass`,
`1=proved failure`, and `2=unproven/environmental`; only `0` evidence may support
ADR-001.

### Measurement environment

Record Python, OS/kernel, CPU quota/model, memory limit, filesystem type/free
space, PostgreSQL version/config class, process/service count, dependency lock
hash, fixture scale, warm-up count, repetitions, and monotonic timestamps. Use
the same isolated synthetic dataset and resource limits for every candidate.
Report median and worst observed duration/RSS/CPU/disk/temp use; do not discard
failed or timed-out runs. At least three measured repetitions follow one warm-up.
Host facts are re-probed read-only and sanitized; host mutation remains Plan K.

### Pass/fail thresholds

- **Authorization:** every cross-organization queryset, view, form, Admin, task,
  and download case denies access server-side; protected-download denial returns
  zero file bytes. Any bypass rejects the architecture candidate.
- **MFA:** every privileged role is forced through TOTP; recovery tokens are
  single-use; password reset and privilege/credential changes invalidate relevant
  sessions; protected Admin cannot bypass MFA. Any bypass rejects the package.
- **Uploads/storage:** disguised executables, MIME/content mismatch, oversize,
  traversal, public/static exposure, and unauthorized delivery all fail before
  OCR or byte delivery. Stored keys reveal no identity data.
- **Jobs/transactions:** every injected retry, duplicate delivery, timeout, and
  crash produces at most one committed business effect; recoverable work resumes
  without manual database edits; audit/outbox records commit atomically with the
  command. Lost or duplicated effects reject the candidate.
- **Audit:** 100% of the event classes required by the real-data policy are
  exercised; events are attributable and append-only; fixture identity/document
  contents and secrets are absent from audit payloads and ordinary logs.
- **A1 boundary:** the A1 package imports no Django module, deterministic reruns
  have identical declared hashes, source changes mark artifacts stale, and no
  prepared package can become an official certificate without a separate event.
- **Dependencies:** all selected versions support the chosen Python/Django matrix,
  have compatible licenses and an identified maintenance path, and have no known
  unmitigated critical/high vulnerability at review time. Unproven support rejects
  acceptance.
- **Capacity:** measured peak plus the recorded pilot-growth reserve must preserve
  Plan K's 15 GiB/15% free-space gate and must not exceed the recorded service
  memory/CPU envelope. A candidate with an unbounded worker or temp-file profile
  fails regardless of speed.
- **Rollback:** a synthetic previous release is restored or safely forward-fixed
  within 15 minutes, with zero loss of committed synthetic records/artifacts and
  no incompatible worker left consuming jobs. Irreversible migrations require a
  separately accepted forward-fix plan before ADR acceptance.
- **Reproducibility:** a clean rerun from the pinned lock and fiction manifest
  verifies every evidence hash and produces the same pass/fail disposition.
  Flaky, skipped, redacted-to-meaninglessness, or environment-unknown results are
  `unproven`, never pass.

### Review and rollback

The proof sprint may be reverted by removing only its named proof modules,
synthetic fixtures, tests, scripts, and tracked synthetic reports. It must not
touch canonical A1 production code, protected inputs/outputs, host services,
database clusters, remotes, or secrets. Failure of a candidate is retained as
decision evidence; it is not repaired by weakening a threshold. After all gates
pass, engineering attaches the manifest, proof report, threat model, dependency
review, and rollback result. A critical failure reopens the affected accepted
choice. The validator—not approval alone—opens the implementation gate.

## Decision record

ADR-001 must state selected packages and versions, deployment topology, storage/backend choice, trust boundaries, data flow, alternatives rejected, evidence, operational costs, upgrade policy, rollback path, and unresolved risks. Use declared scoring weights: workflow fit 20%, security/privacy 20%, maintainability 15%, delivery speed 15%, operations 10%, integration 10%, cost 5%, migration/exit 5%. A critical authorization, maintenance, licensing, recovery, or privacy failure rejects a candidate regardless of score; run speed- and cost-doubled sensitivity checks.

The [Google AI Studio frontend review](../docs/prototypes/2026-08-13-google-ai-studio-frontend-review.md)
is provisional comparison evidence only. Its export was rejected for direct import;
ADR-001 must still decide between Django templates/HTMX and a Next.js frontend
with an explicit Django API and operational boundary.

## Exit gate

- Proof results are reproducible from synthetic fixtures.
- Dependency compatibility is confirmed against Python 3.13/Django 5.2.
- Failure and tenant-isolation tests pass.
- Threat model, dependency/license/version review, observability contract, deployment rollback proof, and synthetic abuse/security cases are accepted.
- Sysadmin topology constraints are incorporated.
- ADR-001 direction is approved and every required check in
  `planning/approvals.json` passes before application scaffolding begins.

## Exclusions

No real PII, MinIO default, original `django-q`, Supabase deployment, public frontend selection, or production rollout.
