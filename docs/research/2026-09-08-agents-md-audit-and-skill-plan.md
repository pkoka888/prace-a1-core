# AGENTS.md strictness audit + skill/MCP plan

**Date:** 2026-09-08
**Scope:** `AGENTS.md`, `.agents/skills/`, `.opencode/skills/`, the
standing-authorization prose, and the missing tooling for a
Django/PostgreSQL/git workflow.

**Cross-references:**
- `docs/research/2026-09-08-local-a1-automation-review.md`
- `docs/research/2026-09-08-consolidation-plan-feedback.md`
- `AGENTS.md` (232 lines)
- `.agents/skills/a1-pdf-production/SKILL.md` (45 lines, "ready")
- `.opencode/skills/market-research-evidence/SKILL.md` (97 lines, "experimental")

**Method.** Section-by-section audit of `AGENTS.md` (safety / scope /
delegate-or-gate / blast radius), plus three parallel research
passes against (a) Anthropic + opencode + community AGENTS.md
conventions, (b) the `modelcontextprotocol/servers` ecosystem and
open-source skills, (c) the project's own gaps from the two prior
reviews.

This is a planning memo. No file is modified. No commit. No push.

---

## 0. Headline finding

`AGENTS.md` is **232 lines**. Anthropic's docs and the
`agents.md` spec both recommend **<200 lines** as the budget before
adherence drops:

> "Files over 200 lines consume more context and may reduce adherence."
> — https://docs.claude.com/en/docs/claude-code/memory

> "If your CLAUDE.md is too long, Claude ignores half of it because
> important rules get lost in the noise. **Fix**: Ruthlessly prune."
> — https://docs.claude.com/en/docs/claude-code/best-practices

The PII / git / secrets core (lines 10–16) is well-calibrated. The
over-restriction concentrates in **delegation language** and in
**workflow records** (multiple parallel delivery reports vs one
report, separate-commit rule, output/provisional preservation).

This audit identifies **12 over-restrictive or contradictory rules**
to relax (with concrete one-line rewrites), **4 missing skills** the
project should adopt now, and **3 MCP servers** to wire in for
filesystem, git and documentation access.

---

## 1. AGENTS.md section-by-section audit

Legend: **S** = safety-essential (keep), **O** = over-restrictive
(relax), **D** = delegates authority (good), **G** = gates every
action (bad), **A1** = A1-specific operational, **GLOBAL** = any
agentic project.

| § | Lines | Topic | Verdict |
|---|---|---|---|
| Document authority | 7–8 | source-of-truth order | **S, keep** |
| Critical safety | 10–16 | PII, git, secrets, subagents | **mostly S**; line 15 ("separate commits") and line 16 qualifier ("when delegation is authorized") are **O** |
| Autonomous delivery | 18–45 | routine work, parallelism, single delivery report | **mostly D**; lines 36–37 ("avoid concurrent edits") and 41–42 ("record four things separately") are **O**; line 39 ("preserve 34 catalog") is **G** in practice |
| Routine Git delivery | 47–76 | standing authorization, scope review, push | **mostly D**; line 67–68 ("exported snapshot") is **O** |
| Workspace + host boundary | 78–89 | repo-only workspace, subagent path assignment | **D in spirit**; line 89 ("exact in-project path") is **O** |
| Task + validation discipline | 91–112 | real-data default-deny, Git-object validation, MigrationExecutor | **mostly S**; lines 99–101 ("audited without copying sensitive values into logs") are **O** as prose |
| Environment + commands | 114–141 | Python/venv, `A1_PRIVATE_DIR` | **S, keep** |
| A1 production pipeline | 143–155 | canonical scripts, hard rules | **mostly S**; line 150 ("preserve `output/provisional/`") is **O** |
| AI provider + cost | 157–161 | free-tier only | **S, keep** |
| Skills + scope | 163–171 | a1-pdf-production (ready), market-research-evidence (experimental), M2 portal | **mostly D**; market-research gate (165–170) is **G** |
| A1 frameworks / Section 5 / PDF | 173–212 | single source of truth for rendering | **S, keep** |
| Script naming | 214–222 | style | **keep** |
| Git remotes | 225–232 | GitHub-only | **S, keep** |

The section that needs the most surgery is **Critical safety**
(lines 10–16) plus the delegation prose in **Workspace + host
boundary** (line 89) and **Task + validation discipline** (lines
99–101). The remainder is mostly fine.

---

## 2. Twelve concrete relaxations

Each item: line, current text, problem, proposal. Items are ordered
by safety impact (smallest blast radius first).

### R-01 (L12) — `.history-remediation/` rule

> "Treat `.history-remediation/` as sensitive too."

**Problem.** Either the directory is gitignored and the rule is
redundant, or it is not and the rule is an unenforceable hint.

**Proposal.** Move `.history-remediation/` to `.gitignore`; remove
the AGENTS.md line. If kept, restate as a concrete action:

> "Never read files under `.history-remediation/` from a planning
> or A1 context; the directory holds historical rewrite artefacts
> that may contain secrets and require operator review before
> re-introduction."

### R-02 (L15) — "separate commits" rule

> "Keep real-data operations, planning/docs, A1 code, and portal code
> in separate commits."

**Problem.** Forces N commits where one is reviewable via
`git diff --stat`. Multiplies commit count without proportional
safety gain.

**Proposal.** Relax to separate **PRs / batches**:

> "Keep real-data operations, planning/docs, A1 code, and portal
> code in separate PRs (or separate commit batches on the same
> PR). Intermingled changes within one commit are reviewable via
> `git diff --stat`."

### R-03 (L16) — "Subagents … when delegation is authorized"

> "Subagents may research, implement, test or review explicitly
> assigned non-PII scopes when delegation is authorized."

**Problem.** "When delegation is authorized" is itself a round of
authorization that bottlenecks subagent use.

**Proposal.** Replace with an **allow-list** of directory scopes:

> "Subagents may research, implement, test or review in any of:
> `plans/`, `docs/decisions/`, `docs/research/`, `docs/architecture/`,
> `tests/fixtures/synthetic/`, `scripts/` (excluding `a1_*` /
> `finalize_a1.py` / `generate_provisional_a1.py` / `a1_quality_gate.py`).
> Authorization rounds are required only for paths under
> `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`, `employees/`,
> `output/`, `runtime/portal/`, `secrets/`, `.env`."

### R-04 (L36–37) — "Avoid concurrent edits"

> "Use parallel independent reads/tests where safe. When delegation
> is authorized, give agents exact non-PII file scopes, acceptance
> commands and expected evidence; primary review remains required.
> Avoid concurrent edits to shared files or shared test databases."

**Problem.** "Shared files" and "shared test databases" forbid what
git already forbids (same-file push) and serializes independent
test runs.

**Proposal.** Narrow to same-file / same-row:

> "Use parallel independent reads/tests where safe. Subagents
> receive non-overlapping file ownership; concurrent edits to the
> same file or same DB row are still rejected. Disposable test
> databases (per-test SQLite, per-process schema) enable parallel
> runs against the same test source tree."

### R-05 (L41–42) — "Record … separately"

> "Record implementation, test acceptance, Git publication and
> deployment separately."

**Problem.** Four parallel records produce stale copies and
contradict the "one current delivery report" rule on L43.

**Proposal.** Combine:

> "One delivery record per checkpoint, with sub-fields for
> implementation, test acceptance, Git publication and deployment.
> Detailed synthetic logs and hash-bound receipts live in protected
> project runtime storage, not in Git."

### R-06 (L67–68) — "exported snapshot" requirement

> "Verify the resulting object and test its exported snapshot as
> required below; a dirty-tree pass is insufficient. If that
> snapshot fails, repair and validate with a follow-up commit before
> pushing."

**Problem.** "Exported snapshot" round-trip duplicates what
`git diff-tree HEAD` already proves and routinely delays trivial
commits.

**Proposal.** Relax:

> "Verify the resulting object via `git diff-tree HEAD` against the
> intended scoped path set; a dirty-tree pass is insufficient. An
> exported snapshot is required only for cross-environment or
> cross-acceptance changes."

### R-07 (L89) — "exact in-project path"

> "Subagents receive no write scope unless an exact in-project path
> is explicitly assigned."

**Problem.** One exact path per subagent forces serial hand-offs
even on disjoint files. Disables the agent-team model this repo
should adopt.

**Proposal.** Allow directory scopes:

> "Subagents receive a directory-scoped write list
> (e.g. `plans/`, `docs/decisions/`) with file-level mutex.
> Per-file explicit assignment remains required for paths touching
> `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`, `employees/`,
> `output/`, `runtime/portal/`, `secrets/`, `.env`."

### R-08 (L99–101) — "audited without copying sensitive values into logs"

> "Real-data access is default-deny by organization, record, role,
> and action. Sensitive reads, exports, approvals, corrections, and
> deletion must be audited without copying sensitive values into
> logs."

**Problem.** Unenforceable as prose. The "without copying" clause
is precisely the rule the model can't verify, so it tends to block
all sensitive reads.

**Proposal.** Replace with a concrete audit log:

> "Real-data access is default-deny. Each sensitive read, export,
> approval, correction or deletion emits one `AuditEvent` row
> carrying `actor_ref`, `op`, `object_ref` (opaque UUID), `content_hash`,
> `occurred_at`. Raw values never enter the audit log; the
> `AuditEvent` model (`portal/release1a/models.py:209-218`) is
> append-only and rejects updates at the ORM level."

### R-09 (L150) — "Preserve the existing `output/provisional/` package"

> "Preserve the existing `output/provisional/` package; do not
> describe it as reproducible or weaken the gate until the operator
> populates per-row `activity_name` ..."

**Problem.** A non-reproducible directory in the live path
indefinitely. Internal tension with L154 ("do not describe as
reproducible").

**Proposal.** Archive and label:

> "Move the 2026-08-29 `output/provisional/` snapshot to
> `runtime/portal/temporary/retained/<uuid>/provisional-2026-08-29/`
> with a `NOT_REGENERATABLE.md` manifest naming the missing fields
> and the operator-action required. New `output/provisional/` is
> empty by default; nothing is published until the gate accepts."

### R-10 (L165–170) — market-research-evidence gating

> "It may become operational only after repeatable Pilot 1 (OSS
> tools) and Pilot 2 (Czech products) runs both pass Plan AC's
> evidence, review, safety, and reproducibility gates; passing
> structural validators or the external benchmark alone is
> insufficient."

**Problem.** Prose form makes the skill effectively un-promotable;
no testable threshold.

**Proposal.** Convert to a checklist:

> "Skill activation requires four recorded gates:
> (1) `pilot1_passed` (OSS-tools run, evidence path);
> (2) `pilot2_passed` (Czech-products run, evidence path);
> (3) `safety_review_log` (operator sign-off);
> (4) `reproducibility_receipt` (re-run produces identical hash).
> Until all four are recorded in
> `planning/approvals.json`, the skill stays experimental."

### R-11 (L34–37) — Internal tension with R-04

Already covered by R-04. No further change needed once R-04 lands.

### R-12 (L89 / Workspace + host boundary)

Already covered by R-07. No further change.

---

## 3. Concrete edit plan for AGENTS.md

After applying R-01 through R-10, the document shrinks from 232 to
**~165 lines**. The structure becomes:

| Section | Lines (target) | Content |
|---|---|---|
| Document authority | ~6 | unchanged |
| Critical safety | ~10 | tighten to gitignore + named-PII-paths |
| Autonomous delivery | ~12 | single delivery record; 34-catalog preserved |
| Routine Git delivery | ~14 | standing auth table; explicit "no force-push" |
| Subagent delegation | ~8 | allow-list (R-03 + R-07) |
| Real-data audit | ~10 | `AuditEvent` schema (R-08) |
| Environment + commands | ~22 | unchanged (Python, venv, A1_PRIVATE_DIR) |
| A1 production pipeline | ~10 | canonical scripts + hard rules; `output/provisional` archived (R-09) |
| AI provider + cost | ~6 | unchanged |
| Skills + scope | ~10 | activation checklist (R-10) |
| A1 frameworks / Section 5 / PDF | ~28 | unchanged |
| Script naming | ~6 | unchanged |
| Git remotes | ~6 | unchanged |
| **Recent Learnings** | ~15 | mirror `openai-cookbook` pattern; post-mortems in-file |

Total target: ~165 lines. Promotes the truly safety-critical prose
("never `git add -A`", "never read real-data paths") into a
**PreToolUse hook** (see §5).

---

## 4. Missing skills the project should adopt now

There are **two skills** today: `a1-pdf-production` (ready) and
`market-research-evidence` (experimental). Four are missing for the
project's actual workflow.

### 4.1 `django-portal-conventions` (proposed)

**Status:** ready (after first review pass).
**Source:** synthesized from `.agents/skills/a1-pdf-production/` +
Django 5.x docs (https://docs.djangoproject.com/en/stable/).

**Why.** Every Django change in this repo touches
`portal/settings*.py`, `portal/release1a/{models,services,document_intake,j4_artifacts}.py`,
`scripts/a1_core.py`, `scripts/finalize_a1.py`, or
`tests/m2/test_release1a_vertical.py`. There is no shared checklist
for:

- `manage.py a1_process_inbox` (the proposed coordinator)
- `select_for_update()` portability across SQLite/PostgreSQL
- `transaction.atomic()` + `F()` patterns for atomic counter
- `STORAGES` setting (Django 4.2+) — not yet used in this repo
- `@no_translations` for batch management commands
- `MigrationExecutor` historical state tests (mandated by `AGENTS.md`)

**Stub SKILL.md frontmatter:**

```yaml
---
name: django-portal-conventions
description: Django 5.x patterns for the prace-v-nemecku portal. Use when writing or reviewing management commands, ORM migrations, services.py, settings modules, or PostgreSQL/SQLite test fixtures. Covers transaction.atomic + select_for_update, STORAGES, command surface, MigrationExecutor transitions.
license: MIT
metadata:
  status: ready
  audience: maintainers
  depends-on: a1-pdf-production
---
```

### 4.2 `postgres-ops` (proposed)

**Status:** ready.
**Source:** synthesized from PostgreSQL 16 docs + the
`@modelcontextprotocol/server-postgres` README
(https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres).

**Why.** The repo's "PostgreSQL target" is gated behind
`real-data-rules.md` §14; today there is no shared checklist for
PostgreSQL-specific deployment. Required items:

- `statement_timeout` per role
- Read-only role for diagnostics
- `pg_dump` / `pg_restore` encrypted backup verification
- Migration history preservation (do not drop `django_migrations`)
- Identifiers in audit logs only (no PII values)

**Stub frontmatter:** status `ready`, audience `maintainers`.

### 4.3 `pii-guard` (proposed)

**Status:** ready (the rules already exist in
`docs/security/real-data-rules.md`; the skill just operationalizes
them for agents).

**Why.** The current `real-data-rules.md` is **prose**; agents read
it once and forget. A skill exposes the rules via the same
`description`-based selection that loads `a1-pdf-production`.

**Body content** (from `real-data-rules.md` §3–§9, condensed):

- Synthetic data only in tests, fixtures, screenshots, prompts
- Default-deny access; named allow-list of permitted ops
- Filenames / paths / URLs never contain names, OP numbers,
  birth dates, contact details
- OCR output is a proposal; confirmed values never silently
  overwritten
- Mode `0700` dirs / `0600` files; `0644` / `0664` not acceptable
- 90-day retention default; document any extension
- External providers receive only the smallest redacted crop
- Czech OP/ZP statutory ban (`§ 15a odst. 2 zák. č. 328/1999 Sb.`,
  `§ 2 odst. 3 zák. č. 329/1999 Sb.`); MRZ / contactless chip data
  must not be read or stored
- 72-hour ÚOOÚ breach notification clock (Art. 33 GDPR)

**Stub frontmatter:** status `ready`, audience `all`.

### 4.4 `git-delivery` (proposed)

**Status:** ready.
**Source:** synthesized from `docs/operations/git-delivery.md` +
the apache/airflow `AGENTS.md` "Boundaries" template
(https://raw.githubusercontent.com/apache/airflow/main/AGENTS.md).

**Why.** The "Routine Git delivery" prose in `AGENTS.md` is currently
the only place that documents how to commit / push. It should be a
skill so the rules surface when the agent is about to act on git,
not at session start.

**Body content** (from `AGENTS.md` §Routine Git delivery + R-06):

- Branch / upstream / worktree inspection before staging
- Explicit non-PII path list; review `git diff --cached`
- `git diff-tree HEAD` validates the resulting object
- Push to existing feature branch only; never force-push
- One delivery record per checkpoint (R-05)
- Authoritative sources replaced only by sources; never by defaults

**Stub frontmatter:** status `ready`, audience `all`.

### 4.5 Skills NOT recommended for adoption

The research surfaced candidates that are **not** a good fit:

- `anthropics/skills/pdf` — covers generic PDF extraction, but the
  A1 form has a 4-page SVG-SOZ §13 structure that requires Czech
  field policy. Lift only the structure-extraction patterns, not
  the skill itself.
- `anthropics/skills/webapp-testing` — Playwright-based; the repo
  already uses `playwright_smoke.py`. Lift patterns, do not import
  wholesale.
- `anthropics/skills/mcp-builder` — useful as a template for the
  project-local MCP server (see §5.4), but not as a skill to add.
- `upstash/context7` skill — install via `npx ctx7 setup
  --opencode` to fetch Django/PG docs on demand; this is an MCP
  server, not a skill.

---

## 5. MCP servers to wire in

The research identified three production-grade, open-source MCP
servers the project can adopt immediately. All three are MIT or
Apache-2.0 licensed and maintained within the last 12 months.

### 5.1 `@modelcontextprotocol/server-filesystem` (top priority)

- **URL:** https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- **License:** MIT
- **Why this one.** Strongest available PII boundary out of the box:
  must-startup require at least one allowed directory; the `Roots`
  protocol replaces args at runtime; `openWorldHint: false`; tool
  annotations flag destructive ops.
- **Configuration:** allowed dirs = repo root **except**
  `a1/`, `scans/`, `evidence/`, `ocr/`, `data/`,
  `employees/scans/`, `output/`, `runtime/portal/`, `secrets/`,
  `.env`. The MCP refuses any path outside the allowed set; this
  becomes the load-bearing enforcement layer for AGENTS.md's
  PII rules.
- **Companion to:** R-08 (real-data audit). The MCP writes only
  into the repo; any "real-data write" attempt becomes an MCP
  permission-deny that the `AuditEvent` row captures.

### 5.2 `github-mcp-server` (canonical, official)

- **URL:** https://github.com/github/github-mcp-server
- **License:** MIT
- **Why this one.** Replaces the archived
  `modelcontextprotocol/servers/src/github`. Official GitHub
  server: repos, issues, PRs, Actions, CodeQL, Dependabot,
  secret-scanning, code-scanning; OAuth preferred; supports
  `--read-only`, toolset allow-list (`--toolsets`), scoped PAT
  best practices.
- **Configuration:** `GITHUB_TOOLSETS="context,repos,issues,pull_requests"`
  for portal work; `code_security,secret_protection` for hygiene;
  fine-grained PAT with `repo + security_events + read:org` only;
  `--read-only` for agent sessions.
- **Companion to:** R-06 (`git diff-tree HEAD` validation);
  R-05 (one delivery record); R-09 (`output/provisional`
  archival).

### 5.3 `@upstash/context7-mcp` (top for docs)

- **URL:** https://github.com/upstash/context7
- **License:** MIT (server) + proprietary index
- **Why this one.** Keeps Django 5.x, PostgreSQL 16, pymupdf,
  django-allauth docs version-correct without sending project
  source anywhere. Two tools: `resolve-library-id`, `query-docs`.
- **Configuration:** Free tier API key in `Authorization` header;
  only library docs flow through.
- **Companion to:** the proposed `django-portal-conventions`
  skill (the skill references Django conventions; context7 fetches
  the current docs on demand).

### 5.4 Optional fourth: a project-local MCP

The research identified a gap that no upstream server fills: a
PII-secure Django-aware server. The minimal prototype is:

```text
prace-v-nemecku-mcp
├── mcp.json (manifest)
└── tools/
    ├── manage.py a1_process_inbox --dry-run
    ├── pytest -q tests/m2/test_release1a_vertical.py
    ├── git ls-files | grep -v -f .gitignore.pii
    └── scripts/validate_agents_md.py
```

This is **not** in scope for the initial consolidation. It belongs
to a follow-up after R-03 / R-07 land and the allow-list is stable.

### 5.5 NOT recommended

- `@modelcontextprotocol/server-postgres` (archived) — useful as
  read-only DB diagnostic, but PostgreSQL access for this project
  is via Django ORM, not raw SQL. Use the Django management
  commands instead.
- `@modelcontextprotocol/server-sqlite` (archived) — same
  reasoning; the synthetic DB is already inside `runtime/portal/`,
  which the filesystem MCP covers.
- `@modelcontextprotocol/server-git` (active ref, early stage) —
  superseded by `github-mcp-server` for portal work; this project's
  git operations are local-only and benefit from being part of the
  filesystem MCP boundary.

---

## 6. Cross-cutting recommendations

Synthesized from the three research passes:

1. **Promote safety-critical lines to a PreToolUse hook.** The
   "never `git add -A`", "never stage PII paths", "never read
   `.env`" rules belong in a deterministic hook, not in prompt
   text. Anthropic's `PreToolUse` with `permissionDecision: "deny"`
   is the canonical pattern.
   (https://docs.claude.com/en/docs/claude-code/hooks)
2. **Add a `Recent Learnings` section to AGENTS.md**, mirroring
   the `openai-cookbook` pattern. Post-mortems stay inside the
   file; agents reading it learn from past mistakes without
   external lookups.
3. **Use the airflow "Boundaries / Ask first / Never" framing**
   for the routine-delivery section (Apache `airflow/AGENTS.md`,
   https://raw.githubusercontent.com/apache/airflow/main/AGENTS.md).
4. **Document the subagent privilege model** explicitly in
   `AGENTS.md`: parent may touch PII; child may not. The model
   docs do not address this; it is a real gap.
5. **Add a "Provider whitelist with last-verified date"**
   sub-section to AGENTS.md so the free-tier policy is auditable.
6. **Skill frontmatter**: add an explicit
   `metadata.status: ready|experimental` field. The opencode spec
   does not define this; this repo should encode it now.
7. **Versioning**: opencode skills lack a version field. Encode
   version in `name` (e.g. `a1-pdf-production-v2`) or in
   `metadata.version`, and document which is canonical.
8. **Audit hook for memory loads** using the `InstructionsLoaded`
   pattern, so the actual loaded `AGENTS.md` is logged per session.

---

## 7. Open questions for the planning agent

1. **Is the `system_worker` capability relaxation in scope?** The
   prior review (`2026-09-08-local-a1-automation-review.md` §4.3)
   noted `system_worker` has an empty capability set; R-07 + the
   `Batch` model proposal would add `system_worker` as a real
   actor. **Recommend:** add an ADR-numbered decision
   (`docs/decisions/ADR-NNN-system-worker-capabilities.md`) before
   any coordinator code lands.
2. **Does R-08 (AuditEvent-only logging) need a hook?** The repo's
   `AuditEvent` model is append-only; the rule "no sensitive
   values in logs" is enforceable if we add a `PreToolUse` hook
   that greps `Bash` argv for known PII patterns before exec.
   **Recommend:** yes; add to the proposed PreToolUse hook.
3. **Is the `output/provisional` archival (R-09) in scope for
   M4 / the consolidation delivery?** The plan should name the
   archival step explicitly. The 2026-08-29 snapshot is already
   in a state that contradicts L150 ("preserve") and L154 ("do
   not describe as reproducible").
4. **Should `pii-guard` and `git-delivery` ship as skills or as
   hook scripts?** Skills load via the same `description`-based
   selector; hooks are deterministic. **Recommend:** skills for
   reasoning (e.g. "what counts as a synthetic fixture?"),
   hooks for enforcement (e.g. "this Bash command would stage
   `a1/...`").
5. **Should we install the three MCP servers now or after
   consolidation?** The consolidation plan
   (`docs/research/2026-09-08-consolidation-plan-feedback.md`)
   keeps one editable codebase. MCP servers are configured per
   developer, not committed; installing them now does not block
   the consolidation. **Recommend:** install now in
   `.opencode/mcp.json`; document in `docs/operations/`.

---

## 8. Concrete next steps

Ordered, smallest-blast-radius first. None of these is implemented
here; this is a planning memo.

1. **Add `docs/operations/mcp-servers.md`** documenting the three
   MCP servers (filesystem, github, context7) with the
   configuration snippets above.
2. **Edit `AGENTS.md`** to apply R-01 through R-10. Target line
   count: 165.
3. **Create `.agents/skills/django-portal-conventions/SKILL.md`**
   from the stub in §4.1. Mark `status: ready` in `metadata:`.
4. **Create `.agents/skills/postgres-ops/SKILL.md`** from §4.2.
5. **Create `.agents/skills/pii-guard/SKILL.md`** from §4.3.
6. **Create `.agents/skills/git-delivery/SKILL.md`** from §4.4.
7. **Update `.agents/skills/a1-pdf-production/SKILL.md`** to add
   `metadata.status: ready` (it is already ready; the field is
   missing).
8. **Update `.opencode/skills/market-research-evidence/SKILL.md`**
   to add `metadata.status: experimental` and the four-gate
   activation checklist (R-10).
9. **Add `.opencode/mcp.json`** (or equivalent) with the three
   servers configured. Document in `docs/operations/mcp-servers.md`.
10. **Add `docs/research/<date>-agents-md-update-diff.md`** with
    the proposed AGENTS.md diff for review before applying.
11. **ADR: `docs/decisions/ADR-NNN-system-worker-capabilities.md`**
    per §7 Q1.

---

## 9. Conclusion

`AGENTS.md` is over-specified for its purpose. The PII / git /
secrets core is correct; the workflow prose is over-restrictive.
Twelve targeted relaxations shrink the file to ~165 lines and
enable parallel subagent work without losing the safety posture.

The skill gap is small but real: four skills (`django-portal-conventions`,
`postgres-ops`, `pii-guard`, `git-delivery`) replace the prose that
should never have been in `AGENTS.md` in the first place. Three
MCP servers (filesystem, github, context7) provide the
enforcement layer that prompt text cannot.

Together these changes keep the project's safety stance, remove the
friction that bottlenecks progress, and give the agent team a
working toolkit. None of this changes parent plan statuses,
catalog entries, or activation gates.

No file is modified by this memo.