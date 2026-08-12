# Agent Guidelines — Práce v Německu

## Authority and conflict order

When instructions disagree, use this order:

1. `AGENTS.md` for agent safety, workspace, privacy, cost, Git, and operating rules.
2. `docs/security/real-data-rules.md` for real-data handling and activation.
3. The canonical A1 workflow READMEs and `.agents/skills/a1-pdf-production/`
   for current A1 production.
4. Approved ADRs and approved decision briefs for settled decisions.
5. `roadmap.md` for milestone order and current product stage.
6. `prd.md` for product outcomes, scope, and open product questions.
7. `plans/INDEX.md` and active dated plans for bounded work.
8. Research and prototypes for evidence and visualization only.
9. Historical/superseded documents for context only; never execute them.

Planning navigation: `docs/decisions/decision-register.md` records decision state;
all ADRs live in `docs/decisions/` as `ADR-NNN-short-title.md`; Plans Q and R own
repository remediation and A1 stabilization. Plan statuses use only the controlled
vocabulary in `plans/INDEX.md`; run Plan M's project-owned planning validation
command once implemented.

An approval in a brief must be reflected in the relevant higher-level authority.
Research, prototype placement, or historical text never silently changes policy.

## Start every task

1. Read this file, `roadmap.md`, and `plans/INDEX.md`; then read only the active
   plan, decision, workflow, and skill relevant to the task.
2. Inspect `git status`, the current branch, and overlapping changes before edits.
3. Classify the request as research, decision preparation, implementation,
   A1 production, infrastructure, or Git/history work. Do not mix these scopes.
4. Confirm whether inputs are synthetic or real. Use synthetic data unless the
   real-data policy and explicit task scope authorize otherwise.
5. State which skill is being used. If no skill applies, follow the active plan
   rather than inventing a new workflow.

## Research, decisions, and visual-first planning

- Inspect the repository before asking Pavel or Jan discoverable questions.
- For substantial independent research, use bounded lower-cost subagents where
  available. Give each a question, source quality, cost/privacy constraints, and
  no-write scope by default. The primary agent validates and integrates results.
- Research current primary/official sources for unstable, legal, financial,
  security, provider, library, or market claims. Record source and access date.
- Before implementation of a substantial workflow, prepare recommended variants
  and synthetic examples in the living visual cockpit. Obtain annotation, record
  the decision, then update PRD/roadmap/plan/ADR before code.
- The cockpit is a derived presentation layer. Its future structured catalog and
  all views must link to authoritative sources; visual cards cannot own policy,
  requirements, status, or approval.

## Agent and skill boundaries

- Subagents are research/analysis workers unless given an explicit in-project
  path and bounded write scope. They never receive scans, employee datasets,
  `.env`, credentials, or unredacted A1 artifacts.
- Only the primary agent integrates subagent work, changes authoritative docs,
  edits real employee data, or performs Git publication actions.
- Skills encode repeatable operational procedures, deterministic scripts, and
  validation contracts. Plans encode one-time discovery or implementation work;
  docs encode domain decisions and references; production logic stays in source.
- Keep `.agents/skills/a1-pdf-production/` as the only active project skill until
  another workflow repeats and has stable commands and acceptance tests.
- Do not create skills for one-off research, interviews, legal analysis, an ADR,
  Git-history remediation, or temporary cleanup.
- Proposed future skills are governed by Plans L and M: a planning-cockpit skill
  after catalog generation is stable, and a portal-development skill only after
  the Django scaffold and its test commands exist.

## Git and change safety

- The current worktree may contain concurrent user/agent changes. Never discard,
  reset, checkout over, reformat, or broadly stage unrelated work.
- Never use `git add -A`, `git add .`, wildcard staging, or force-add. Stage an
  explicit reviewed list of non-PII paths and inspect `git diff --cached`.
- Keep documentation/planning, A1 code/config/tests, portal code, runtime-data
  operations, and history remediation in separate commits and reviews.
- Do not commit or push unless explicitly requested. Never force-push, rewrite
  history, change visibility, create tags/releases, or delete branches without a
  separately approved procedure and exact remote targets.
- Before any commit or push, run relevant tests, `git diff --check`, an internal
  link/status check for docs, and PII/secret checks over staged content.
- Keep `a1/`, `scans/`, `ocr/`, `evidence/`, `output/`, `runtime/`, `secrets/`,
  `.env`, and other real-data paths ignored and unstaged. Do not create archives
  or backup copies as a workaround.
- Historical documents stay in place with a non-executable banner until a
  separate reference/link audit authorizes moving or deleting them.

## Workspace Boundary

- The only persistent project workspace is `/var/www/prace-v-nemecku.tvoje.info` and its subdirectories. Create, edit, generate, archive, or retain project files only inside this root.
- Do not create project artifacts under `/root`, `/home`, `/srv`, another repository, or any other host path. Names such as `/root/arch_options` shown by the collaboration system are logical agent task identifiers, not filesystem locations.
- `/tmp` may be used only for disposable, non-PII intermediate files that are deleted or allowed to expire during the same task. Never place scans, employee data, A1 artifacts, credentials, durable backups, or deliverables in `/tmp`.
- Reading system configuration outside the project is allowed only when needed for non-mutating diagnostics. Writing outside the project requires explicit user approval and must be performed by the responsible sysadmin when it concerns host services, system databases, certificates, or off-server backups.
- Subagents are research/analysis workers by default. Give them an explicit in-project path and write scope before authorizing file edits; otherwise they must return findings to the primary agent without creating files.
- The primary agent owns integration: validate subagent findings, preserve concurrent work, and place accepted outputs in the appropriate project subdirectory.

## The Canonical Pipeline
1. **Reviewed inputs**: The current provisional cohort is the nine reviewed rows in
   `$A1_PRIVATE_DIR/a1/review.csv` plus Pavel Kašpar and Rudolf Kotľár in
   `config/a1_provisional.json`. These sources must resolve to 11 unique employee IDs.
   **Operational inputs are resolved exclusively through the `A1_PRIVATE_DIR`
   environment variable.** The repository itself is private, so the operational
   inputs now live *inside* the repo at the repo-root directories `a1/`, `scans/`,
   `evidence/`, and `ocr/`, which are listed in `.gitignore` and never committed. Set
   `A1_PRIVATE_DIR` to the repository root (e.g. `export A1_PRIVATE_DIR="$(git rev-parse --show-toplevel)"`)
   so those in-repo gitignored directories serve as the inputs. Canonical commands
   fail closed when `A1_PRIVATE_DIR` is unset; there is no tracked fallback. The
   legacy `private/a1_final_review.csv` copy inside the repo has been removed and must
   not be reintroduced.
2. **Institution enrichment**: Resolve each row's `institution_profile` from `config/institutions/`. Treat the listed office contact as provisional unless OSSZ confirms that person as the authorized signatory.
3. **Form composition**: `scripts/generate_provisional_a1.py` reads the reviewed inputs and uses data/profile helpers from `scripts/finalize_a1.py`.
4. **Rendering**: `scripts/a1_core.py` renders the form with `templates/a1_background.pdf` and the field/page/checkbox definitions in `config/a1_layout.json`.
5. **Provisional publication**: Generate through a staging directory and atomically publish the complete review set to `output/provisional/` with its manifest and checklist.
6. **Visual review**: Render fresh previews in `output/provisional-previews/`, bind them to PDF hashes, and verify all three pages for every person.
7. **Approval**: `validated_by_user=1` and authoritative certificate/signatory evidence are required before promotion to `output/pdf/`.

The legacy `data/a1_forms/`, `templates/a1_clean_background*.pdf`, former `a1_form_overlay.pdf`, `config/a1_field_coords.json`, and `config/a1_checkbox_coords.json` artifacts are not the active provisional production path. Do not silently switch to them. Any template/layout migration must update this document and pass visual regression tests first.

## Privacy Rules

`docs/security/real-data-rules.md` is the authoritative operational policy and the
single real-data activation gate. Agents must enforce these invariants:

- Use real data only for a recorded worker, assignment, A1, rights-request, or
  security purpose. Keep tests, docs, screenshots, prototypes, issues, and agent
  prompts synthetic.
- Keep real data only in designated gitignored project directories. Never commit
  or force-add it, expose it through public URLs, or put it in `/tmp`.
- Default-deny access by organization, record, role, and action. Audit sensitive
  reads, downloads, exports, corrections, approvals, and deletions without
  copying sensitive values into the audit message.
- Treat OCR and external-model output as proposals. A logged-in authorized human
  must correct or confirm values before they become authoritative.
- Do not send full scans, A1 artifacts, or employee datasets to external models.
- Require a retention-review date; the pilot default is 90 days. Delete expired
  source and derived data or record a justified extension/legal hold.
- Do not create ad-hoc backup copies of real data. Git is not a backup for
  gitignored files or the database; proceeding without backups is an explicitly
  accepted durability risk, not permission to duplicate PII.

## AI Provider, Model and Cost Policy

### Authorized paid access

- The only authorized paid AI service is the existing Codex subscription,
  currently paid at approximately USD 100 per month.
- Codex subscription models must be accessed through the Codex environment.
- The Codex subscription does not authorize OpenAI API usage and does not provide
  an API spending budget.
- Do not use `OPENAI_API_KEY` for paid API requests, even if that variable exists.

### Free API providers

API credentials may exist in `.env` for providers including OpenRouter, Groq,
Cerebras, DeepSeek, Fireworks, NVIDIA, SambaNova, Z.ai, OpenCode and related
services.

- These credentials authorize only models/endpoints that are free at execution
  time and remain within the provider's free quota.
- Never infer authorization for paid usage merely because an API key exists.
- Verify the selected model's current price and free-tier eligibility before use.
- For OpenRouter, the selected model ID must end exactly with `:free`, or use an
  explicitly free router whose returned model is verified as zero-cost.
- Other providers may use different free-model naming; verify their official
  pricing or API metadata instead of assuming naming conventions.
- If cost cannot be verified as zero, do not make the request.
- Never enable billing, purchase credits, accept a paid trial conversion or use
  an automatic fallback that can select a paid model.
- Historical reports suggesting an OpenRouter credit purchase are advisory only
  and are superseded by this policy.

### Provider selection and fallbacks

1. Use deterministic/local processing when it can solve the task.
2. Use available free provider quotas for work that genuinely benefits from a
   model.
3. Discover currently available free models at runtime where supported.
4. Prefer the best suitable free model, not a hardcoded stale model ID.
5. On quota exhaustion, HTTP 429, unavailable model or provider failure:
   - log the provider, model, status and retry timing;
   - never log credentials or authorization headers;
   - try another verified-free configured provider;
   - defer remaining work if no free provider is available.
6. Rate limits may slow execution but must never trigger a paid fallback.

### Privacy with external models

- Treat scans, identity documents, generated A1 forms and previews as PII.
- Send only the smallest necessary crop or redacted payload to an external model.
- Do not send full OP/ZP scans when local OCR or a cropped field is sufficient.
- Never include API keys, unrelated employee data or `.env` contents.
- Record which provider/model processed PII, the purpose and the execution date.
- External model output is untrusted and must pass deterministic validation and
  human review before modifying authoritative employee data.

### Infrastructure notes

- A litellm gateway may be running on the host; it is owned and maintained by
  other agents/projects and is out of scope for this repository's agents. Do not
  fix, restart or reconfigure it.
- Context7 MCP (`@upstash/context7-mcp`) is the preferred mechanism for
  up-to-date library/provider documentation where it is configured (e.g. Kilo
  Code). In sessions where Context7 is not available, use official docs and
  primary repositories and record URL + access date.

## Authoritative Data Sources
1. **Current reviewed identities**: resolved from `$A1_PRIVATE_DIR/a1/review.csv`
   (the former repo-local `private/a1_final_review.csv` is no longer a tracked
   input). These inputs live in-repo under the gitignored `a1/`, `scans/`, `ocr/`,
   and `evidence/` directories (see `.gitignore`); set `A1_PRIVATE_DIR` to the repo
   root so they resolve.
2. **Current additional identities and provisional issuance policy**: `config/a1_provisional.json` for Pavel Kašpar, Rudolf Kotľár, per-person issue dates, provisional IDs, activity, and status.
3. **Institution profiles**: JSON files in `config/institutions/`, including the source URL and access date. An office director/contact is not automatically an authorized A1 signatory.
4. **Normalized source and validation references**: `$A1_PRIVATE_DIR/a1/employees_normalized.json`, `config/employee_schema.json`, and `config/address_enrichment.json`. They support reconciliation but do not override a later explicit operator correction in the    reviewed CSV. The normalized source now lives under `A1_PRIVATE_DIR` (in-repo,
   gitignored) and is never committed.
5. **Active provisional rendering**: `templates/a1_background.pdf` with `config/a1_layout.json`.
6. **Employer profiles**: Files in `$A1_PRIVATE_DIR/evidence/` (formerly `data/employer_profiles/`) are authoritative only for the employer they name and must never supply another person's issuance data.

## Profile Logic
- **Employee Profiles**: Construct current provisional profiles from reviewed CSV rows plus the two explicit additional records. Preserve source provenance for every value.
- **Employer Profiles**: Use employer JSON only when the row explicitly references that employer.
- **Institution Profiles**: Select `config/institutions/<profile>.json` from the reviewed row's `institution_profile`.
- **Address Validation**: Reconcile against `config/address_enrichment.json`, but preserve explicit scan-backed operator corrections and flag conflicts.
- **Eligibility and status**: The present review copies use the configured self-employed multi-state profile, including 3.4 and 4.1.2. This remains provisional and must not be generalized to future cohorts without source evidence.
- **Dates**: The configured provisional issue date is unique per person, Monday or Thursday, and 61–180 days before the reference date; the provisional coverage period is one year less one day.

## Prohibition on Copying Issuance Data
- **Direct Copy Ban**: Under no circumstances shall issuance data (pre-filled forms, completed A1 forms) be copied directly from one employee record to another
- **Template-Only Approach**: All forms must be generated exclusively from the canonical templates and data sources
- **No Form-to-Form Copying**: Prohibits copying field values from one generated PDF to another
- **Data-First Principle**: All form field values must originate from the authoritative data sources, not from existing forms
- **Audit Trail**: All data transformations must be traceable back to the original authoritative sources

## Verification Gates
1. **Pre-Generation Validation**:
   - Employee data validated against `config/employee_schema.json`
   - Required fields checked for completeness
   - Data types and formats verified

2. **Generation Verification**:
   - Template integrity confirmed before processing
   - Field coordinates validated against template dimensions
   - Population accuracy checked sample-wise

3. **Post-Generation Checks**:
   - Generated PDFs validated for proper field population
   - Visual verification of critical fields (name, address, dates)
   - Checksum validation of generated files
   - Current cohort contains exactly 11 unique three-page PDFs and 33 matching fresh previews
   - No legacy or cross-person values, hidden colored rules, opaque text masks, clipping, overlap, or incorrect checkbox states

4. **Review Process**:
   - Operator review of provisional forms in `output/provisional/`
   - Manual verification of data accuracy and form quality
   - Approval and `validated_by_user=1` required before final placement in `output/pdf/`

5. **Automated Tests**:
   - Unit tests in `tests/` directory validate core functionality
   - Integration tests verify end-to-end pipeline operation
   - Regression testing ensures no degradation of functionality

## Shared A1 Production Skill

- Use `.agents/skills/a1-pdf-production/` for A1 generation, recovery, template/layout work, visual QA, manifests, or client-confirmation packages.
- Keep production behavior in canonical repository scripts; the skill contains operating policy and validation contracts, not a duplicate generator.
- Deterministic geometry/pixel validation and local visual review are authoritative. A free external vision model may provide advisory review only under the provider and privacy rules above.

## Future Product Boundary

The product vision and requirements are maintained in `prd.md`; the authoritative
execution sequence and discovery gates are in `roadmap.md`, with bounded active
plans indexed by `plans/INDEX.md`. These documents guide future work but
do not authorize deployment, external sharing of PII, paid services, or promotion
of provisional A1 artifacts.

- Do not scaffold the portal until Plan E records ADR-001, Plan F confirms the
  first Jan workflow, and the M1 synthetic architecture gates are complete.
- Treat the existing scan/A1 scripts as a bounded internal service candidate, not
  as a public API. Web integration must preserve all provenance, deterministic QA,
  human review and approval gates in this file.
- The future product has three principal access domains: candidates, the Czech
  operator, and tenant-scoped German partner companies. Enforce least privilege,
  organization/record scoping, and explicit document permissions server-side.
- OP/ZP scans and A1 artifacts require protected storage, type/size validation,
  authenticated access, auditable reads/exports, and the retention/deletion
  lifecycle in `docs/security/real-data-rules.md`. Malware scanning and encryption
  at rest are deployment-hardening work selected from measured risk and available
  server support; they do not block scaffolding. Never expose files publicly.
- OCR and external-model output is proposed data only. It must never overwrite an
  authoritative employee field or trigger an issued/final A1 state without
  deterministic validation and human approval.
- Keep append-only audit events for authentication, permission failures, sensitive
  document access, exports, material record changes, approval transitions and
  integration actions. n8n execution history is not a substitute for the product's
  authorization/audit log.
- External job feeds and social publishing require verified current terms and
  supported APIs. Distinguish consuming from posting; do not scrape or use browser
  bots where permission is absent or unclear.
- Use synthetic data in development, tests, screenshots and documentation. Keep
  development, staging and production separated. Incident, retention, deletion,
  and data-subject-request procedures must pass before new real-data portal use.
  Restore procedures are required only if backups are later enabled.
- Legal questions about recruitment, identity-document necessity, retention,
  controller/processor roles, cross-border transfers and financial records require
  Czech/German counsel; do not encode research assumptions as legal conclusions.
