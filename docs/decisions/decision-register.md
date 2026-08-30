# Decision Register

**Owner:** product owner
**Approver:** Pavel unless a row identifies Jan, specialist, or sysadmin authority

This register records state; it does not replace the linked approved source. ADRs
live in this directory and use `ADR-NNN-short-title.md`. Allowed states are
`proposed-default`, `variant-selection-required`, `prototype-required`,
`awaiting-pavel`, `awaiting-jan`, `accepted`, `rejected`, `superseded`, and
`not-applicable`.

An approver is not "waiting" merely because they own the eventual decision.
Evidence-gated rows remain `prototype-required` or `proposed-default` until a
complete review packet exists. The
[Release 1A unblock and review packet](../release-1a/unblock-review-packet.md)
defines which synthetic defaults apply now and which exact facts or authorities
still require Jan or Pavel.

Human approval, technical validation, implementation permission, and real-data
activation are separate fields in [`planning/approvals.json`](../../planning/approvals.json).
The HTML decision panel is the preferred review surface; this table is a concise
human index and must agree with the JSON validator.

| ID | Decision | State | Source | Owner | Approver | Date | Evidence | Notes |
|---|---|---|---|---|---|---|---|---|
| DEC-001 | Persistent project root is `/var/www/prace-v-nemecku.tvoje.info` | accepted | [`AGENTS.md`](../../AGENTS.md) | primary agent | Pavel | 2026-08-12 | Workspace Boundary policy | Host service paths remain sysadmin-owned. |
| DEC-002 | Jan-first private portal is Release 1A | accepted | [solution brief §1](2026-08-12-jan-release-1-solution-brief.md#1-product-boundary) | product owner | Pavel | 2026-08-12 | Checked approval in source | Public frontend is outside 1A. |
| DEC-003 | Stable worker plus effective-dated activity profiles | accepted | [solution brief §4](2026-08-12-jan-release-1-solution-brief.md#4-domain-model) | product owner | Pavel | 2026-08-12 | Checked approval in source | Preserve profile-specific provenance. |
| DEC-004 | OCR values require human confirmation; Jan/Pavel/delegated admins have broad 1A workflow authority | accepted | [solution brief §5–6](2026-08-12-jan-release-1-solution-brief.md#5-end-to-end-data-flow) | product owner | Pavel | 2026-08-12 | Confirmed role statement in source | Authorization remains organization-scoped. |
| DEC-005 | Assignment overlap warns instead of universally blocking | accepted | [solution brief §7](2026-08-12-jan-release-1-solution-brief.md#7-assignment-behavior) | product owner | Pavel | 2026-08-12 | Checked approval in source | Ambiguous A1 periods still block preparation. |
| DEC-006 | Django modular-monolith baseline | accepted | [ADR-001](ADR-001-jan-portal-architecture.md) | product engineering | Pavel | 2026-08-17 | Pavel approved ADR-001 architecture direction | Technical validation and implementation gate remain pending in JSON. |
| DEC-007 | `django-allauth[mfa]` with mandatory privileged-role TOTP | accepted | [ADR-001](ADR-001-jan-portal-architecture.md) | product engineering | Pavel | 2026-08-17 | Pavel approved all ADR-001 selected components | MFA checks remain pending. |
| DEC-008 | `django-q2` ORM-broker background queue | accepted | [ADR-001](ADR-001-jan-portal-architecture.md) | product engineering | Pavel | 2026-08-17 | Pavel approved all ADR-001 selected components | Retry/idempotency/crash checks remain pending. |
| DEC-009 | Encrypted filesystem with authorized Nginx internal delivery | accepted | [ADR-001](ADR-001-jan-portal-architecture.md) | product engineering | Pavel/sysadmin | 2026-08-17 | Pavel approved direction; sysadmin validation pending | Storage authorization and host-fit checks remain pending. |
| DEC-010 | Project-owned append-only `AuditEvent` boundary | accepted | [ADR-001](ADR-001-jan-portal-architecture.md) | product engineering | Pavel | 2026-08-17 | Pavel approved all ADR-001 selected components | Audit coverage checks remain pending. |
| DEC-011 | Separate public frontend | not-applicable | [`roadmap.md`](../../roadmap.md) | product owner | Pavel | 2026-08-12 | Release 1A scope | Revisit only for public growth. |
| DEC-012 | Activate new real-data portal use | prototype-required | [real-data activation gate](../security/real-data-rules.md) | product owner | Pavel | — | Gate evidence incomplete; not ready for approval | Synthetic work may proceed; move to `awaiting-pavel` only after every activation item has evidence. |
| DEC-013 | Require the 15 GiB/15% capacity gate and tested encrypted backup/restore before real-data activation | accepted | [Plan PLAN-INFRA](../../plans/PLAN-INFRA.md) | product owner/sysadmin | Pavel | 2026-08-13 | Operator decision; policy reconciled in roadmap, solution brief, and real-data gate | Does not block synthetic implementation. |
| DEC-014 | Confirm published sanitized checkpoint `c01aa2b` as the approved repository baseline | accepted | [Plan PLAN-A1](../../plans/PLAN-A1.md) | primary agent | Pavel | 2026-08-13 | Remote refs observed at `c01aa2b`; original approval evidence not yet reconciled | Acceptance does not authorize GC, ref deletion, or another push. |
| DEC-015 | Accounting-specialist acceptance of invoice ground truth and AD implementation boundary | prototype-required | [Plan PLAN-INVOICE](../../plans/PLAN-INVOICE.md) | product engineering + Czech/German accounting specialists | accounting-specialist (role required) | — | Inputs defined; acceptance pending specialist sign-off | Public/synthetic in-memory proof may proceed; persistence/adapters, production implementation, Plan acceptance, real invoices, bookkeeping, payments, tax advice, and production activation remain unauthorized. |
| DEC-016 | GitLab secondary backup and CI activation with GitHub as authoritative origin | proposed-default | [Plan PLAN-INFRA](../../plans/PLAN-INFRA.md) | primary agent | Pavel | — | Plan defines the proposal; explicit activation approval is not recorded | GitHub remains authoritative `origin`; no GitLab remote, CI, credential, runner, or publication mutation is authorized yet. |

AF2 credential provisioning is an operational prerequisite, not a product
decision, so it is intentionally not DEC-017. Plan AF2/AF2.2 tracks it until the
offline containment and exact zero-cost gates make a live credential necessary;
provisioning never implies authority to run, publish, or activate a model.
