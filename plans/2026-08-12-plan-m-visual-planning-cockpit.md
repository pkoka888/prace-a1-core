# Plan M — Generated Visual Planning Cockpit

**Status:** planned
**Prerequisite:** Plan L accepted
**Milestone:** M1 and continuous
**Owner:** product design + engineering

## Objective

Make the repository-controlled prototype the visual front door to planning while
keeping Markdown policies, decisions, roadmap, PRD, and plans authoritative.

## Work

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
