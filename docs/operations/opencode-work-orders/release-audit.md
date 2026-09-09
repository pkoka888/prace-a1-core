# Release integration audit

Parent: PLAN-INFRA / ENG-001. Run after implementation ownership is released.
Read: approved source/test/plan namespaces from the packet; `scripts/release_verifier.py`,
`scripts/validate_planning.py`, `planning/approval_register.py`, catalog/schema and
approval register. Do not edit approval decisions or production services.

Write: `docs/research/opencode-release-audit-2026-09-06.md` plus an explicit safe
publication inventory `docs/research/opencode-release-paths-2026-09-06.json`.
No Git publication is authorized by this work order.

Check transitive packaging: the existing views import intake_views/document_intake/
document_storage/document_labels, which import src/document_core; include all
required templates, migrations, test settings and harness. Enumerate exact files,
including untracked ones, not a broad directory or wildcard staging command.

Run relevant A1/core/approval tests and the PostgreSQL intake harness. Validate
Django model/migration coherence using isolated test settings only. Run the current
release verifier in its documented synthetic environment; distinguish a verifier's
own unit tests from actual ENG evidence. Inspect the verifier's assertions: a
regex/token check is not proof that a button stores PDF bytes or rejects staleness.
Report legacy baked-count assumptions and missing semantic coverage explicitly.

Run planning validation, asset freshness, relative-link checks and scoped diff checks.
Scan exact proposed source paths for accidental PII/secrets without printing matches.
Keep 34 top-level IDs and the sequence Sprint 1–3 including functioning J4 → ENG-001
→ REV-002 → remaining hardening/OPS/LEG/INF → REV-003.

Expected report: tests with counts/exit codes, remaining failed/pending engineering
checks, exact publication inventory, immutable-receipt coverage, migration order,
rollback, real-data/host gates and proposed status updates. Do not say a release is
complete while required runtime files are untracked. Once publication is explicitly
requested later, the primary agent must check the resulting Git object and run tests
from an exported HEAD snapshot; working-tree success is not sufficient.

## Stabilization closure evidence

Verify current CLI journey tests as well as historical suites; the initial focused
baseline was 5 failures and 33 passes. Include audit/path helpers and new test files
in exact source/dependency inventory. Record implementation, synthetic acceptance
and deployment separately. A SQLite missing-table error does not establish the
production PostgreSQL target. Fresh/historical MigrationExecutor tests prove test
transitions only; identifying and migrating a service database is separately gated.
No bare manage.py migrate instruction belongs in the agent handoff. Unknown
research/runtime artifacts require primary classification; no reorganization here.

Bounded stabilization now passes 157 focused tests and 19 subtests, with 75
passing document-core tests. Preserve the initial failed run as historical evidence.
Check final manifest/PDF/operation-receipt/terminal-event binding; reject dependencies
on the hash of the entire append-only audit log. Review missing-policy and staging
cleanup failures, protected institution inputs, and isolated release-verifier tests.
