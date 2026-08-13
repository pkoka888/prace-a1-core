# Decision Register

**Owner:** product owner
**Approver:** Pavel unless a row identifies Jan, specialist, or sysadmin authority

This register records state; it does not replace the linked approved source. ADRs
live in this directory and use `ADR-NNN-short-title.md`. Allowed states are
`proposed-default`, `variant-selection-required`, `prototype-required`,
`awaiting-pavel`, `awaiting-jan`, `accepted`, `rejected`, `superseded`, and
`not-applicable`.

| ID | Decision | State | Source | Owner | Approver | Date | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|
| DEC-001 | Persistent project root is `/var/www/prace-v-nemecku.tvoje.info` | accepted | [`AGENTS.md`](../../AGENTS.md) | primary agent | Pavel | 2026-08-12 | Workspace Boundary policy | Host service paths remain sysadmin-owned. |
| DEC-002 | Jan-first private portal is Release 1A | accepted | [solution brief §1](2026-08-12-jan-release-1-solution-brief.md#1-product-boundary) | product owner | Pavel | 2026-08-12 | Checked approval in source | Public frontend is outside 1A. |
| DEC-003 | Stable worker plus effective-dated activity profiles | accepted | [solution brief §4](2026-08-12-jan-release-1-solution-brief.md#4-domain-model) | product owner | Pavel | 2026-08-12 | Checked approval in source | Preserve profile-specific provenance. |
| DEC-004 | OCR values require human confirmation; Jan/Pavel/delegated admins have broad 1A workflow authority | accepted | [solution brief §5–6](2026-08-12-jan-release-1-solution-brief.md#5-end-to-end-data-flow) | product owner | Pavel | 2026-08-12 | Confirmed role statement in source | Authorization remains organization-scoped. |
| DEC-005 | Assignment overlap warns instead of universally blocking | accepted | [solution brief §7](2026-08-12-jan-release-1-solution-brief.md#7-assignment-behavior) | product owner | Pavel | 2026-08-12 | Checked approval in source | Ambiguous A1 periods still block preparation. |
| DEC-006 | Django modular-monolith baseline | proposed-default | [solution brief §2](2026-08-12-jan-release-1-solution-brief.md#2-architecture-and-deployment) | product engineering | Pavel | — | ADR-001 proofs pending | Acceptance requires measured proofs. |
| DEC-007 | MFA package | prototype-required | [Plan E](../../plans/2026-08-12-plan-e-architecture-proofs-and-adr.md) | product engineering | Pavel | — | Synthetic comparison pending | Record in ADR-001. |
| DEC-008 | Background queue package | prototype-required | [Plan E](../../plans/2026-08-12-plan-e-architecture-proofs-and-adr.md) | product engineering | Pavel | — | Failure/recovery proof pending | Record in ADR-001. |
| DEC-009 | Protected storage implementation | prototype-required | [Plan E](../../plans/2026-08-12-plan-e-architecture-proofs-and-adr.md) | product engineering | Pavel/sysadmin | — | Authorization/download proof pending | Record in ADR-001. |
| DEC-010 | Audit package and project-owned event boundary | prototype-required | [Plan E](../../plans/2026-08-12-plan-e-architecture-proofs-and-adr.md) | product engineering | Pavel | — | Coverage proof pending | Record in ADR-001. |
| DEC-011 | Separate public frontend | not-applicable | [`roadmap.md`](../../roadmap.md) | product owner | Pavel | 2026-08-12 | Release 1A scope | Revisit only for public growth. |
| DEC-012 | Activate new real-data portal use | awaiting-pavel | [real-data activation gate](../security/real-data-rules.md) | product owner | Pavel | — | Gate evidence incomplete | Synthetic work may proceed. |
| DEC-013 | Require the 15 GiB/15% capacity gate and tested encrypted backup/restore before real-data activation | accepted | [Plan K](../../plans/2026-08-12-plan-k-server62-readiness.md) | product owner/sysadmin | Pavel | 2026-08-13 | Operator decision; policy reconciled in roadmap, solution brief, and real-data gate | Does not block synthetic implementation. |
| DEC-014 | Confirm published sanitized checkpoint `c01aa2b` as the approved repository baseline | awaiting-pavel | [Plan Q](../../plans/2026-08-12-plan-q-repository-history-reference-privacy.md) | primary agent | Pavel | — | Remote refs observed at `c01aa2b`; original approval evidence not yet reconciled | No further push, rollback-ref publication, or GC is authorized. |
