# Plan PLAN-WORKERS-MIGRATE-TO-DB — Worker data: from JSON/CSV to database

**Status**: planned
**Milestone**: M2–M5 (accepted cutover after ENG-001 → REV-002)

## Current scope and next work — 2026-09-14

Core-v1 database acceptance belongs to JAN-02/JAN-04 in [delivery reliability and Jan core v1](2026-09-14-delivery-reliability-and-jan-v1.md):
worker/document/assignment persistence, real PostgreSQL migration/concurrency checks
and exact restart survival. Optional fields may remain null; complete A1 mappings
or PDF equivalence do not gate saving workers or shipping the core portal.

DB-MIG-1 through DB-MIG-7 remain traceable below. Their A1 export/render equivalence
and legacy-master freeze are separate optional-A1/cutover work, not prerequisites
for new synthetic core records. Accepted legacy cutover and real-data migration
retain their explicit scope and authorization. Do not infer current target state
from dated migration ranges or old reports. JAN-03 reconciles machine acceptance.

## Retained migration contracts and dated evidence

Historical implementation checkpoints below are not a current instruction to
repeat seed/bootstrap/PDF work. The child reliability plan owns current priorities.



2026-09-09 draft checkpoint: synthetic inbox/`a1_prepare_draft` now calls the
canonical unverified-draft publisher. Migration 0016 reserves an immutable number,
source/profile/dependencies and package UUID; retries recover the same package.
Unknown certificate dates remain blank; every page has an UNVERIFIED DRAFT notice.
Human/visual confirmation and official issuance remain separate. Migration 0017 adds
immutable generations for changed dependencies, preserving the number and prior packages.
BO generation access and generation-bound visual confirmation are implemented. BO field confirmation is revision-checked. BO identity association/conflict resolution now submits source- and worker-revision-bound choices to the canonical identity service. Explicit synthetic legacy-key reconciliation is implemented. Selected-cohort CSV/identity input bundles are implemented. Profile-bound protected publication and the synthetic export CLI are implemented. Case-level BO publication and manifest-pinned ZIP download are implemented. Selected-cohort BO publication is implemented. Complete-input synthetic operator-workflow checks pass; source-linked structured address entry in BO is implemented. BO assignment/institution fact entry is implemented. Cold-start readiness checks now cover both BO entry paths and blocked retry without duplicates. Source-bound BO completion of missing identity facts is implemented. Next: validate the sparse-input journey through canonical draft generation and artifact review. See the
[local automation contract](2026-09-08-local-a1-automation.md) and delivery record.
Existing environments remain unchanged; selected supervised release needs 0014–0019.

## Consolidated contract — 2026-09-08

The [local automation plan](2026-09-08-local-a1-automation.md) is the bounded child
contract for J2/J4 and DB-MIG-1 through DB-MIG-7. Its
[44-field mapping](../docs/architecture/release-1a-field-mapping.md) supersedes the
older assumption that every CSV field needs a Worker/A1Case column. This is a
planning checkpoint, not a completed migration or portal activation.

Respect [ADR-001](../docs/decisions/ADR-001-jan-portal-architecture.md) and
[ADR-002](../docs/decisions/ADR-002-release-1a-data-and-transactions.md).
Preserve catalog IDs and registered approvals. No extra ADR, repeated operator
permission or new activation gate is required for the authorized synthetic preparation.

2026-10-20 documentation checkpoint: the
[official A1 field → source mapping](../docs/architecture/a1-field-source-mapping.md)
adds the official-form view alongside the 44-field CSV mapping, restructured
into six topics with one owner each (certificate, person, employer/role/
situation, activity, institution, provenance). It states which official
positions 1.1–6.11 are owned by whom, which are derived, and which are
conditional on the legal situation (R1–R10), and records the
employer-as-organization decision: the employer is a legal entity in its own
`LegalEntity` master table, never the tenant `Organization`. The
[gap analysis](../docs/architecture/a1-gap-analysis.md) (G1–G15),
[automation scenarios](../docs/architecture/a1-automation-scenarios.md) and the
architecture solution
`docs/architecture/solutions/a1-topic-data-architecture-solution.md` state the
same arrangement as an ordered, low-risk landing sequence. The
[LangGraph guide](../docs/architecture/langgraph-integration.md) was aligned
with the measured layer: three orchestrator defects were found by running it
and fixed (a shadowed-module `UnboundLocalError`, a state channel name that
LangGraph 1.x reserves, and a dry run that wrote into the protected output
tree), and the agent-ops experiment suite now passes 37/37 after the venv was
aligned with the already-pinned dependency file.

2026-10-20 alignment checkpoint. The competing draft
`docs/architecture/a1-form-architecture.md` was removed and its content
consolidated into the registered mapping, so one document owns the field
logic. Corrections carried over: `status_posted_self_employed` is at
`scripts/a1_core.py:450`; the layout key is `status_posted_self_employed`;
the seven A1 suites hold 124 tests; and status 3.3 needs **12** code sites,
not 5 or 9 — `mark_provisional`'s Section 5.1 blanking, the per-variant
`status_profiles` and the preview profile choices fail *silently* rather than
raising, so an incomplete activation list yields a wrong certificate instead
of an error. The full path with the failure mode of each site is in the
mapping §15. `scripts/a1_completion_preview.py` offered only two of the three
supported statuses in the undecided worksheet; it now offers all three, so an
OSVČ case is no longer steered away from `self_employed_multi_state`.

Four latent defects were fixed while validating: the J4 confirmation receipt
recorded an empty `build_id` because `settings` was undefined in
`portal/release1a/views.py` and the `NameError` was swallowed, so the
artifact-approval evidence never bound to a build; an operator password-reset
script referenced an undefined `temporary_password`; a type annotation
referenced an unimported `Any`; and two review loops unpacked `_`, shadowing
the module's gettext alias, so a `gettext` call inside those loops would have
raised. A 63-second browser diagnostic that had no assertions — and could
therefore never fail — is now opt-in behind `A1_BROWSER_DEBUG=1` and no
longer runs in directory sweeps. `portal/release1a/views.py` now passes the
repository's own `ruff` default rules with no findings, against 15 at HEAD.

Documentation and small repairs only: no schema, migration, seed, record
import, acceptance state or change to the CSV contract, validation gates,
provisional notice or issuance workflow. The employer and institution stores
remain as they are today (structured `Assignment.a1_facts_json` and
provenance-carrying institution profile files); no normalisation was
performed.

A repo-wide formatter pass reformatted 372 files in the working tree. It is
not part of this increment: 238 of the 282 changed Python files are exactly
`ruff format` plus `ruff --fix` output on HEAD — what the repository's own
`.pre-commit-config.yaml` mandates on commit — and only 44 carry behavioural
changes. It belongs to its own delivery unit with its own scoped checks, and
must not be bundled with A1 work.

2026-10-20 commit-gate checkpoint. The three pre-commit failures reported
after the CLI-agent drift review were verified rather than accepted as
pre-existing. The secret-scanning gate could not run at all: the hook has
configured `--baseline .secrets.baseline` since it was added, but that file has
never existed in the repository history. A baseline over exactly the 823
tracked files was generated with the hook's own pinned detector, after every
finding was reviewed and found benign (hashes, synthetic test values, a
labelled insecure local default, a docstring example). `ruff.toml` now records
the two deliberate patterns the default rule set flags — E402 for the Django
`django.setup()` bootstrap and the `sys.path` scripts, F403/F405 for the
isolated settings modules — and 40 real findings were fixed across 20 files.
CI now pins the same ruff version as the hook, because an unpinned CI ruff and
a pinned hook ruff could disagree about what passes. The root-owned
`public-site/` directory is excluded from the two file-fixing hooks, which
open files read-write even when the content is correct. All hooks now pass.

One defect surfaced during that work and is recorded rather than fixed:
`scripts/generate_a1_incremental.py` loads the cohort passed to `--cohort` and
never uses it, so the incremental generator does not gate its output against
the authoritative cohort the way `generate_provisional_a1.build_provisional_rows`
does. Correcting it is a behaviour change to an inherited generator and needs
its own test.

The `planning_cockpit` check remains red, for a reason that predates this
increment and that no working-tree edit can fix: the test builds its fixture
from the **committed** tree, and the committed `plans/INDEX.md`,
`plans/PLAN-INFRA.md` and `roadmap.md` link to
`plans/2026-09-18-backup-and-project-separation.md`, which is untracked
working-tree material. A sweep of the committed tree found 29 relative-link
targets absent from it. Ten of those exist on disk and are repaired by
committing them — including this increment's own
[a1-field-source-mapping.md](../docs/architecture/a1-field-source-mapping.md),
[a1-gap-analysis.md](../docs/architecture/a1-gap-analysis.md) and
[a1-automation-scenarios.md](../docs/architecture/a1-automation-scenarios.md).
The rest are permanently broken paths whose link text omits the `docs/`
prefix, plus one deliberate negative-test fixture. Commit scope is Jan's
decision: the A1 increment, the formatter reformat, and the untracked files
the committed tree already references are three separable units.

2026-09-09 implementation checkpoint: seed/reproducer repairs and bounded J2
synthetic intake have behavioral coverage. Fixture role mapping, duplicate/case
reconciliation and exact settings selection are implemented; evidence belongs in
the delivery record. J2 now persists evaluated evidence and unconfirmed identifier
claims, creates eligible drafts and exposes revision-checked explicit resolution.
Migrations 0014/0015 are tested on disposable databases; existing environments are preserved.
Synthetic input snapshots and all 44 canonical CSV columns are exported by
`portal/release1a/a1_exports.py`, with versioned assignment facts and provenance.
No DB-MIG cutover is accepted. Generation-bound visual confirmation is implemented. BO field confirmation is revision-checked. BO identity association/conflict resolution is revision-checked. Explicit synthetic legacy-key reconciliation is implemented. Selected-cohort input bundles are implemented. Profile-bound publication/CLI is implemented. Case-level BO publication/download is implemented. Selected-cohort BO publication is implemented; complete-input workflow checks pass; source-linked structured address entry in BO is implemented; BO assignment/institution fact entry is implemented; cold-start operator readiness checks are next; selected supervised
migration remains required before runtime use. Existing cutover dependencies remain unchanged.

## Purpose and current ownership

After accepted cutover, organization-scoped Django services own worker identity,
assignment, institution, A1 input and confirmation revisions. Both dashboard and
local coordinator use those services; A1 rendering uses the shared Python core.
CSV/JSON are revision-bound compatibility exports, not editable masters.

Before cutover, preserve and reconcile `a1/review.csv`, `a1/cohort.json`, normalized
identity sources and explicitly selected scoped run snapshots. Never choose a
winner by modification time, copy facts from generated PDFs, or freeze sources
before reconciliation. Issued identifiers and confirmed facts retain their evidence.

Worker has names, birth date and broad activity profile today; accepted additional
identity fields fit WorkerIdentityRevision. FieldProposal/FieldDecision already
hold review evidence. There is no Approval model or dedicated A1Case.document_id
or issue_date column. Case facts fit versioned snapshots with structured provenance
and input decisions; visual confirmation is separate. The mapping proposes only
`Worker.legacy_employee_id` and `Assignment.a1_facts_json` as additional columns,
with the required constraints and revision/service contracts. Assignment facts now
have migration 0015 and a synthetic update/export service; the legacy key remains planned.

## Implementation milestones

Preserve existing task IDs. Acceptance descriptions below define future scoped
checks; test modules and commands are added/updated with implementation, not assumed
available from their mention here. Use one shared export adapter in
`portal/release1a/a1_exports.py`, as specified by the mapping.

| ID | Contract | Required acceptance |
|---|---|---|
| DB-MIG-1 | Reconcile identity/legacy bindings into Worker projections and immutable identity revisions; preserve pending proposals | All identity fields mapped; tenant uniqueness; historical MigrationExecutor transition; pending OCR never overwrites accepted fields |
| DB-MIG-2 | Store versioned assignment facts, institution/profile payload and case certificate inputs with structured provenance | Explicit profile/assignment selection; source and input decision binding; generated IDs/dates remain provisional; visual and input acceptance distinct |
| DB-MIG-3 | Adapt a selected database snapshot to the existing core form contract; keep finalize_a1.row_to_form Django-independent | Same normalized core input as the pinned compatibility export; one export service; no live legacy master reads on the cutover path |
| DB-MIG-4 | Dashboard/local coordinator use shared services and the existing canonical renderer/J4 artifact publisher | Actual PDF, snapshot, previews and receipt; stable retry ID; stale dependencies rejected; all-page QA |
| DB-MIG-5 | Resumable reconciliation/import of explicitly selected CSV/cohort/identity snapshots with source hashes | Dry-run reports conflicts without changes; approved synthetic apply is transactional/idempotent; no duplicate workers or invented confirmations |
| DB-MIG-6 | Freeze legacy master editing only after accepted reconciliation; maintain protected history and derived compatibility exports | Guard cutover production adapters against live legacy-master reads; historical import and explicit export adapters remain allowed; rollback references preserved |
| DB-MIG-7 | Demonstrate dashboard/local/core round-trip equivalence on the same synthetic revision | Compare every mapped value/provenance and renderer input; compare PDF bytes with pinned template, renderer, dependencies and deterministic metadata; explain any nondeterminism |

## Environment and delivery order

Follow the child plan's inventory, fresh development database, seed reconciliation
and release reproduction prerequisites before the coordinator/cutover work.
Use `runtime/portal/supervised-development/` with `portal.settings_supervised_synthetic`;
PostgreSQL supplies migration/concurrency acceptance, SQLite isolated synthetic tests.
The existing root and synthetic-review SQLite databases are historical inputs to
inventory, not a database template. Rebuild fresh from the on-disk migration graph;
never fabricate migration records or propagate inconsistent history with `--fake`.

Extend the existing seed deliberately for that synthetic environment and planned
`--verify` fixture reconciliation. Implement the planned
`scripts/release_reproducer.sh <sha>` for immutable `runtime/s-<full-commit-sha>/`
exports and protected receipts. Neither command is introduced by this documentation.

One editable source tree remains. Do not move entire PDF packages or duplicate
runtime credentials. Classified private retained material uses
`runtime/portal/temporary/retained/<uuid>/`, with hash/location manifest and retention
review; `.archive/` is non-sensitive. Existing protected data was never Git material,
so this plan does not require deleting an archive from Git or rewriting history.

## Dependencies, acceptance and next owner

- PLAN-INFRA owns runtime provisioning and infrastructure evidence; routine synthetic
  implementation remains authorized under existing active plans.
- PLAN-WORKERS owns worker/BO workflow acceptance; ENG-001 and observed Release 1A
  acceptance remain cutover dependencies. No registered approval state changes here.
- PLAN-LEGAL supplies purpose/retention interpretation; real-data portal migration
  and activation follow [real-data-rules §12–14](../docs/security/real-data-rules.md#12-mandatory-recovery-before-real-data-activation)
  and [PLAN-REAL-DATA](PLAN-REAL-DATA.md). Production prerequisites do not block
  synthetic preparation; existing authorized operator-only A1 work stays distinct.

Run affected checks once against matching source/dependencies/configuration, under
[AGENTS.md](../AGENTS.md). Update [one delivery record](../docs/operations/git-delivery.md)
with implementation, validation, publication, deployment and activation separately.
Documentation/field coverage alone cannot establish runtime acceptance.

Next owner: engineering for the inventory and fresh synthetic development setup,
then the DB-MIG tasks above. Jan supplies missing business facts and confirms exact
revisions in BO. The [framework guide](../docs/architecture/A1_FRAMEWORKS.md) describes
the current file-based/case-snapshot paths without claiming cutover already happened.
