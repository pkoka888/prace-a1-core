# Plan AE — Repository Workflow, Dual Remotes, and CI Automation

## Goal

Stabilize the mixed worktree before further feature work, update the roadmap and planning index with explicit parallel lanes and phase exits, then introduce agent-safe Git automation and GitLab CI.

GitHub remains the authoritative `origin`; GitLab becomes the private secondary backup and CI host. GitHub Actions remains technically available for private repositories, but hosted execution consumes a monthly allowance and can incur charges beyond it. Self-hosted GitLab CI is therefore the preferred zero-incremental-provider-cost path.

**Status:** active
**Milestone:** M0
**Owner:** primary agent

## Current checkpoint — Phase 0 complete

Phase 0 containment passed on 2026-08-15. The generated inventory at
`plans/audits/2026-08-15-worktree-inventory.json` records the live exact counts
and classifies every dirty path exactly once as eligible or quarantined. This proves
classification only; it does not approve any path for staging or publication.

## Implementation Phases

### Phase 0 — Inventory and containment

Goal: every changed path has an owner, disposition, commit package, and validation gate before staging is possible.

- Add a dedicated Plan AE for repository workflow, dual remotes, and CI automation; index it as an active M0 lane.
- Create a machine-readable change-package catalog and schema covering:
  - governance/planning;
  - GitLab operations and automation;
  - A1 documentation/policy;
  - CLI verification;
  - Plan AC integrity and research tooling;
  - Plan AD invoice contracts;
  - planning/research cockpit prototypes;
  - unrelated or quarantined artifacts.
- Permanently exclude ignored PII paths, `.history-remediation/`, `scripts/validate_ocr_proposals.py`, and `práce-v-německu.zip`.
- Require manual privacy review and path sanitization for CLI reports, tooling ledgers, rendered HTML, `public-site/`, and other unclassified files.
- Restore the useful authority details lost from `AGENTS.md`: approval propagation, plans/skills/research distinctions, and the prohibition on treating research as execution authority.

Exit: the catalog covers every modified/untracked path; no unsafe, sensitive, quarantined, or unclassified path can be staged by automation.

### Phase 1 — Restore a green trusted baseline

Goal: local deterministic checks are green before CI or publication automation is trusted.

Sequential blockers:

1. Preserve synthetic-mini-v2 as a stale quarantined checkpoint. Its two known
   hash mismatches are asserted by a regression test and status record. Do not
   re-pin or overwrite it; Plan AC Integrity 1.3 must create a new versioned
   successor and clean-room replay.
2. Sanitize host-specific paths from publishable CLI audit outputs.
3. Validate the change-package catalog against the complete dirty path set and
   produce an exact-path, fail-closed inventory receipt.

Capture/Proposal Integrity 1.3, successor synthetic artifacts, and review queues
belong to Plan AC's parallel integrity lane. They are not Plan AE implementation
work and do not block the Release 1A critical path. Plan AE requires those files
to remain quarantined or explicitly classified while its own baseline is restored.

Parallel after item 1:

- Validate the Plan AD in-memory contract package.
- Validate planning catalog/cockpit freshness.
- Review A1 policy-only changes without regenerating the blocked provisional package.
- Review prototype and public-site artifacts separately; portal scaffolding remains prohibited.

Exit: all eligible package checks and the full synthetic pytest suite pass;
planning and generated assets are current; quarantined artifacts either remain
absent from clean clones or pass explicit expected-quarantine regression checks;
no live research capture, portal scaffold, or real-data operation has occurred.

### Phase 2 — Reconcile authoritative planning

Goal: roadmap, index, catalog, plans, and decisions describe one executable sequence.

- Update `roadmap.md` with these lanes:
  - **Critical M0/M1A:** worktree stabilization → Plan L/M checkpoint → E/F/H → N-1A/O-1A → ADR-001/002 acceptance.
  - **Parallel infrastructure:** Plan K plus GitLab runner preparation.
  - **Parallel non-blocking research:** G/J/P and broader N/O.
  - **Plan AC integrity lane:** Integrity 1.3 and synthetic replay first; live capture remains blocked.
  - **Plan AD lane:** in-memory proof may proceed; persistence, fiscal behavior, Slauf mapping, and acceptance remain DEC-015-gated.
  - **Separate A1 lane:** Plan R remains blocked on the seven missing Section 4 columns; preserve the existing provisional package.
  - **Quarantined lane:** benchmark ranking, OCR proposal validator, ZIP, and unreviewed operational artifacts.
- Update `plans/INDEX.md` with lane, concurrency, prerequisite, owner, current blocker, expected result, and acceptance command for every active plan.
- Add Plan AE and record the secondary-backup-plus-CI decision in the decision register.
- Keep ADR-001 proposed and portal scaffolding blocked until its proofs and M1A gates pass.
- Regenerate the planning data asset and verify index/header/catalog coherence.

Exit: the planning validator passes and an agent can determine what is runnable, parallel, gated, or quarantined without interpreting narrative history.

### Phase 3 — Agent-safe local Git automation

Goal: automate repetitive checks without weakening human authorization or exact-path staging.

Add a testable repository workflow command with these interfaces:

- `audit --package <id>`: read-only classification, forbidden-path, secrets/PII indicator, diff, and required-check report.
- `stage --package <id> --confirm <id>`: stage only the manifest’s explicit paths after a successful audit; reject ignored, forbidden, missing, unclassified, overlapping, or unexpectedly changed paths.
- `verify-staged --package <id>`: inspect the staged path set and complete staged diff, rerun package checks, and emit a machine-readable receipt.
- `publish --branch <name> --confirm <name>`: require a clean index/worktree for the package sequence, validated receipts, matching local branch/upstream expectations, and explicit interactive confirmation; push GitHub first and GitLab second.
- `status --remotes`: compare local, GitHub, and GitLab branch SHAs without changing state.

Safety invariants:

- No `git add .`, `-A`, wildcard, force-add, force-push, tags, `--all`, branch deletion, credential reads, or remote configuration changes.
- Commit creation and publication remain separately and explicitly user-authorized.
- A failed GitLab push never rewrites or rolls back GitHub.
- Logs contain paths, hashes, commands, and exit states—not file contents, credentials, or PII.
- Unit tests use temporary synthetic repositories only.

Exit: synthetic tests prove forbidden paths and unclassified changes fail closed, package staging is exact, and dual publication cannot occur without confirmation.

### Phase 4 — GitLab secondary and CI activation

Goal: reviewed branches are backed up and validated on self-managed infrastructure.

1. Refresh the revoked GitLab credential from the SOPS vault without exposing it in commands, repository files, or logs.
2. Add the `gitlab` LAN remote, push `master`, set GitLab’s default branch to `master`, then verify SHA equality with GitHub.
3. Provision a project-scoped, protected GitLab Runner on an isolated runner host using a container executor; do not install it on the GitLab server or give it access to repository PII directories.
4. Add `.gitlab-ci.yml` with parallel jobs:
   - governance/schema/link validation;
   - fast unit and contract tests;
   - full synthetic pytest suite;
   - generated-asset freshness;
   - expected-quarantine assertions.
5. CI must not perform deployments, live collection, commits, pushes, mirroring, A1 generation, or access secrets/real-data directories. Do not retain repository outputs as CI artifacts by default.
6. Run pipelines for GitLab branches and merge requests. Publication continues through the guarded local GitHub-first/GitLab-second command.

Native GitLab pull mirroring is not selected because pull mirroring is Premium/Ultimate, while this GitLab CE setup is intended to remain Free. Bidirectional mirroring is also avoided because GitLab warns it can create conflicts.

Exit: the same reviewed branch SHA exists on both remotes, GitLab CI passes on synthetic inputs, GitHub remains authoritative, and no automatic deployment or reverse synchronization exists.

## Commit Package Order

1. Governance and reconciled plans.
2. Plan AC integrity repairs and synthetic fixtures.
3. Plan AD in-memory contracts.
4. CLI verification and sanitized reports.
5. Planning/research cockpit assets.
6. A1 policy/documentation changes.
7. Git workflow automation and tests.
8. GitLab CI and integration documentation.

Each package receives its own explicit-path review, validation receipt, commit authorization, and commit. The ZIP, quarantined validator, PII paths, and rejected/unclassified artifacts are never included.

## Test and Acceptance Plan

- Full synthetic test suite returns zero failures.
- `tests/test_validate_change_packages.py` proves complete, non-overlapping,
  fail-closed dirty-path classification and forbidden-path rejection.
- Planning validator, generated planning asset, and research cockpit checks pass.
- Plan AC capture and integrity checks remain owned and accepted by Plan AC.
- Git automation tests prove exact-path staging, classification completeness, confirmation enforcement, remote ordering, and fail-closed handling of dirty/divergent state.
- CI runs without private A1 inputs, external AI/API calls, live network collection, deployments, or paid services.
- A final SHA comparison confirms GitHub and GitLab contain the intended branch commits.

## Assumptions and Defaults

- GitHub remains the source of truth; GitLab is secondary backup plus CI.
- GitHub Actions is not impossible for private repositories—GitHub Free currently includes 2,000 hosted minutes monthly, and self-hosted runners are free—but GitLab CI better fits the existing on-premise and cost-control requirements.
- GitLab CI/CD and self-managed runners are available on the Free tier.
- No existing uncommitted file is presumed acceptable merely because tests currently reference it.
- No commit, push, runner installation, GitLab setting change, deletion, live capture, or portal scaffolding is implicitly authorized by this plan.
