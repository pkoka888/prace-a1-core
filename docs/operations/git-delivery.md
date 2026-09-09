# Git delivery safeguards — 2026-09-08

Parent: PLAN-INFRA. Scope: source-delivery policy and bounded delivery evidence.
No deployment, new runner/remote, history rewrite or real-data processing.

## Current operating policy — 2026-09-08 consolidation

[AGENTS.md](../../AGENTS.md) is the concise operational authority. This section
supersedes historical blanket requirements to repeat working-tree tests in an
export for every small change. Historical results below remain evidence for their
own scopes, not additional present-day gates.

| Change | Required verification |
|---|---|
| Documentation | Relevant links/status consistency, whitespace and staged-content review |
| Ordinary code | Focused regression checks once against delivered inputs |
| Migrations, storage, authorization, shared rendering or dependencies | Relevant integration checks; historical migrations use MigrationExecutor |
| Release candidate | One reproducible committed-source acceptance run |
| Generated A1 package | Artifact-specific deterministic checks and local all-page visual review |

Reuse evidence only when tested source, dependencies and configuration match.
Inspect the committed path/blob set and scope completeness; `git diff-tree` proves
contents, not runtime behavior. Use an exported-source check when the dirty tree
cannot establish matching delivered inputs, and for integration/release acceptance.
Do not rerun an unchanged suite merely because a commit was created. Existing
mandatory hooks remain effective until deliberately updated; no bypass is authorized.

Routine implementation and private origin feature-branch publication need no extra
permission. Coherent code/tests/migrations/docs may share a commit. Keep unrelated
work separate; inspect explicit staged paths and all outgoing commits. A failure
blocks the behavior it covers; record unrelated failures and continue independent
safe work. No history rewrite, force-push, public release, deployment or activation.

### Revision-checked BO identity association — 2026-09-10

| Field | Evidence / state |
|---|---|
| Implementation | BO signed worker choices bind actor, organization, reviewed run set/evaluation, worker version and identity revision. POST validates under locks and calls canonical identity resolution; an override requires a reason. GET saves no evaluation or decision. The shared evaluator checks the derivative source hash. Failed/superseded batch members do not disable completed current document choices |
| Validation | Focused PostgreSQL association/intake/identity integration in progress; final results and committed-source receipt will be recorded here. Planning checks pass 24/24. No schema or rendering change |
| Publication | Local implementation pending scoped commit; inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; disposable synthetic tests only; historical databases and working PDF packages preserved |
| Activation | Unchanged. Association does not confirm individual fields, verify identity or imply A1 submission/issuance |
| Limitations | Scope is initial region association and resolution of matching conflicts. Reassignment of an already-decided association is not introduced. Selected supervised release still requires migrations 0014–0018 before runtime use |
| Next owner | Engineering: synthetic legacy-key reconciliation with explicit mappings/collision rejection, then complete revision-bound CSV/cohort/identity compatibility exports and round-trip evidence. Accepted cutover remains governed by existing DB-MIG dependencies |

### Revision-checked BO field review — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | BO sends tokens bound to exact proposal/source/OCR result, worker association and current identity revision. A locked batch validates all selections before existing canonical field confirmations, preserving atomicity. Confirmed values are shown separately from OCR and are the initial edit value; replacing one requires a reason. Stale forms return 409 with no partial decisions. Missing/non-reviewable proposals do not disable other reviewable fields |
| Validation | All 32 PostgreSQL field-review/intake tests passed, including independent-connection stale-form rejection, batch rollback, deleted selections, omitted values, derivative/source mismatch and confirmed-value replacement reasons. Planning checks pass 24/24. Required hooks passed, including 189 Django tests with 21 environment-specific skips. Committed-source `811c1d1` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 73 workflow tests with three PostgreSQL-only skips covered separately; source integrity remained intact. No model/schema or renderer changes |
| Publication | Implementation committed locally as `811c1d1`; this evidence-only checkpoint preserves its tested source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; disposable synthetic tests only; existing environments unchanged |
| Activation | Unchanged. No automatic confirmation, worker projection overwrite, A1 issuance or real-data activation |
| Limitations | Canonical non-BO programmatic confirmations retain their existing explicit API. BO association/conflict resolution still needs integration with the existing expected-worker/revision identity service. Field confirmation is distinct from whole-person verification and A1 visual review |
| Next owner | Engineering: identity association/conflict resolution in BO with expected worker and identity revisions; then reconciled legacy cutover |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/b9ebbf5d137347ba97632ea1df69036d/receipt.json`.

### Generation-bound visual confirmation — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0018 adds an immutable generation-specific visual confirmation with actor/time and source/fingerprint/PDF/receipt hashes. BO requires explicit review of all three pinned previews and submitted expected tokens. The service verifies current source/package/dependencies under organization locks, rechecks after insertion, and records an atomic audit. Retries retain the original confirmation. Historical packages receive no automatic confirmation; rollback refuses to discard review records |
| Validation | All 15 PostgreSQL service/access/HTTP tests passed, including authorization, stale input, CSRF, audit rollback, independent-connection concurrency and MigrationExecutor preservation/rollback protection. The existing 17-test J4 delivery workflow passed. Initial route-wiring errors were corrected before this acceptance; the legacy regenerate guard remains separate. Required hooks passed, including 180 Django tests with 20 environment-specific skips. Committed-source `bbbbf4c` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 64 workflow tests with two PostgreSQL-only skips covered by the separate PostgreSQL run; source integrity remained intact. Model/migration parity and 24 planning checks pass. Renderer and package bytes are unchanged |
| Publication | Implementation committed locally as `bbbbf4c`; this evidence-only checkpoint preserves its tested source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; migration is exercised only on disposable synthetic databases. Selected supervised release needs 0014–0018; its existing database remains at recorded 0013 |
| Activation | Unchanged. These tests use synthetic actors/data. Production identity verification, readiness, case visual fields and submission/issuance are untouched; visual review does not establish correct identity facts |
| Limitations | Confirmation belongs to one exact generation. A replacement has no inherited review; reusing an identical earlier generation retains its original evidence. The protected package is immutable and its initial pending marker is historical; the structured DB confirmation owns subsequent visual-review evidence. Legacy non-draft case behavior is preserved |
| Next owner | Engineering: BO identity/field confirmation using expected revisions, explicit source associations, conflict handling and protection against OCR overwrite. Reconciled legacy cutover remains separate |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/fe8f1eaf45f048098c62fd88a8edacda/receipt.json`.

### BO access to applicable A1 generations — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | New read-only generation access service selects by current source/profile/dependency fingerprint. BO detail pins generation IDs in PDF/all-page preview links. Stale explicit links fail; unpinned access resolves the applicable generation, including dependency reversion. Returned bytes, PNG format/dimensions and receipt hashes are checked; responses are private/no-store and HTTP reads audited |
| Validation | Seven focused synthetic access tests passed after correcting invalid-page handling and using the versioned assignment service in the source-change test. The existing 17-test J4 delivery workflow passed. Tests cover stale/reverted dependencies, tenant/role/activation denial, no GET generation, legacy action separation, tampered bytes and post-verification preview geometry changes. Planning has 24 passing checks. Required hooks passed, including 172 Django tests (18 environment-specific skips). Committed-source `a58ed39` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 56 workflow tests; source integrity remained intact. No renderer or generation-input contract changed |
| Publication | Implementation committed locally as `a58ed39`; this evidence-only checkpoint preserves its source blobs. Inherited outgoing history still needs content/provenance review before private-origin publication |
| Deployment | None; selected supervised release and database unchanged |
| Activation | Unchanged. No real-data activation, new generation on GET, human confirmation, submission or issuance |
| Limitations | Existing non-draft case behavior is retained. Draft cases cannot enter legacy approval/regeneration/confirmation endpoints; generation-bound confirmation remains unimplemented. Historical stale packages are preserved but are not served as applicable review copies |
| Next owner | Engineering: generation-bound visual confirmation with expected source/fingerprint/receipt, actor/time evidence and stale rejection; keep identity verification distinct. Follow with identity/field BO integration and reconciled cutover |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/2f4f1bba826442079c0ae4fab62fdcb6/receipt.json`.

### A1 generation revisions — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0017 adds immutable render generations under each stable number reservation. Exact snapshot/dependency fingerprints deduplicate retries; changed profiles/templates/builds receive their own package. Earlier packages and the original case projection are preserved. Inbox and command return the matching generation reference/revision. Migration copies existing reservations/packages and prevents rollback that would lose generation-only evidence |
| Validation | Eight focused draft tests passed. Model/migration parity and 24 planning checks passed. Two synthetic generations/six pages were inspected locally; number, boxes, blank dates and Section 5 remain correct, and only the intended institution address changes. The 94-test PostgreSQL run passed 92 tests and exposed two incomplete historical test fixtures (missing required birth dates), corrected without changing runtime code. The affected PostgreSQL migration/concurrency module then passed all six tests. Required hooks passed. Committed-source `67559c8` acceptance passed all three commands (planning, tooling/A1 and inbox/identity/input/generation); source integrity remained intact |
| Publication | Implementation committed locally as `1fb8da1`; historical fixtures corrected in `67559c8`. Inherited outgoing history still requires content/provenance review before private-origin publication |
| Deployment | None. Migration 0017 runs only in disposable synthetic tests. Selected supervised release needs 0014–0017; its existing database remains at recorded 0013 |
| Activation | Unchanged; all generations remain unverified. No human confirmation, submission, issuance or real-data portal activation |
| Limitations | BO still reads the older case artifact projection. Dependency reversion reuses the matching prior generation; numeric revision order alone does not establish current applicability. Changed source facts require a new immutable input case. Running processes must restart after code changes |
| Next owner | Engineering: organization-scoped BO access to the exact applicable generation, followed by expected-generation and expected-source confirmation with stale rejection; keep visual review separate from identity confirmation. Legacy reconciliation/cutover remains separate |

Protected synthetic visual manifest:
`runtime/portal/temporary/a1-generation-visual-dfe8o90t/manifest.json`.
Local engineering review does not set human confirmation or promote an artifact.
Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/293d0b27f5a844c4be0a3a58fdf0945e/receipt.json`.
This evidence-only checkpoint preserves the accepted implementation blobs.

### Unverified application-draft publication — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Synthetic inbox and `a1_prepare_draft` use the new explicit pending-input contract in the existing canonical publisher/core. Migration 0016 reserves immutable numbers, source/profile/dependencies and package keys. J4 publication recovers the same package after a DB/audit failure. Every page displays UNVERIFIED DRAFT; unknown certificate dates and human flags are preserved |
| Validation | 87 PostgreSQL integration tests passed, including simultaneous reservation, historical 0015→0016→0015 and package recovery. 37 focused inbox/identity/draft tests and 13 artifact tests passed. 54 core/finalize/stabilization tests plus 18 subtests passed; normal-mode comparison across three profiles/nine pages has zero changed pixels at 300 DPI. Three synthetic draft PDFs/nine fresh previews were locally inspected; checkboxes, blank dates, notices and Section 5 output match the explicit draft contract. Models match migrations; planning is 24/24. The required hook exposed four stale comprehensive expectations, reproduced unchanged on the prior renderer; fixtures/assertions now follow explicit posting and established natural casing without altering renderer behavior. Required staged hooks passed. Committed-source `09d28dd` acceptance passed 23 applicable planning checks, 98 tooling/A1 tests plus 18 subtests, and 46 inbox/identity/input/draft tests; source integrity remained intact |
| Publication | Implementation committed locally as `09d28dd`; this documentation checkpoint records its acceptance. Inherited outgoing history requires content/provenance review before private-origin publication |
| Deployment | None; disposable synthetic databases only. Existing supervised DB remains at recorded 0013 and needs selected-release 0014–0016 before runtime use. No employee PDFs or services changed |
| Activation | Unchanged; synthetic-only capability-checked adapter. Application drafts are not human-verified, visually approved, submitted or issued certificates |
| Limitations | One reservation/package per immutable input case. A changed template/profile/code dependency fails closed; a replacement generation-revision lifecycle for unchanged inputs is not implemented. BO artifact access/confirmation still uses the earlier J4 contract. Source changes require process restart, avoiding loaded-code/font mismatch. Local command returns private paths; no public links or production activation |
| Next owner | Engineering: generation revisions preserving prior numbers/packages across dependency changes, then BO artifact access and revision-checked confirmation. Legacy reconciliation/cutover remains separate |

Protected synthetic visual manifest:
`runtime/portal/temporary/a1-draft-visual-j7ktekp1/visual-manifest.json`.
Local visual inspection is engineering evidence, not a human identity decision or
an artifact promotion. The canonical checkbox receipt records the unchanged
normal-mode pixel comparison against the previous renderer.

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/b85bce63e9684e6d936e06e29e8688a6/receipt.json`.
This evidence-only checkpoint preserves the tested implementation blobs.

### Revision-bound A1 input preparation — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Migration 0015 adds structured assignment facts. Synthetic version-checked updates and `a1_exports.py` prepare immutable input cases and export all 44 canonical CSV fields plus JSON provenance. Inbox records case references and missing-fact blockers. Accepted identity revisions override pending OCR; retries reuse inputs and stale exports fail closed. Assignment dates are pinned but never silently become certificate dates |
| Validation | Focused input tests pass, including malformed pending dates, accepted overrides, stale assignment periods, corruption, authorization, audit rollback and Section 5 defaults/overrides. Planning/tooling regression: 124 tests passed; model/migration parity reports no changes. 80 PostgreSQL integration tests passed, including concurrency and historical 0014→0015→0014 migration. Planning is 24/24 after adding exact synthetic test paths to the existing allow-list. Required hooks passed. Committed-source `d83fc0d` acceptance passed all three commands: 23 applicable planning checks, 91 tooling/A1 tests plus 9 subtests, and 41 inbox/identity/input tests; source integrity remained intact |
| Publication | Implementation committed locally as `d83fc0d`; this documentation checkpoint records its completed acceptance. Inherited outgoing history still requires content/provenance review before private-origin publication |
| Deployment | None. Migration 0015 is exercised only in disposable test databases; supervised development remains at recorded migration 0013. Existing databases, services and PDF packages are preserved |
| Activation | Unchanged; new input services are synthetic-only and capability checked. No machine action creates human verification or official issuance |
| Limitations | Input preparation only: no PDF, number reservation, complete compatibility package, institution-profile pinning or BO UI adapter. Canonical readiness retains its current human flags; this service does not forge them. The richer target snapshot/export contract and legacy cutover remain incomplete |
| Next owner | Engineering: explicit unverified application-draft mode through the shared publisher/core, DB-stable provisional numbering and artifact-specific deterministic/all-page visual checks. BO revision integration proceeds in parallel. Apply 0014/0015 through the selected supervised release before runtime use |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/1eb55479d4014569be04b90c8c2aede6/receipt.json`.
This evidence-only checkpoint preserves the tested implementation blobs.

### J2 durable identity and unconfirmed drafts — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Additive migration 0014 adds immutable service-level evaluation/claim/resolution records. Inbox persists evaluated evidence, preserves manifest hashes and explicit per-file profiles, and creates or reuses eligible unconfirmed drafts. Conflicting batch profiles propagate to all identifier peers. Explicit resolution rechecks source fingerprints and expected worker version/revision, requires an override reason, and binds the human association to its evidence. Organization mutexes use PostgreSQL NO KEY UPDATE to coexist with OCR foreign-key checks |
| Validation | 68 PostgreSQL integration tests passed, including simultaneous evaluation/draft/resolution, competing decisions, OCR completion overlap, and historical 0013→0014 migration/uniqueness. 32 focused SQLite workflow tests, 14 historical-migration/reproducer tests and 76 planning/catalog tests passed; model/migration parity reports no changes; planning is 24/24. Required hooks passed. Committed-source `165491c` acceptance passed 23 export-applicable planning checks, 91 tooling/A1 tests plus 9 subtests, and all 32 inbox/identity tests with source integrity intact. Review found and corrected profile propagation and an OCR/organization lock interaction |
| Publication | Implementation committed locally as `165491c`; this documentation checkpoint records its completed acceptance. Inherited outgoing history still requires content/provenance review before private-origin publication |
| Deployment | No existing environment migrated; supervised development remains at its recorded 0013 state. New migration tested only in disposable databases; no services or PDF packages changed |
| Activation | Unchanged; new identity services are synthetic-only and require active authorized operators. No new real-data activation |
| Limitations | BO forms still use their existing association/field-confirmation paths; new revision-checked resolution is a service ready for UI integration. New drafts are not confirmed identities, active workers, issued certificates or A1 PDFs. Missing profile, incomplete/conflicting evidence and possible existing workers defer only draft creation |
| Next owner | Engineering: connect draft workers to DB-MIG input mapping/shared exports and J4 unverified A1 generation; integrate BO revision checks in parallel, without gating eligible drafts on BO completion. Apply 0014 through the selected supervised development release before runtime use |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/b98a200ed2634096ac4cd0c6b84cd825/receipt.json`.
The documentation-only checkpoint preserves the tested implementation blobs and
clarifies that BO UI work runs in parallel with the next A1 generation increment.

### J2 derived identity suggestions — 2026-09-09

| Field | Evidence / state |
|---|---|
| Implementation | Inbox recomputes shared-core identity suggestions across completed batch regions. Protected receipts bind run/version/output hashes, confirmed-worker snapshot hash and decision/revision references. Conflicting identity field evidence blocks suggestions; matching failures remain retryable partial batches. Confirmed fields, worker links and human decisions are unchanged |
| Validation | Full shared core: 92 tests passed. Ephemeral PostgreSQL intake/inbox/readiness/J4: 49 tests passed, including all 19 inbox tests. Planning: 24/24 checks passed. Static scoped review found no additional defects. Required hooks passed. Committed-source `db6c472` acceptance passed all three commands: 23 export-applicable planning checks, 91 tooling/A1 tests plus 9 subtests, and 19 inbox tests; source integrity remained intact |
| Publication | Implementation committed locally as `db6c472`; this documentation checkpoint records its completed acceptance. Private-origin publication remains pending review of the inherited outgoing batch, not engineering permission |
| Deployment | None; isolated synthetic test databases only. Existing supervised, historical and production databases/packages are unchanged |
| Activation | Unchanged; existing real-data-rules §14 remains the portal gate |
| Limitations | Derived suggestions are not durable identity decisions or BO acceptance tokens. Name-only matches/new identities remain unresolved; no worker creation or A1 draft generation. Receipt evidence must be revalidated before future revision-checked writes |
| Next owner | Engineering: durable J2 identity/conflict resolution and safe draft-worker creation under DB-MIG-1/2/5, with PostgreSQL uniqueness/concurrency and stale-revision acceptance, then J4 drafts/BO |

Protected committed-source receipt:
`runtime/portal/temporary/release-reproducer/f6a08e372b914983918443c9bbcdc793/receipt.json`.
The documentation-only evidence checkpoint preserves the tested implementation blobs.

### Readiness and roadmap repair — 2026-09-09

OpenCode's cross-reference feedback confirms the bounded `cba3e50` delivery.
Its remaining-work concern is valid: inherited work is not delivered merely
because it exists locally. The review also found older roadmap sections that
contradicted the new contract despite passing structural validation; these are
corrected here. A new Recent Learnings section is optional, not another gate.

| Field | Evidence / state |
|---|---|
| Implementation | Explicit `readiness --provisional`; one shared CSV required-field helper used by readiness and validation; report/summary mode and review_preflight scope; authoritative default and human flags retained. Roadmap/index now distinguish implemented components, fresh synthetic preparation and gated cutover; M4-A model/export/dashboard claims corrected |
| Validation | Exported A1 source: 47 tests and 9 subtests passed; required hook repeated that focused suite successfully. Documentation source checks: 44 field rows, 97 relative links and 24/24 planning checks passed from the staged-source export |
| Publication | A1 implementation `445aee1`; separate documentation checkpoint carries this record. Exact commits/remote SHA and result are in protected runtime receipt and operator handoff |
| Deployment | Not performed; no service, historical database, employee PDF or migration changes |
| Activation | Unchanged; existing real-data-rules §14 and registered approvals remain in force |
| Limitations | Readiness is review preflight, not normalized-source reconciliation or artifact QA; unattended drafts, seed --verify, fresh development bootstrap and reproducer still planned |
| Next owner | Engineering: repair seed/fixture shape mapping and verify idempotence, then fresh supervised development and immutable-source reproducer under the existing plan |

A missing 5.1 still blocks authoritative readiness and provisional employee
profiles. Provisional mode follows existing validation requirements for missing
issuance evidence; it never sets approval flags or creates PDFs. Regression cases
cover mode/profile selection, missing territory, duplicate IDs, unverified office
profiles, all four human flags, unchanged input bytes and audited mode-labelled CLI
receipts. Existing publisher, normalized-source and promotion checks remain active.

Acceptance command: `venv/bin/python -m pytest tests/test_finalize_a1.py tests/test_a1_stabilization.py -q`.
The tested export and resulting A1 Git object contain identical source/test blobs.
The old planning filename-token check rejects A1 source filenames in a mixed
code/documentation staging set; keep this A1 code and the planning update as
separate reviewed commits with their configured hooks. No check is disabled or
redefined by this repair. The documentation checkpoint runs the planning validator
with the A1 source already committed. This legacy mixed-batch limitation remains
a scoped tooling follow-up, not a new application or activation gate.

The metadata-only inventory retained 81 inherited entries (12 modified, 69 untracked)
in planning, A1-policy, tooling and research/report scopes. These are classified as
preserve pending scoped content review, not declared stale or approved for staging.
The inventory includes no copied employee content and remains under protected
`runtime/portal/temporary/readiness-roadmap-20260909/`. Existing parent-plan edits
are preserved; only the small readiness correction to PLAN-A1 is included here.
Do not create another editable source tree or archive unknown files to obtain a
clean status. New deliveries continue updating this record; detailed inventories
and hash-bound receipts remain runtime artifacts.

### Tooling repair and bounded J2 intake — 2026-09-09

This delivery completes the reviewed seed/reproducer repairs and adds the first
synthetic completed-batch inbox increment. It preserves the earlier unrelated OCR
benchmark test and historical databases/packages. The original report's completion
claim was corrected by `3e31594`; the implementation below supersedes that repair list.

| Field | Evidence / state |
|---|---|
| Implementation | Exact sanctioned seed settings; explicit private verification roots; read-only SQLite verify; independent role/profile/state expectations and multiset worker/assignment/case reconciliation. Reproducer verifies exact Git blobs and uses an isolated acceptance copy, single-attempt command results and protected hash-bound receipts. J2 uses shared intake/OCR with private organization roots, completed manifests, hash/type checks, local locking, per-item recovery and opaque receipts. |
| Validation | Seed/containment: 31 tests passed; final diagnostic change: one affected test passed. Reproducer: 13 behavioral tests passed. J2: 14 SQLite integration tests passed. Supervised settings: 43 existing checks plus five inbox-configuration checks passed (an inherited setgid bit on newly created inbox directories was corrected). PostgreSQL integration: 44 tests passed in an ephemeral cluster, including J2 and historical migration paths. Planning: 24/24 checks passed. Committed source `6e37d6c`: 91 pytest tests and 9 subtests plus 14 J2 Django tests passed; all 23 archive-applicable planning checks passed and source integrity remained unchanged. |
| Publication | Implementation commit `4797352`, entrypoint repair `d57ad18`, and directory-mode repair `6e37d6c` are local. Accepted source is `6e37d6c`; this documentation checkpoint records its evidence. Earlier outgoing commits remain unpublished pending content review; no history rewrite or force-push is authorized. |
| Deployment | No service or production deployment. Fresh `runtime/portal/supervised-development/` was built from all 13 on-disk Release 1A migrations and passed apply/verify twice: 3 synthetic organizations, 4 workers, 5 assignments, 2 A1 cases. Bootstrap source `d57ad18` has the same seed/models/supervised-settings blobs as accepted `6e37d6c`. Existing historical databases/PDFs are untouched; accounts remain inactive and inbox operator defaults unprovisioned. |
| Activation | Unchanged. The inbox adapter explicitly refuses real-data activation and uses existing actor/membership/MFA capability checks. Configuration creates no operator or human confirmation. |
| Limitations | J2 intake leaves identities unassigned with requires_review; no worker auto-merge, A1 draft generation, BO completion or scheduler is included. Originals remain protected in the inbox pending retention review. Local file locking is not distributed coordination; existing OCR retry/dependency policies still apply. |
| Next owner | Engineering: J2 identity/conflict handling and DB-MIG-1/2/5 revision mapping, then J4 unverified drafts and BO confirmation, preserving DB-MIG-6/7 cutover dependencies and real-data-rules §14. |

Protected evidence: `runtime/portal/temporary/release-reproducer/523088de500044b5a90a13e44ab85e14/receipt.json`
and `runtime/portal/supervised-development/bootstrap-receipt.json`. The first
committed-source run on `d57ad18` exposed inherited setgid on newly created receipt
directories; its failed receipt is retained. `6e37d6c` clears that flag only on new
directories and adds the corresponding synthetic regression; the later run passed.
The synthetic bootstrap's `environment.json` contains a development-only test key,
not production credentials or an activated operator. No service is started by it.

Selected verification commands:

```bash
venv/bin/python -m pytest tests/m2/test_synthetic_containment.py tests/test_release_reproducer.py -q
venv/bin/python scripts/test_document_intake.py
bash scripts/release_reproducer.sh <delivered-source-sha>
```

The PostgreSQL harness owns an ephemeral in-project cluster with Unix sockets and
no network listener; it now includes J2 inbox scenarios alongside existing intake,
historical migration, readiness and J4 service tests. No system database is used.
The release reproducer omits only the index-specific staged check in a plain archive;
mandatory source publication hooks remain effective. Its receipt binds the actual
source commit, invoking runner/interpreter, installed dependencies, environment,
first command exit codes, logs and before/after source integrity. Runtime writes
occur in a separate disposable acceptance copy, not the immutable source export.

The [local automation contract](../../plans/2026-09-08-local-a1-automation.md) specifies
the completed-manifest format and one-time supervisor inbox configuration. After
configuration, the bare management command uses existing authorized actor/org IDs;
explicit CLI overrides still require the same authorization and root segregation.
A completed intake means persisted machine proposals, not confirmed identity or
certificate issuance. No approval states or top-level catalog IDs are changed.

### Consolidation documentation delivery — 2026-09-08

Historical delivery state at `cba3e50`; the 2026-09-09 repair above supersedes its
reported readiness discrepancy.

| Field | Evidence / state |
|---|---|
| Implementation | AGENTS.md shortened to 170 lines; consolidated local plan, 44-field mapping, parent/index/roadmap references, framework and archive guidance; package catalog registers five previously unclassified documentation paths; planning validator permits the three exact reviewed A1 document paths with six regression cases |
| Validation | 24/24 planning checks; 44/44 mapping rows; 133 relative links resolve in staged-source export; 97 focused planning/approval/package tests pass from exported staged source; staged whitespace/content classification passes |
| Publication | The commit containing this checkpoint is the delivery object; exact local/remote SHA and final status are recorded in protected runtime delivery-receipt.json and the operator handoff, not inferred from test results |
| Deployment | Not performed; no settings, database, service or file relocation changes |
| Activation | Unchanged; real-data-rules §14 and existing registered approvals remain authoritative |
| Limitations | Historical databases and unreviewed work retained; generic readiness still requires activity_name while provisional validation permits blank 5.1; future seed --verify, reproducer and coordinator are not implemented |
| Next owner | Engineering: inventory dependencies/selected inputs, then fresh synthetic development setup and the existing J2/J4/DB-MIG tasks |

Only this task's documentation hunks are included; inherited parent-plan edits,
untracked reports and fixtures are excluded. No application tests or PDF generation
are needed to establish this documentation checkpoint. The necessary validator
false-positive repair is the only source-code change: exact document names, not a
broad directory exemption. Protected-path/content checks remain in force.

Acceptance commands: `venv/bin/python scripts/validate_planning.py` and
`venv/bin/python -m pytest tests/test_validate_planning.py tests/test_validate_approvals.py tests/test_validate_change_packages.py -q`.
The exported staged source passed all 97 tests and 24 planning checks; final
Git-object verification matches delivered inputs to that evidence. The mapping's
AST check covers each CSV_FIELDS key once. Relative-link checks use the staged
source export rather than relying on untracked local reports. Existing hooks may
repeat their own configured checks; they are not bypassed.

During verification the staged document filenames triggered the old substring
rule; the narrow fix removed that false positive. One new negative-test specimen
initially used `1a` rather than the prohibited `a1` token; corrected to an actual
rejected sibling filename, then the complete exported suite passed. No protected
input was read. Detailed source hashes, commands and publication state are retained
at `runtime/portal/temporary/consolidation-docs-20260908/delivery-receipt.json`.

## Checkbox alignment repair — 2026-09-08

The original PDF and the working raster background had different box geometry;
3.4 and 4.1.2 outlines were absent. Restored all ten blank outlines at the original
vector coordinates, corrected the corresponding layout, and inset X strokes by
1 point. No employee values or original selection marks were copied.

The previous blank background is retained in protected runtime. The one-time
repair rejects any other input hash; 300-DPI comparisons on all three pages found
zero changed pixels outside the checkbox repair regions. All three synthetic
pages and the four reported problem crops were visually reviewed. Tests now check
all ten X/Y/page/size values, actual background outlines, full rendered stroke
containment and hashes binding template/layout/renderer/reference. They need no
ignored employee/reference PDF. Receipt: `config/a1_checkbox_fix_receipt.json`.

Employee PDFs were not regenerated. Existing packages remain unchanged; their
canonical source/approval/visual gates still apply. The synthetic review artifact
is `runtime/portal/temporary/checkbox-alignment-review/synthetic-checkboxes.pdf`.
The background and coordinates must be changed and accepted together from now on.

## Approval validation and fixture isolation — 2026-09-08

The shared approval validator now preserves CLI catalog-state/date checks, rejects
cycles and unmet dependency states, and makes each gate decision from one validated
register snapshot. Dirty review scope, mismatched commit/hash and an incorrect Git
root fail closed when requested. Malformed JSON shapes fail cleanly. Technical
validation may pass while human approval remains proposed; that never opens a gate.
Approval records, catalog IDs and human/activation decisions were not changed.

Publication provenance: a concurrent session included the five staged governance
files in its A1 commit `95ade12` and published it. This was not the intended scope
split. Its governance-only exported acceptance passed 74 tests; no A1 geometry,
artifact generation or visual acceptance is established by this report.
Follow-up `1cdec5f` isolates Git commands from caller/hook environment overrides.

The original planning fixture helper copied runtime files into its temporary test
root and exhausted /tmp. Only the copies created by that failed run were removed.
The helper now uses committed text fixtures and excludes protected paths, unreviewed
fixture data, environment files, binaries and symlinks. Gitless exported snapshots
prune protected directories before reading. Regression tests assert these boundaries.
An isolated-worktree hook exposed inherited Git variables redirecting fixture
commands; the disposable checkout was rebuilt and the accidentally changed shared
`core.bare` flag restored to false. The delivery-tool fixture suite required the
same isolation; its accidental local test identity was restored to the original
repository identity. Main-worktree status was checked afterward.

Acceptance command: `venv/bin/python -m pytest tests/test_validate_approvals.py tests/test_validate_planning.py -q`.
Both the isolated hook run and exported `1cdec5f` snapshot passed **75 tests**.
Final planning/asset checks are verified before Git publication. Detailed synthetic logs
remain under `runtime/portal/temporary/approval-*.log` (not tracked).

Next owner: primary engineering, to review the remaining verifier/browser/seed
packages and unrelated planning work. Use isolated checkouts while another session
is active; never share staging. No service deployment or real-data activation is
included. The current A1 binary remains outside this governance acceptance scope.

## Shared intake delivery — 2026-09-08

Implementation: `9ab6f46` publishes the shared offline core; `a52363a` publishes
synthetic runtime dependencies; `5a96935` publishes the portal adapter and required
J4 integration. Catalog commits `10b6099` and `5612cd7` define their reviewed
boundaries. No intended core/runtime/portal paths remain dirty after these commits.
The parent PLAN-WORKERS checkpoint is staged separately from its inherited edits.

Upload and supersession now use the same validation, protected storage and OCR
pipeline. Supersession preserves old bytes/receipts, serializes version creation,
reuses identical retries and cleans up a new source on transaction failure. Late
OCR cannot overwrite the latest document state; obsolete proposals/associations
cannot be accepted. Output-storage failure leaves a retryable failed run.
J4 preparation retains an empty PDF hash until actual canonical artifact attachment.

Acceptance from exported Git objects (installed project venv; synthetic data only):

| Object | Command | Result |
|---|---|---|
| `9ab6f46` | `unshare -Urn venv/bin/python -m pytest tests/test_document_core -q` | 87 passed; networking disabled |
| `a52363a` | `env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m pytest tests/test_readiness_checks.py tests/test_runtime_hardening.py tests/test_settings_supervised_synthetic.py -q` | 82 passed |
| `5a96935` | `env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python manage.py test tests.document_web.test_intake tests.m2.test_views tests.m2.test_release1a_vertical tests.m2.test_review_fixes tests.m2.test_j4_delivery tests.test_j4_minimum tests.m2.test_readiness --noinput -v 1` | 101 run; 98 passed, 3 PostgreSQL-only skips |
| `5a96935` | `venv/bin/python scripts/test_document_intake.py` | 30 passed on disposable PostgreSQL 18, including all three skipped cases |
| `5a96935` | `env DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m pytest tests/test_j4_artifacts.py tests/test_runtime_contract.py tests/test_release1a_migration_chain.py -q` | 46 passed; five expected database-override warnings |

The PostgreSQL run covers concurrent replacement, late OCR completion, bounded
query cancellation and historical MigrationExecutor transitions. All disposable
clusters are stopped and removed by their harness. Artifact tests use the committed
template, not the unrelated modified template in the working tree. They establish
synthetic integrity/behavior, not all-page visual acceptance or certificate issuance.
The missing-database side-effect test now allows cold subprocess startup separately
from the strict deadline/cancellation tests; no production timeout was increased.

The benchmark-specific contract test stays with the unpublished benchmark script;
it was moved to `tests/test_ocr_benchmark_contract.py`, not discarded or promoted.
The planning checkpoint publishes the reviewed child plan and architecture contract.
References to other unpublished local reports are labelled explicitly. Existing
34 catalog IDs and approval states are preserved. Working-tree planning passed
24/24; final documentation-object checks and remote SHA are verified before the
handoff claims publication. No full-repository CI or deployment acceptance is claimed.

Synthetic logs: `runtime/portal/temporary/intake-delivery-20260908/`; exported
objects: `runtime/s-<commit>/`. Publication targets only the existing GitHub feature
branch. Next owner: primary engineering, to review remaining governance, planning,
benchmark/research and fixture scopes, then reconcile draft PR #1 against CI.
Unrelated template changes and employee artifacts remain untouched. Deployment,
observed review, real-data activation and all existing human gates remain pending.

## Bounded dependency repair — 2026-09-08

Implementation commits `c322e8a` and `153cf05`, with dependency follow-up
`ab43d27`, restore migration stages 0008–0011, preserve the committed 0012
dependency, add 0013 for the confirmation reverse relation, and publish the
canonical A1 audit/path modules. The institution inventory test now runs without
Git metadata and rejects an empty inventory. Louny's unresolved code keeps its
profile at NEEDS_VERIFICATION. No institution or certificate evidence was approved.

Acceptance from an exported `ab43d27` snapshot without `.git`: **57 passed** with
`venv/bin/python -m pytest tests/test_finalize_a1.py tests/test_a1_stabilization.py tests/test_release1a_migration_chain.py tests/test_validate_change_packages.py -q`
(the existing project venv interpreter was invoked by absolute path). The first
A1 snapshot failed because its template-repair receipt dependency was absent;
`ab43d27` includes that metadata-only historical receipt. This is not fresh
template visual acceptance. The snapshot test exercises historical app states
through MigrationExecutor, preserves document/J4 data, and checks model parity.

The existing two historical intake/J4 tests also passed on a disposable SQLite
test database in the working tree. Planning validation passed 24/24 there;
neither result establishes acceptance of the remaining unpublished portal modules.
Detailed synthetic logs and exported snapshots are in protected project runtime
storage under `runtime/portal/temporary/delivery-20260908/`.

Git publication is tracked separately from implementation and acceptance; the
remote SHA must be verified after pushing these bounded commits. No persistent
database migration, deployment, employee generation, promotion or activation was
performed. Databases created from the withdrawn local squash require their own
history review before use; they were not migrated by this repair.

Next owner: primary engineering, for the remaining shared document/runtime/J4
source packages and supersession integration. Preserve unrelated work. The initial
inventory contained 262 dirty files (27 modified, 235 untracked), including 134
untracked research files; that inventory is not a staging approval. Research,
unreviewed fixtures, template changes and unrelated planning work remain outside
this bounded delivery. Parent plan statuses and activation gates are unchanged.

## Current delivery

The pre-commit gate validates exact staged bytes and the staged package catalog.
Missing/malformed catalogs, unknown or quarantined paths, protected paths, credential
indicators, unsupported index entries and oversized files fail closed. Deleted
ordinary source files are accepted without reading absent blobs. Unrelated unstaged
work is excluded. Catalog checks run with argument arrays, no shell eval, and a
five-minute timeout. Their execution still uses the working tree, so match evidence
to the delivered inputs under the current operating policy above. Export checks are
required when that match is unproven, not a duplicate suite for every small edit.
This is not a full PII detector.

Run `bash scripts/install-git-hooks.sh` after cloning. The installer preserves an
existing hook before replacement and refuses an independently configured hooksPath.
The hook requires the repository venv; it never bypasses validation on failure.

Existing GitHub Actions use explicit Bash (pipefail), direct pytest output, mandatory
dependency installation and lint, read-only token permissions, job timeouts and
cancellation of superseded runs. The slow-suite push condition matches master.
A tracked-blob signature scanner emits paths only, never matching secret values.
No new CI provider or runner is activated. Existing dependency/collection/lint
failures are now visible and must be fixed in their responsible delivery packages.

Environment variants, SQLite sidecars and all runtime outputs are ignored;
`.env.example` remains eligible for explicit synthetic review. No runtime contents
were moved, read or deleted. The reviewed template binary attributes are published.
Ignore rules do not protect already tracked files or historical Git objects.

## Acceptance and next steps

Focused acceptance: **16 tests passed**, including an exported commit snapshot
of implementation commit `5d41658`. Planning checks: **24/24** in the working tree.
The first full exported planning snapshot exposed missing local evidence references.
ADR comparison links and the benchmark receipt reference now explicitly identify
unpublished local evidence; no artifact or decision was promoted.
Broad CI acceptance remains pending and is not inferred from these results.

Run `venv/bin/python -m pytest tests/test_validate_change_packages.py -q`,
`bash -n scripts/pre-commit scripts/install-git-hooks.sh`, staged validation and
`git diff --cached --check`. Tests use synthetic temporary repositories and cover
staged/worktree disagreement, catalog disagreement, deletions, symlinks, quarantine,
malformed input, failed commands, environment variants and credential diagnostics.

Keep the 34 planning IDs and activation gates unchanged. Next: publish reviewed
A1/core/portal dependencies in coherent commits, including the collector module
missing from the current committed test suite. Reconcile draft PR #1 after clean
snapshot and remote CI acceptance. Historical branches remain untouched; never use
bulk push. Master protections/account capabilities require a separate decision.
