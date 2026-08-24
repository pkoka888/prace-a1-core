# Plan M — Generated Visual Planning Cockpit

**Status:** active
**Prerequisite:** Plan L governance baseline exists. Plan L acceptance is required
for this plan's exit, not for synthetic catalog and validator work to begin.
**Milestone:** M1 and continuous
**Owner:** product design + engineering

## Objective

Make the repository-controlled prototype the visual front door to planning while
keeping Markdown policies, decisions, roadmap, PRD, and plans authoritative.

## Work

- Deliver the minimal Release 1A catalog, source linker, dependency/status
  validator, and whole-platform shell before expanding the visual views.

- Define a versioned structured catalog with fields `id`, `kind`, `title`, `owner`,
  `approver`, `milestone`, `status`, `decision_state`, `evidence_state`,
  `dependencies`, `risks`, `quality_gates`, `source_links`, `exit_evidence`,
  `last_reviewed`, `executable`, and `successor`.
- Generate or data-bind visual views from the same catalog: whole-platform map,
  roadmap, Now/Next/Later, dependencies, role journeys, service blueprint, data
  lifecycle, entities/permissions, states, decisions, and implementation evidence.
- Add risks/blockers, quality-gate, evidence/confidence, role, data-lifecycle,
  entity/state, and historical-context views with scope filters: Current, Release
  1A, Later Design, Public Growth, and Historical.
- Start every substantial product/architecture review with synthetic visual
  alternatives; record the selected option in a brief/ADR before changing status.
- Add validators for schema, IDs, statuses, dependencies, sources, evidence, and
  conflicts with the authoritative document metadata.
- The offline, no-autofix validation command also checks Markdown links and bare
  paths; plan/index/catalog status coherence; duplicate IDs/missing dependencies;
  `executable: false` for historical records; missing owners/gates/evidence/source;
  accepted decisions without approved sources; staged PII/secret indicators; and
  prototype cards without authoritative source links.
- Keep the prototype self-contained, accessible, repository-local, and free of
  PII/external runtime dependencies. Do not introduce an external PM SaaS as an
  authority.

## Deliverables and exit

- Catalog schema, example catalog, deterministic renderer/loader, and validation
  command.
- Whole-platform overview first, followed by role and engineering drill-downs.
- Every visual item links to a real source; no manually duplicated independent
  backlog/status remains.
- Evidence state is exactly `none`, `provisional`, `synthetic-tested`,
  `primary-source-verified`, `operator-verified`, or `specialist-verified`.
- Synthetic desktop/mobile prototype passes link, accessibility-smoke, JavaScript,
  catalog, and screenshot review.

Only after repeated successful updates should a `planning-cockpit` skill be
created to operate the stable commands.

## Planning-tooling checkpoint (2026-08-13)

Minimal Release 1A slice delivered and validated:

- Catalog schema (`planning/catalog.schema.json`), versioned catalog (`planning/catalog.json`, 45 required IDs), deterministic validator (`scripts/validate_planning.py`, named checks — see the validator's `--json` for the live count, exit 0/1/2, deterministic `--json` with `next_actions`), and a generated cockpit asset (`docs/prototypes/roadmap-portal/planning-data.js`) consumed by a new "Plánovací katalog" tab that shows Now/Parallel/Gated lanes, the Release 1A path, plan/decision state, missing-gate visibility, and historical/non-executable state.
- The prototype remains a derived, synthetic presentation; Markdown plans and the
  decision register remain authoritative, while the catalog is their validated
  derived index. The asset regenerates deterministically, supports a read-only
  `--check`, and is covered by `tests/test_validate_planning.py`.

**Plan M is `active`**, not accepted/completed. The minimal slice is operational;
broader cockpit views, accessibility/screenshot review, repeated update evidence,
and the later planning-cockpit skill gate remain open.

Plan AF appears only as a parallel tooling-evidence item. Its evaluation results
do not satisfy Plan M's accessibility, screenshot, or repeated-use exit gates.
