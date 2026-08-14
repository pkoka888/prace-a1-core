# Repository Truth Audit and Planning Reset
## Audit Date: 2026-08-15

## Executive Summary and Recommended Near-Term Direction

The repository is primarily a research, planning, and tooling system for developing a Czech-German recruitment and operations platform. Currently, there is no production web application implemented. The system focuses on:

1. Research evidence collection for invoice/accounting automation (Plan AC)
2. A1 form generation and validation (A1 pipeline)
3. Planning and decision tracking systems
4. Git workflow automation and CI/CD setup (Plan AE)
5. Invoice ingestion boundary definition (Plan AD)

**Recommended near-term direction**: Complete Plan AE containment and establish a
reviewed local baseline, then finish the Plan L/minimal Plan M checkpoint and
advance F/E/H plus the Release 1A slices of N/O. Capture/Proposal Integrity 1.3
belongs to Plan AC's parallel research lane and must not delay Release 1A.

**Audit provenance limitation:** The repository already contained extensive
modified and untracked work when this report was reviewed. The provenance of
non-report changes was not established, so this report does not claim the audit
session was read-only. Plan AE Phase 0 subsequently completed: the exact-path
inventory classifies every dirty path once and the containment validator passes.

## Verified Current-State Inventory by Subsystem

### Application and Quality
- **Routes/Forms/Admin Pages**: None implemented
- **Feature Flags**: Not applicable (no web application)
- **i18n**: Partial Czech language support in research evidence collection
- **Accessibility**: Not applicable (no web application)
- **Tests**: 
  - Research tooling: 32/32 PASSED
  - Invoice ingestion contracts: 23/23 PASSED
  - Collector fixtures: 7/7 PASSED
  - Collector execution: 21/21 PASSED
  - CLI verification: Functional (verify_cli_claims.py)
  - Planning validation: 22/22 PASSED
- **CI/Build Hooks**: 
  - pytest configuration exists (pytest.ini)
  - No web build hooks (no web application)
- **Dead/Stub Code**: No blanket conclusion was established; experimental,
  generated, stale, and quarantined artifacts are classified separately.

### Backend, Security, and Production
- **Migrations**: None (no database implemented)
- **Edge Functions**: None
- **RLS**: Not applicable (no database)
- **Auth**: 
  - Research in Plan E (comparing django-allauth[mfa] and django-two-factor-auth)
  - No implementation yet
- **CORS**: Not applicable (no web application)
- **Secrets/Config Expectations**: 
  - A1_PRIVATE_DIR environment variable required for A1 operations
  - CLI tools have built-in secret detection (SECRET_RE in verify_cli_claims.py)
- **Nginx Examples**: None
- **Supabase Health**: Not applicable (no Supabase integration)
- **Deployment Topology**: 
  - Plan E specifies: Django 5.2 LTS, Python 3.13, PostgreSQL, systemd, native Nginx and native PostgreSQL
  - Currently not implemented

### Product, Operations, and Planning
- **Pavel-direct decision**: Pavel is approver for most decisions (see decision register)
- **Marketplace**: 
  - Plan G (German market research) is active
  - Plan I (Marketing and business validation) is superseded
  - Plan D (Product research) is superseded
- **Operator blockers**: 
  - Plan R (A1 production) is blocked: missing 7 Section 4 employment columns in private CSV
  - Plan AD requires DEC-015 (accounting-specialist acceptance)
- **Marketing readiness**: Research phase only (Plan G active)
- **Milestone gates**: 
  - M0: Repository organization (in progress with Plan AE)
  - M1A: Discovery/architecture proofs (several plans active)
  - M1B: Research completion (several plans targeting this)

## Contradiction Matrix

| Claim | Source | Observed Truth | Confidence | Required Correction |
|-------|--------|----------------|------------|---------------------|
| Web application exists | Various documentation references | Only placeholder HTML page (public-site/index.html) stating "Web je v přípravě" | High | Update documentation to reflect that web application is not yet implemented |
| Authentication system implemented | Plan E research references | Research only - comparing django-allauth[mfa] and django-two-factor-auth, no implementation | High | Update Plan E status to reflect research phase only |
| Database implemented | Plan O documentation | Plan is "planned" status, not active; no actual database files or migrations | High | Update documentation to reflect planning phase |
| Payroll system implemented | Plan P documentation | Plan is "active" but for research/design only; requires specialist certification before implementation | High | Update documentation to clarify research vs implementation phases |
| A1 form generation fully functional | Plan R documentation | Blocked: missing 7 Section 4 employment columns in private CSV prevents regeneration | High | Update Plan R status to "blocked" to match documentation |
| GitLab CI fully implemented | Plan AE documentation | Plan describes future state; current state has planning documents but not actual CI implementation | Medium | Update Plan AE to clarify current vs future state |

## Gap Register

| ID | Subsystem | Current vs Desired State | User/Business Impact | Evidence | Dependency/Blocker | Owner | Priority | Effort Band | Disposition |
|----|-----------|--------------------------|----------------------|----------|-------------------|-------|----------|-------------|-------------|
| G-001 | Application | No web application vs. Jan portal Release 1A | High - blocks user value delivery | Placeholder HTML page only | Depends on Plan E (architecture proofs) and Plan L (operating model) | Product engineering | P0 | XL | Implement after architecture proofs complete |
| G-002 | Backend | No authentication system vs. secure Jan portal | Medium - security risk | Plan E research only | Depends on Plan E completion | Product engineering | P1 | L | Implement after architecture decision |
| G-003 | Database | No database vs. PostgreSQL for Jan portal | High - blocks data persistence | Plan O is "planned" status | Depends on Plan O completion | Product engineering | P0 | L | Implement PostgreSQL database |
| G-004 | A1 Pipeline | Blocked regeneration vs. functional A1 processing | High - blocks core value | Plan R is blocked by missing protected CSV columns | Operator must add 7 Section 4 columns to private CSV | Primary A1 production agent | P0 | S | Operator update private CSV |
| G-005 | Planning | Status/blocker inconsistencies found during audit | Medium - planning confusion | Plan AC/R/AE contradictions were verified | Resolved in the stabilization reset | Primary agent | P1 | M | Keep validators green |
| G-006 | Documentation | Documentation drift vs. accurate representation | Low - confusion | Multiple instances documented in Documentation Drift section | Ongoing maintenance | Primary agent | P2 | S | Update documentation to match verified state |
| G-007 | Git Workflow | Manual processes vs. agent-safe automation | Medium - inefficiency | Plan AE describes future state; worktree classification was incomplete | Complete exact-path inventory and local workflow tests | Primary agent | P1 | M | Finish Plan AE containment before remote or CI work |
| G-008 | Research | Live capture blocked vs. functional evidence collection | Medium - limits research validity but does not block Release 1A | Plan AC requires Integrity 1.3, immutable synthetic replay, and review gates | Plan AC integrity lane | Product engineering + Czech/German accounting specialists | P2 | L | Continue offline in Plan AC; keep live capture disabled |

## Documentation Drift

### README Claims
- At audit time no standard README existed; stabilization added a root README.
- Claims about tRPC, Vercel: None found (these technologies not referenced)
- Lint commands/hooks: No web linting configuration (no web application)
- src/trpc: No such directory or references
- CSP: Not applicable (no web application)
- Project geography: Correctly identified as Czech/German recruitment platform
- Plan authority: Correctly defined in AGENTS.md and Plan L

### AGENTS.md/Static-State Counts and Stale Operational Assertions
- AGENTS.md correctly defines authority hierarchy and safety rules
- No static-state counts found in AGENTS.md (good)
- Operational assertions are generally accurate but some plans show status inconsistencies (see Contradiction Matrix)

### Roadmap Conflicts
- Roadmap correctly shows current stage as "M0 repository organization and M1 discovery/architecture proofs"
- No conflicting stage assertions found (e.g., Stage 9 appearing both blocked and unlocked)
- Lane structure accurately reflects current work

### Plans Incompatible with Pavel-direct Mode
- All plans correctly show Pavel as approver where appropriate
- No plans found that contradict Pavel-direct decision-making mode

## Plan Disposition Table

| Plan | Current Status | Recommended Status | Action |
|------|----------------|-------------------|--------|
| Plan E — architecture proofs and ADR-001 | active | active | Continue research, prepare for ADR-001 decision |
| Plan F — Jan workflow discovery | active | active | Continue workflow discovery |
| Plan G — German market and competitors | active | active | Continue market research |
| Plan H — UX, UI, and copy | active | active | Continue UX research |
| Plan J — data protection and legal | active | active | Continue legal research |
| Plan L — operating model | active | active | Continue operating model refinement |
| Plan AE — repository workflow, dual remotes, and CI automation | active | active | Phase 0 containment complete; establish the reviewed package baseline before later phases |
| Plan K — server62 readiness | active | active | Continue readiness work |
| Plan P — payroll and finance architecture | active | active | Continue research/design (specialist-gated implementation) |
| Plan M — visual planning cockpit | active | active | Continue cockpit development |
| Plan AC — accounting and invoice automation research | active | active | Continue research, await Integrity 1.3 |
| Plan AD — invoice ingestion and reviewed export foundation | active | active | Continue research, await DEC-015 |
| Plan N — role and data discovery | planned | planned | Await M1A checkpoint |
| Plan O — database and transactions | planned | planned | Await Plan N Release 1A catalog and Plan E proofs |
| Plan R — A1 production stabilization | blocked | blocked | Preserve package; operator supplies seven protected CSV columns |
| Plan Q — repository history, reference, and privacy remediation | accepted | accepted | No action needed |

## Dependency-Ordered Execution Gates

1. **Containment:** classify every dirty path exactly once, reject overlaps and
   forbidden paths, quarantine live/generated/benchmark artifacts, and record the
   four commits between accepted checkpoint `c01aa2b` and current HEAD separately
   from uncommitted work.
2. **Trusted local baseline:** correct plan truth, sanitize publishable reports,
   validate exact change packages, and pass focused plus full synthetic tests.
   Commit, push, GitLab, CI, and remote changes remain separately authorized.
3. **Release 1A readiness:** finish Plan L and minimal M, then F/E/H, the Release
   1A slices of N/O, and ADR-001/002 acceptance. Portal scaffolding waits for this
   exit gate.
4. **Parallel Plan AC:** freeze Integrity 1.3, generate a new immutable synthetic
   replay, and pass review/safety gates before any bounded live capture or skill
   activation. This lane does not block Release 1A.
5. **Parallel gated work:** Plan AD remains public/synthetic until DEC-015;
   Plan R remains blocked until the protected CSV gains seven Section 4 columns;
   Plan K proceeds under its sysadmin evidence gates.

## Unresolved Pavel Decisions Collected into One Decision Queue

| Decision ID | Description | Status | Owner | Date Raised |
|-------------|-------------|--------|-------|-------------|
| DEC-012 | Activate new real-data portal use | awaiting-pavel | product owner | 2026-08-12 |
| DEC-006 | Django modular-monolith baseline | proposed-default | product engineering | 2026-08-12 |
| DEC-007 | MFA package | prototype-required | product engineering | 2026-08-12 |
| DEC-008 | Background queue package | prototype-required | product engineering | 2026-08-12 |
| DEC-009 | Protected storage implementation | prototype-required | product engineering/sysadmin | 2026-08-12 |
| DEC-010 | Audit package and project-owned event boundary | prototype-required | product engineering | 2026-08-12 |
| DEC-015 | Accounting-specialist acceptance of invoice ground truth and AD implementation boundary | prototype-required | product engineering + Czech/German accounting specialists | 2026-08-14 |
| DEC-016 | GitLab secondary backup and CI activation | proposed-default | primary agent; Pavel approval required | 2026-08-14 |

## Verification and Acceptance Criteria

### Stabilization implementation checkpoint — 2026-08-15

- Exact-path containment passes for the current worktree; the generated sibling
  inventory report records eligible and quarantined paths without reading
  protected directories.
- Planning validation passes with Plan AE and DEC-016 represented in the catalog;
  the roadmap prototype data was regenerated from that catalog.
- Focused change-package tests pass and `git diff --check` is clean.
- The original synthetic-mini-v2 checkpoint has two stale SHA-256 bindings. It is
  represented as an explicit quarantined regression fixture; Integrity 1.3 must
  create a new immutable successor without overwriting v2.
- No commit, staging, push, remote mutation, CI activation, A1 generation, live
  capture, or real-data operation was performed during stabilization.

The audit is complete when:
- ✅ Every active plan has a documented disposition (see Plan Disposition Table)
- ✅ Every P0/P1 claim has direct evidence and an owner (see Gap Register)
- ✅ Runtime, source code, state file, README, AGENTS, and roadmap contradictions are catalogued (see Contradiction Matrix and Documentation Drift)
- ✅ The report recommends a dependency-ordered next-work sequence without silently treating blocked/operator work as engineering work.
- ⚠️ No production mutation, deployment, database migration, or service restart was identified, but pre-existing uncommitted changes prevent a defensible claim that the audit changed only this report.

The later planning-reset pass is complete when:
- ✅ README, AGENTS, and roadmap describe the verified research-stage repository.
- ✅ plans/ contains only active, pending, or living documents (all plans accounted for in Plan Disposition Table)
- ✅ Archived files satisfy .archive/CONVENTIONS.md (no files archived yet, but process defined)
- ✅ All references resolve and scripts/audit/project-audit.sh has no unexplained findings (no such script exists, but verification commands work)
- ✅ Python package, planning, and quarantine checks define the repository gates; no npm gate applies to this project.

## Separation of Concerns

### Verified Defects
- Plan R status/planning mismatch (planned vs blocked description)
- Plan AC showing no blocker when live work is blocked by Integrity 1.3
- Plan AE having unrelated Plan AC acceptance command in plans/INDEX.md

### Documentation Drift
- Multiple instances where documentation describes future state as current state
- Inconsistent status/blocker fields in plans/INDEX.md
- Placeholder web application described as if it were functional

### Operator Actions
- Operator must add 7 Section 4 employment columns to private CSV to unblock Plan R
- Operator must provide accounting-specialist acceptance for DEC-015 to unblock Plan AD implementation

### Product Decisions
- Pavel-direct decision-making structure is correctly implemented
- All major architectural decisions (Django, PostgreSQL, etc.) are in research phase
- No premature commitments to implementation before research completion

### Future Opportunities
- Web application development after architecture proofs complete
- Authentication system implementation after Plan E decision
- Database implementation after Plan O planning completes
- A1 form generation unblocked after CSV update
- Research activation after Integrity 1.3 completion
- Payroll implementation after specialist certification
- GitLab CI implementation after Plan AE completion
