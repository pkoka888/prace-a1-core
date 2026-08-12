# Plan L — Agent, Skill, Workflow, and Git Operating Model

**Status:** active
**Priority:** First
**Milestone:** M0–M1
**Owner:** primary agent with Pavel approval for publication/destructive actions

## Objective

Make every agent operate from the same authority hierarchy, visual-first decision
workflow, privacy boundary, skill system, validation gates, and safe Git process
before application scaffolding begins.

## Agent operating loop

Every substantial task follows this sequence:

```text
orient → classify → inspect → research → visualize → decide
→ update authority → implement → verify → hand off → publish only if authorized
```

1. Read `AGENTS.md`, `roadmap.md`, `plans/INDEX.md`, and only the relevant active
   plan/decision/skill.
2. Inspect branch, status, overlapping changes, ignored private paths, and relevant
   implementation before proposing work.
3. Classify the task as research, decision preparation, product implementation,
   A1 production, infrastructure, or Git/history work; do not mix categories.
4. Research discoverable facts before asking Pavel/Jan. Use bounded lower-cost
   subagents for independent workstreams and primary/official sources for unstable
   or high-risk claims.
5. Present meaningful alternatives and synthetic examples in the visual cockpit.
6. Record approval in a decision brief/ADR and update PRD/roadmap/plan before code.
7. Implement the smallest approved vertical slice and verify proportional to risk.
8. Report changes, tests, risks, and remaining decisions. Commit/push only when
   explicitly authorized.

## Roles and authority

- **Primary agent:** owns task classification, source-of-truth updates, integration,
  conflict resolution, final validation, and handoff.
- **Research subagent:** read-only by default; receives a bounded question, source
  and cost requirements, privacy limits, and an explicit deliverable.
- **Implementation subagent:** permitted only with an explicit project-local path,
  file scope, interface contract, and non-overlapping ownership.
- **A1 production agent:** must use the A1 skill and canonical pipeline; cannot
  reinterpret employee or issuance data.
- **Sysadmin:** owns host-level services and system paths; agents provide
  requirements and validate application behavior.
- **Pavel/Jan:** approve operational choices shown as recommended variants;
  destructive publication, real-data activation, and business/legal commitments
  require the appropriate human authority.

No subagent receives `.env`, scans, employee datasets, full A1 documents, or real
payroll data. Only the primary agent changes authoritative planning/policy files.

## Skill portfolio

### Active now

- `a1-pdf-production`: keep. It is a repeated, fragile production workflow with
  deterministic scripts, reference contracts, visual QA, and a stable handoff.

### Planned after stable workflows exist

- `planning-cockpit`: create only after Plan M's catalog schema, renderer,
  validators, and update workflow pass repeatedly. It will synchronize the
  derived visual cockpit and validate source links/status—not own decisions.
- `portal-development`: create only after the Django scaffold, module boundaries,
  commands, fixtures, authorization checks, and test suites stabilize. It will
  route tasks to canonical commands and checks, not duplicate application logic.
- A payroll-release skill may be considered only after certified Czech/German
  rule packs and release procedures exist. It is not authorized now.

### Never skills

One-off architecture decisions, market/legal research, interviews, history
rewrites, migrations, incident investigations, and temporary cleanup remain plans
or runbooks. Avoid a large generic “project” skill that duplicates `AGENTS.md`.

Every future skill must be initialized using the project-approved skill creation
workflow, keep `SKILL.md` concise, put details in one-level references, reuse
canonical scripts, include `agents/openai.yaml`, pass structural validation, and
be forward-tested with synthetic tasks before activation.

## Rules and workflow documents

- `AGENTS.md`: concise non-negotiable rules and navigation.
- `SOUL.md`: product character only.
- `roadmap.md`: milestone/delivery sequence.
- `prd.md`: product outcomes and scope.
- `plans/`: bounded work with owner, status, prerequisites, deliverables, exit.
- `docs/decisions/`: decision register, briefs, and all ADRs using `ADR-NNN-short-title.md`; there is no second ADR location.
- `docs/security/`: operational security/privacy policies.
- workflow READMEs: operator commands and handoffs.
- `.agents/skills/`: only stable repeatable agent procedures.
- research/prototypes: evidence or derived views, never authority.

Use one plan status vocabulary: `planned`, `active`, `blocked`, `awaiting-review`,
`accepted`, `completed`, `superseded`, `historical`, `archived`. Plan M will make
this machine-validatable without rewriting historical prose immediately.

Plan L owns the immediate workflow README corrections, decision register and ADR
convention, plan/index status normalization, documentation checkpoint, and exact-
path staging policy. Plans Q and R own history/reference/privacy remediation and
A1 stabilization respectively; neither is folded into this checkpoint.

## Git workflow

### Normal change

1. Inspect `git status --short`, branch/upstream, relevant diff, ignored paths.
2. Preserve all unrelated edits and untracked work.
3. Work in one change class: governance/docs, A1 code, portal code, runtime-data
   operation, or Git/history operation.
4. Run targeted tests, full relevant suite, `git diff --check`, doc link/status
   validation, and staged PII/secret checks.
5. If a commit is requested, stage exact paths only and inspect
   `git diff --cached --stat` plus the complete staged diff.
6. Use an intent-based commit message and report its hash. Push only if requested.

### Prohibited defaults

- no `git add .`, `git add -A`, wildcard staging, or `git add -f`;
- no reset/checkout/clean that discards work;
- no commit, push, merge, rebase, tag, release, branch deletion, visibility change,
  history rewrite, or force-push without matching authority;
- no combining documentation recovery, A1 changes, portal scaffold, private-data
  operations, or history rewrite in one commit;
- no copying ignored data into a tracked/archive path.

### Remote/history work

Treat any sanitized-history replacement as a separate project: resolve exact
source tree and refs, scan all rewritten objects, compare intended tip trees,
prepare a rollback/coordination procedure, obtain explicit authorization for the
exact remote/refs, publish with the narrowest force-with-lease operation, then
verify a fresh clone. The existing rewrite mirror is not an instruction to push.

## Historical-document policy

- Keep currently referenced historical plans/reports in place with a prominent
  `Historical` or `Superseded — do not execute` header and a current successor.
- Keep provisional research beside its accepted disposition; the higher authority
  always wins when conclusions differ.
- Mark `docs/paddleocr/` as historical reference because its described workflow is
  not present in the active tree.
- Do not move/delete historical files during the present dirty transition.
- After a clean documentation checkpoint, run a reference/reachability and privacy
  audit. Only then may a dedicated change move non-PII historical material to a
  project-local archive or delete it. Never archive PII for convenience.

## Validation and exit

- Authority hierarchy and task startup/Git/subagent rules exist in `AGENTS.md`.
- `SOUL.md` contains product principles and no implementation/legal rules.
- Plans L–P are indexed with prerequisites and statuses.
- Historical documents have visible non-executable status; active docs contain no
  stale Plan C execution gate.
- Internal links resolve, plan headers agree with the index, new docs contain no
  PII/secrets, `git diff --check` passes, and the A1 suite stays green.
- Run Plan M's deterministic planning validator once it exists; until then, use
  read-only local checks for Markdown links and bare paths, plan/index coherence,
  decision sources/approvers, stale active paths, and PII/secret indicators.
- A separate, explicit documentation commit can be staged without A1 code/config
  changes or ignored real-data paths.
- Any such commit stages an explicit reviewed path list only and excludes A1
  code/config, runtime/real data, outputs, and unrelated worktree changes.

## Exclusions

No skill creation, Django scaffolding, Git commit/push, history rewrite, remote
action, host reconfiguration, historical-file deletion, or real-data migration in
this plan.
