# Feedback to planning agent — consolidation plan

**Reviewed proposal:** "Consolidate A1, OCR and back-office sources and
environments" (received 2026-09-08, post-dates
`2026-09-08-local-a1-automation.md`).

**Cross-references:**
- `plans/2026-09-08-local-a1-automation.md` (the proposed implementation contract)
- `docs/research/2026-09-08-local-a1-automation-review.md` (the prior review)
- `AGENTS.md`, `plans/INDEX.md`, `roadmap.md`

This memo is a planning-agent-facing response. It classifies every
factual claim in the proposal, then itemises strengths, gaps, and
concrete corrections. No commit, no push, no DB mutation is performed
here; this is a written review only.

---

## 0. Factual verification of the proposal's claims

I verified three specific factual claims the proposal makes about the
current state:

### 0.1 "synthetic-review database stops at migration 0009" — **CONFIRMED**

The DB at `runtime/portal/synthetic-review/db.sqlite3` has 42 rows in
`django_migrations`; the latest `release1a` migration is
`0009_document_region_association`. Migrations `0010…0013` are on disk
but not applied to this DB. See prior review §13.1 for the per-column
matrix. **Correct.**

### 0.2 "root database contains an absent squashed migration name" — **CONFIRMED**

The root `db.sqlite3` `django_migrations` row 44 records:

```
release1a | 0008_squashed_document_intake_and_j4 | 2026-09-07 19:52:21
```

The file `portal/release1a/migrations/0008_squashed_document_intake_and_j4.py`
**does not exist on disk**. The on-disk migration is
`0008_shared_document_intake.py`. The squashed name was recorded by a
different seeded DB (likely the temporary admin / server `db.sqlite3`)
and never committed; subsequent migrations 0009-0013 reference
`0008_shared_document_intake` as their dependency, so the squashed
record cannot be applied to the current code tree without breaking the
migration graph. **The proposal is right to flag this as a known-broken
state.**

### 0.3 "duplicate migration record" — **CONFIRMED**

`django_migrations` rows 28 and 29 both record
`release1a | 0002_release1a_review_and_acceptance` with different
`applied` timestamps:

```
id=28 release1a 0002_release1a_review_and_acceptance 2026-09-02 23:30:47.882439
id=29 release1a 0002_release1a_review_and_acceptance 2026-09-02 23:30:48.617508
```

This breaks the
`(app, name)`-uniqueness assumption that `django_migrations` is
designed around; `manage.py migrate --plan` may behave unpredictably.
**The proposal is right to flag this.**

### 0.4 Other state observed (not claimed by the proposal but worth recording)

- The `id=30` row is missing from `django_migrations` (gap between 29
  and 31). This is consistent with a `DELETE FROM django_migrations`
  followed by an INSERT (auto-increment does not recycle). Together
  with §0.3 it suggests someone manually edited the migration table on
  the root DB.
- Root DB applies migrations up to `0012_a1case_confirmation_evidence`
  (the latest *un-squashed* one), then stops — `0013_alter_a1case_visual_confirmed_by`
  is not applied. Synthetic-review DB applies the un-squashed 0008
  and 0009. The two DBs diverge on which migration 0008 represents;
  this is a known-broken state, not a discrepancy to paper over.
- `releases/` does not exist yet. The proposal's `runtime/releases/<commit-sha>/`
  layout is a forward contract.

These observations strengthen, not weaken, the proposal's premise: the
local state is not consistent and must be rebuilt, not migrated forward.

---

## 1. Item-by-item response

### "Summary"

**Verdict: agree, with one caveat.**

> "Do not copy the entire workspace into another 'final' folder."

Correct — this would duplicate code and defeat the goal of one
editable source tree. The earlier "output/final" anti-pattern (the
Plan-A1 lane historically considered a `output/final/` destination for
approved PDFs) is the same anti-pattern; the proposal's rejection of
"final folder" duplication is consistent with the Plan-A1 hard rule
"Provisional outputs are never final aliases"
(`plans/PLAN-A1.md:174`).

> "Consolidate A1/OCR/BO first; inventory unrelated work without
> relocating it."

Agree. The proposal correctly distinguishes "review and inventory" from
"relocate". Relocation is a separate, reversible operation
(`reversible relocation manifest`, §4.6).

**Caveat.** "The first delivery is consolidation and a verified
directory contract." The proposal should state explicitly that the
"verified directory contract" includes a fail-closed root-storage
check: `DocumentStorageStorage.path` (`portal/release1a/document_storage.py:13-16`)
rejects any key that does not match its regex, so the contract is
enforced by the storage layer, not by convention. The proposal should
name that the regex is part of the contract.

### "1. Reconcile plans with evidence"

**Verdict: agree, with two corrections.**

> "Replace contradictory current-state claims with dated evidence.
> Separate implemented, tested, published, deployed and activated;
> none implies the next."

Agree. The `roadmap.md` already uses this vocabulary (`accepted`,
`synthetic-accepted`, `partial`, `gated`, `published`, `activated`).
The proposal should cite which roadmap section defines each term, so
the vocabulary does not drift.

> "Correct the claim that every CSV field needs a new direct column:
> some evidence already belongs in proposals and immutable revisions."

**This is a fair correction to my prior review.** I wrote that 39 of 44
CSV columns have no model home. A more precise reading:

| CSV column(s) | Natural destination | Justification |
|---|---|---|
| `activity_source`, `activity_source_status`, `certificate_source`, `certificate_source_status`, `signatory_source`, `signatory_source_status` | `FieldProposal.source_*` (new fields) or `FieldDecision.reason` (existing) | These are *proposals with provenance*, not final A1 fields. The existing `FieldProposal.validation_findings` JSON already holds proposal-level findings (`portal/release1a/models.py:386`); adding structured source columns is a small migration. |
| `identity_reviewed`, `certificate_reviewed`, `approved_for_pdf` | `A1Case.<flag>` (new) + `FieldDecision.decision` (existing) | BO-confirmation lifecycle, but `FieldDecision.decision="confirmed"` already covers the leaf decision. The row-level flag is a roll-up. |
| `validated_by_user` | `A1Case.visual_confirmed_by` (migration 0012, exists on disk, not on synthetic DB) | Already on disk as `visual_confirmed_by`. Just re-bind the readiness gate's CSV check to the DB column. |
| `pdf_created` | `A1Case.external_status` (existing enum) | The CSV boolean maps to `external_status in {SUBMITTED, ISSUED}`. |
| `comments` | `A1Case.notes` (migration 0010, exists on disk, not on synthetic DB) | Already on disk. |

So a tighter reading is: **~10-15 of the 39 columns need direct new
columns; the other ~25 belong in existing or near-existing structures
(`FieldProposal`, `FieldDecision`, `WorkerIdentityRevision`,
`Release1aAcceptance`, the J4 audit columns).** The proposal is right
to flag this; the prior review overstated the gap.

**Correction 1.** The proposal should commit to one of the two paths per
CSV column in the field-mapping contract (§2 below) before
implementation. My §13.4 enumeration grouped all 39 together; the
proposal should split them.

> "Distinguish actual storage-key incompatibilities from harmless
> differences between archive and run directories."

Agree. The prior review §3 listed five "conflicts"; one
(`a1/runs/<run_uuid>/` vs `a1/_archive/`) is a naming collision (real
conflict), one (`scans/inbox/`) is a missing policy entry (real gap),
three are regex-vs-plan-path mismatches (storage-layer
incompatibilities). The proposal is right to make this distinction
explicit.

> "Treat legal conclusions in the research report as review inputs,
> not automatic new operational rules."

Agree. The GDPR/Czech-DPA section in the prior review listed
authoritative citations but did not propose operational rules. The
proposal should not implement Art. 30 records-of-processing, Art. 33
breach runbook, MRZ-drop test, or similar items without a separate ADR
and operator approval. Concretely: the prior review §6 should be
classified as "research inputs", not "implementation backlog".

> "Preserve the 34 catalog entries."

Agree. The catalog lives at `planning/catalog.json` (34 entries per
`roadmap.md:58`); the proposal should name the file path.

**Correction 2.** The proposal does not currently list the parent plan
IDs by file path. A one-line reference (`plans/PLAN-INFRA.md`,
`plans/PLAN-A1.md`, etc.) prevents drift when the file paths change.

### "2. Declare one owner for each kind of information"

**Verdict: agree, with one missing row and two corrections.**

The owner table is the proposal's strongest contribution: it makes the
"single source of truth" claim falsifiable. Three notes:

- **Missing row.** The table does not name an owner for **ops-side
  configuration** (release manifest, settings, environment variables,
  credentials). Today that lives in `portal/settings*.py` (six modules)
  and `.env` (gitignored). The plan should add: `Runtime settings:
  portal/settings*.py + runtime environment; one supervised manifest per
  environment; no shared secret files`.

- **Correction A.** "JSON/CSV … generated compatibility exports after
  cutover" is correct but underspecified. After DB-MIG-7, the renderer
  reads from the DB (`plans/PLAN-WORKERS-MIGRATE-TO-DB.md:14-15`). The
  CSV/JSON become *derived compatibility exports*, not authoritative.
  The proposal should commit to a single re-export script (today
  `scripts/normalize_datasets.py` exists, but no clear export-side
  consumer). Without that, "compatibility exports" becomes another
  orphan generator.

- **Correction B.** "Original documents and OCR evidence | Existing
  protected storage services and database references" — agree, but
  the proposal should also state that the storage layer's regex is
  the contract (`portal/release1a/document_storage.py:13-16`). The
  "database references" wording is ambiguous: today the storage layer
  holds the bytes and the DB holds the *opaque key*, not the bytes
  themselves. The proposal should make that distinction explicit
  (`Document.opaque_key`, `Document.sha256` are DB columns;
  `ProtectedDocumentStorage` holds the bytes).

The "field-mapping contract covering every canonical CSV column"
requirement is the right idea. The proposal should require the
contract to live at `docs/architecture/release-1a-field-mapping.md`
(a new file, ADR-numbered), with one row per CSV_FIELDS entry:
destination model/revision, transformation, provenance, nullability,
export mapping. The contract should be reviewed before DB-MIG-1
implementation starts.

### "3. Directory and release structure"

**Verdict: agree, with corrections.**

The directory tree is sensible. Six corrections:

- **`runtime/releases/<commit-sha>/`**: this is forward contract. Today
  the closest equivalent is `runtime/s-<commit>/` (e.g.
  `runtime/s-7e03777/`), which exists from prior delivery exports
  (`docs/operations/git-delivery.md:103`). The proposal should either
  reuse `runtime/s-<commit>/` (preferred — already named, already
  excluded from release manifests via `.gitignore`) or rename with a
  clear migration note.

- **`runtime/portal/supervised-development/`**: the current name in the
  proposal is ambiguous. Today the supervised settings are
  `portal/settings_supervised_synthetic.py` (settings module) and
  `runtime/portal/synthetic-review/` (data root). The proposal should
  pick one of: (a) `runtime/portal/supervised/`, (b) keep
  `runtime/portal/synthetic-review/` and call it the
  "supervised-development" data root, (c) introduce a new sibling
  directory and document the rename.

- **`runtime/portal/temporary/retained/<uuid>/`**: today the analogous
  path is `runtime/portal/temporary/` and items there are explicitly
  scoped per task (e.g. `runtime/portal/temporary/intake-delivery-20260908/`).
  The `retained/<uuid>/` rename is a behaviour change. The proposal
  should classify this as a forward contract for classified private
  material *only*, not a sweeping rename of existing temporary items.

- **`.archive/`**: the existing tracked archive directory is
  `.archive/` (used for plans), and `.history-remediation/` for git
  remediation. The proposal should not introduce a third archive
  root. `.archive/` should be reused for non-sensitive historical
  material; `.history-remediation/` remains for git history cleanup.

- **"PostgreSQL remains system-managed; 'production folder' does not
  mean moving its database files"** — agree, and this is a hard
  constraint from `docs/security/real-data-rules.md:113-115`. The
  proposal should explicitly cite that section.

- **"Separate code-root and data-root configuration before running
  release snapshots. No implicit fallback to root `db.sqlite3`,
  development storage or another environment"** — agree. Today the
  root `db.sqlite3` is the *implicit* default for `manage.py`. The
  proposal should require that `DJANGO_SETTINGS_MODULE` be set
  explicitly in every release script (not left to
  `manage.py`'s default behaviour). This is a one-line code change in
  every entry-point script.

The "Preserve the implemented storage formats" subsection is correct
but should add the explicit regex statement:

```
ProtectedDocumentStorage.path(name) accepts:
  (?:documents|generated)/[a-f0-9]{32}(?:/[a-f0-9]{64})?\.(?:source|json|png)
```

A1 artifacts use the J4 staging directory (`_root`,
`_write`, `_pages`, `publish_artifact` in
`portal/release1a/j4_artifacts.py:32-118`) with `fcntl.flock` and
`fsync`. Operator CLI packages use `scripts/a1_paths.py`
(`unique_staging_path`, `publish_package`). All three are implemented;
the proposal should name them.

### "4. Migration and retained material"

**Verdict: agree, with two new items and one correction.**

The five-step migration order is sound. Additions and corrections:

- **Step 1 — Inventory first.** The proposal should name the inventory
  tool. `scripts/inventory_repository.py` exists; it has been used in
  prior audit rounds (`docs/research/2026-09-07-research-audit.md`).
  The proposal should either reuse it or justify a replacement.

- **Step 2 — Publish missing dependencies.** "Never sweep them into a
  release" is correct. The proposal should also commit to one of two
  postures per untracked file: (a) explicit `git add` after review,
  (b) `.gitignore` entry. Today `docs/operations/git-delivery.md`
  records several untracked artefacts that have been left in place.
  The proposal should not leave that posture implicit.

- **Step 3 — Build fresh synthetic PostgreSQL.** Correct, but the
  proposal must reconcile the migration graph first. The root DB has
  the broken `0008_squashed_document_intake_and_j4` record and the
  duplicate `0002_…` record (§0.2, §0.3); the synthetic-review DB
  has un-applied migrations 0010-0013. A fresh build on PostgreSQL
  applies the on-disk migration chain; the broken records become
  irrelevant. The proposal should explicitly say: do not migrate the
  broken databases forward; rebuild from the published graph.

- **Step 4 — Reconcile historical databases.** "Test migration
  transitions separately; do not fake migration records or upgrade
  an unidentified database" — agree, and this matches `AGENTS.md`:
  "Migration transition tests must use Django historical app states
  through MigrationExecutor". The proposal should require every
  migration milestone to ship a `MigrationExecutor`-based test
  (per AGENTS.md).

- **Step 5 — Implement missing schema and coordinator.** "Follow
  existing DB-MIG/J2/J4 tasks" — agree, but the proposal does not
  name which tasks. A one-line pointer to
  `plans/PLAN-WORKERS-MIGRATE-TO-DB.md:65-73` (DB-MIG-1 through -7)
  closes the gap.

- **Step 6 — Cut over production.** Agree, but the proposal should
  state that the activation gate is `real-data-rules.md` §14, not
  invent a new gate. Today §14 has 13 sub-conditions; the proposal
  should reference them.

- **New item: file-system class boundary.** The proposal introduces
  `.archive/` and `runtime/portal/temporary/retained/<uuid>/`. It
  does not state the file mode (0600/0700 vs 0640/0750). Per
  `real-data-rules.md` §5, mode 0644/0664 are not acceptable for
  PII-bearing files. The proposal should require mode 0600/0700 by
  default; any dedicated-group variant must be justified.

- **New item: protection against the plan creating a "final" directory.**
  The "Do not copy the entire workspace" rule (Summary) and the new
  `runtime/releases/<commit-sha>/` are in tension. Releases are
  immutable per-release snapshots; a `/final` is a moving alias. The
  proposal should explicitly state: every release is keyed by commit
  SHA; there is no `/final` symlink, no promotion path through the
  filesystem. Promotion is a database state + receipt, not a path
  rename.

### "5. Acceptance and delivery"

**Verdict: agree, with two corrections.**

The acceptance list is the right shape. Corrections:

- **"A release runs from its exported snapshot without untracked
  dependencies."** This is the load-bearing acceptance criterion. The
  proposal should commit to a single reproducer script
  (`scripts/release_reproducer.sh` or similar) that takes a commit
  SHA, exports the snapshot, runs migrations, applies the seed, runs
  the synthetic acceptance, and writes a hash-bound receipt. Without
  that script the criterion is not measurable.

- **"Synthetic seeding preserves activity profiles, worker states and
  assignment facts."** This is direct feedback on the prior review's
  §13.3 finding (4 workers in DB diverge from `workers.json` on
  `activity_profile` and `state`). The proposal should add an explicit
  reconciliation command (e.g.
  `scripts/verify_synthetic_seed.py --against tests/fixtures/release_1a/workers.json`)
  that runs after seeding and before acceptance.

- **"BO confirmation records actor, time and exact revision."** Agree.
  The proposal should require the revision to be the
  `WorkerIdentityRevision.revision_number` (existing column,
  `portal/release1a/models.py:407-417`), not a new column. Today's
  per-field `FieldDecision` chain already records actor/time/source
  (`portal/release1a/services.py:227-241`); the BO UI is the gap.

- **"A1 output preserves numbering, dates, checkbox alignment, blank
  5.1 and `DE, CZ` in 5.2."** This is a contract from
  `scripts/finalize_a1.py` and `config/a1_provisional.json`. The
  proposal should name the source: `scripts/a1_core.py` (single entry
  point), `config/a1_layout.json` (geometry), `config/a1_provisional.json`
  (5.1/5.2 defaults).

- **"Deliver one current status report, one source/environment
  manifest and one ordered implementation backlog."** Agree, and the
  proposal should name the file paths (the prior pattern is
  `docs/operations/git-delivery.md` for delivery reports; the
  manifest/backlog are new). Recommendation:
  `docs/operations/<date>-consolidation-status.md`,
  `runtime/releases/<sha>/manifest.json`, and
  `plans/INDEX.md` (existing backlog index).

- **"Defaults: A1/OCR/BO only; one editable source tree; immutable
  releases; PostgreSQL target; existing operational inputs retained
  until verified cutover; no deployment or real-data relocation
  during the initial consolidation."** Agree, but the proposal should
  add: "no git history rewrite, no force-push, no public release of
  the consolidated tree". The GitHub `origin` remains the only remote
  (per `AGENTS.md` "Git remotes"); the GitLab/CI proposal (Plan AE)
  is not in scope for this consolidation.

---

## 2. Strengths of the proposal

To avoid the impression that this memo is only critical:

- **The owner table** in §2 is the proposal's single most important
  contribution. It makes the "single source of truth" claim
  falsifiable and gives the implementer a per-area decision.
- **"Implemented, tested, published, deployed, activated"** is the
  right separation. `roadmap.md` uses similar vocabulary
  (`synthetic-accepted`, `partial`, `gated`, `published`); the
  proposal extends it without contradicting it.
- **The verification of three specific factual claims** in the
  proposal's preamble (§0) is good practice. The duplicate migration
  and absent squashed migration are real defects; the proposal is
  right to surface them.
- **"Treat legal conclusions as review inputs, not automatic new
  operational rules"** is exactly the right separation between
  research and operations. The prior review's GDPR section is a
  review input; this proposal is the place to decide whether and how
  it becomes an ADR.
- **"Inventory first; never sweep; reversible relocation manifest"**
  is the right posture for unknown research/runtime artefacts. It
  matches `docs/research/2026-09-07-research-audit.md` disposition
  rows that have all been reclassified as `retain pending review`.
- **The acceptance list** names the right things: planning coherence,
  release reproducibility, isolation between dev and prod, BO
  confirmation provenance, A1 output invariants, and rollback.

---

## 3. Concrete corrections to apply before the proposal is accepted

In priority order (each item is a one-line change or addition):

1. **Name the file paths** of every plan, ADR, settings module, and
   storage regex in the proposal.
2. **Cite `real-data-rules.md` §14** as the activation gate instead of
   inventing a new one.
3. **Cite `AGENTS.md`'s MigrationExecutor rule** in §4.4.
4. **Cite `portal/release1a/document_storage.py:13-16`** as the
   enforced storage contract.
5. **Split the 39 "missing columns"** into (a) columns that need
   direct new model columns, (b) columns that belong in existing
   `FieldProposal` / `FieldDecision` / `WorkerIdentityRevision` /
   `A1Case.notes` structures. Commit to a per-column decision before
   DB-MIG-1.
6. **Add the field-mapping contract file path**
   (`docs/architecture/release-1a-field-mapping.md`) with a per-row
   destination.
7. **Decide `runtime/releases/` vs existing `runtime/s-<commit>/`**;
   pick one.
8. **Decide `runtime/portal/supervised-development/` vs existing
   `runtime/portal/synthetic-review/`**; pick one.
9. **Add a reproducer-script commitment** to the acceptance list
   (`scripts/release_reproducer.sh <commit-sha>`).
10. **Add a synthetic-seed reconciliation command** (compare DB rows
    against `tests/fixtures/release_1a/workers.json` and
    `assignments.json` after seeding).
11. **State explicit file modes** for `.archive/` and
    `runtime/portal/temporary/retained/` (0600/0700 default;
    0640/0750 only with dedicated-group justification).
12. **Add "no git history rewrite, no force-push, no public release"**
    to the defaults.
13. **Add the missing owner row** for runtime settings + credentials.
14. **Add the missing owner row** for the A1 input contract (today
    `scripts/finalize_a1.py` is the gate; it should be named in the
    table).
15. **Specify the duplicate-migration and squashed-migration fix** in
    §4.3: rebuild the DB from the on-disk graph; do not migrate the
    broken records forward.

---

## 4. Conclusion

The proposal is a sound consolidation direction. It correctly
identifies the local state as broken (duplicate migration, absent
squashed migration, divergent synthetic-review DB) and prescribes a
rebuild-from-graph approach instead of a forward-migrate approach.

The principal corrections are not architectural — they are
specificity: file paths, file modes, contract names, and
per-CSV-column decisions. With the 15 corrections in §3 applied, the
proposal becomes implementable as a single planning deliverable that
satisfies AGENTS.md, `roadmap.md`, and the existing 34 catalog
entries.

No status, gate, or catalog entry has been changed by this review. The
proposal remains a proposal; no implementation work has begun.