---
status: historical
superseded_by: plans/2026-08-15-plan-af-free-model-evaluation.md, plans/2026-08-12-plan-e-architecture-proofs-and-adr.md, plans/2026-08-12-plan-g-german-market-and-competitors.md
date: 2026-08-11
note: "Historical — superseded by Plans AF, E, G (2026-08-12/15). Do not execute."
---

# Plan C — OpenCode: parallel product, market and architecture research

> **Status: Superseded/incomplete.** The requested research package was not completed to this plan's quality bar. Follow-up research is split into Plans E–J in [`INDEX.md`](INDEX.md); reviewed findings are summarized in [`../docs/research/2026-08-12-research-review-and-plan-update-report.md`](../docs/research/2026-08-12-research-review-and-plan-update-report.md).

> Saved from the "Proposed Plan" (Prompts for Kilo Code and OpenCode) on 2026-08-11.
> Execution order position: **Step 4** (OpenCode research). Report: `reports/2026-08-11-report-plan-c.md`.

## Objective

Research a multilingual recruitment/job-operations platform for Czech workers
taking jobs in Germany. Research/documentation task only — do not implement the
customer web application yet.

Use subagents extensively. At minimum create independent workstreams for:
(1) personas, workflows and product requirements; (2) Czech/German competitor
analysis; (3) job feeds, RSS, APIs and syndication; (4) open-source platforms
and boilerplates; (5) GDPR, document security and consent; (6) Facebook/
Instagram/social automation; (7) dashboard, budgeting and operational analytics;
(8) architecture, deployment and cost comparison; (9) independent
evidence/quality audit.

Cost policy (see `AGENTS.md`): the Codex subscription is the only authorized
paid AI access. Any AI/model usage in this research or in the recommended
architecture's automation must be free-only (verified zero-cost at execution
time; OpenRouter `:free` or explicitly free zero-cost router; never purchase
credits, enable billing or use a paid fallback). Job-feed partner fees and
hosting are product/data costs, separate from the AI model budget. A litellm
gateway may run on the host and is out of scope (owned by other agents/projects).
Use Context7 MCP for up-to-date library/provider docs where configured; otherwise
official docs with recorded URL + access date.

Use relevant research skills. Browse current official websites and primary
documentation. For technical claims prefer official documentation and original
GitHub repositories. Record access date and direct URL for every source.

## Product to research

Multilingual recruitment/job-operations platform for Czech workers in Germany.

Potential employees must be able to: browse German job offers; filter/search
offers; leave a contact request; reserve/apply directly; upload OP and ZP
securely; provide email and phone; record availability and preferred dates; add
notes; see application/reservation history; understand consent and
document-retention terms.

Customer/recruitment operator must be able to: create and manage current jobs;
archive and search job history; manage Czech employees/candidates; manage German
partner companies; track applications, reservations, documents and status
history; schedule employee availability and job assignments; see operational and
budget/cash-flow dashboards; forecast planned versus actual revenue/costs; audit
who changed or accessed sensitive records; export operational reports.

German partner companies must be able to: create and edit job offers; specify
capacity, dates, location, pay and requirements; review supplied candidates
subject to permissions; update fulfillment/status; communicate with the operator;
view history for their own company only.

## Market and competitor research

Research leading relevant products in Germany and Central Europe: large German
job portals; temporary-work/recruitment platforms; cross-border recruitment
services; job reservation/shift platforms; ATS/CRM products serving staffing
agencies; portals focused on construction, logistics, manufacturing and trades.

For each competitor capture:
`name,url,countries,target_segment,job_model,application_flow,candidate_profile,
partner_portal,document_upload,scheduling,messaging,pricing_if_public,API,
RSS/XML/feed,posting_integrations,social_features,strengths,weaknesses,
relevance,source_date`.

Do not claim an API/RSS feed from search snippets. Verify it in official
documentation. Distinguish: public supported API; partner/private API; RSS/XML
feed; structured data only; no verified integration; scraping prohibited/unclear.

Also investigate EURES and Bundesagentur für Arbeit/Jobsuche official integration
possibilities and applicable terms.

## Open-source and boilerplate research

Search current GitHub repositories and official project sites for reusable:
job-board platforms; applicant-tracking systems; staffing/recruitment CRMs;
headless CMS/admin dashboards; secure document portals; booking/availability
systems; workflow engines; notification systems; financial dashboards; role-based
B2B portals; audit-log implementations.

For every serious candidate capture:
`repository,official_site,license,commercial_restrictions,last_release,
last_commit,contributors,stars,open_issues,security_posture,stack,
localization,RBAC,multi_tenant,API,webhooks,document_storage,calendar,workflow,
deployment_complexity,estimated_fit,major_gaps`.

Reject abandoned, unclear-license or insecure-looking candidates from the
recommended shortlist, but document why.

## Social automation

Research current supported options for automating job promotion to Facebook and
Instagram: Meta Graph API and permissions/review requirements; Facebook Pages
posting; Instagram professional-account publishing; scheduling and reusable
templates; link/UTM tracking; approved third-party tools; n8n, Make and similar
automation options; Buffer/Hootsuite-class services; rate limits, token lifecycle
and policy restrictions; what cannot be automated safely or legally.

Do not recommend personal-account browser automation or ToS-violating bots.

## Security and GDPR

Research and document requirements for: OP/ZP uploads; lawful basis and explicit
consent; purpose limitation; data minimization; retention/deletion; candidate
data export; access logging; encryption in transit and at rest; malware
scanning; signed URLs; role separation; German partner access; backups; breach
handling; EU hosting/data residency; processor/subprocessor agreements.

Flag legal conclusions requiring Czech/German counsel.

## Architecture options

Compare at least these implementation strategies:

- A. custom application with managed backend/services;
- B. headless CMS/admin platform plus custom candidate frontend;
- C. open-source ATS/CRM extended with custom job portal;
- D. ERP/CRM-centered solution with recruitment modules;
- E. staged hybrid MVP.

For each option estimate: time_to_MVP, customization, security_risk, GDPR_effort,
operating_cost, developer_complexity, vendor_lock_in, multi_tenant_fit,
workflow_fit, document_fit, social_fit, future_scalability.

Use a 0–5 scoring scale. Default weights: workflow/product fit 20%, security/GDPR
20%, implementation speed 15%, maintainability 15%, integration/API quality 10%,
operating cost 10%, extensibility 10%. Produce sensitivity analysis showing
whether the winner changes when cost or speed receives double weight.

## Required outputs

Create a `research/` directory containing:
`00-executive-summary.md`, `01-personas-and-workflows.md`, `02-competitor-matrix.csv`,
`03-job-feeds-api-rss.md`, `04-open-source-shortlist.csv`, `05-social-automation.md`,
`06-security-gdpr.md`, `07-architecture-options.md`, `08-cost-and-delivery-estimates.md`,
`09-source-register.csv`, `10-open-questions.md`, `DECISION_INPUTS_FOR_CODEX.md`.

Use Mermaid diagrams for: candidate journey; German partner job-submission
journey; operator fulfillment workflow; permissions/data-access boundaries;
proposed system context; document lifecycle; job-to-social-publication flow.

`DECISION_INPUTS_FOR_CODEX.md` is the primary handoff for subsequent Codex
planning. It must contain: verified current repository capabilities; recommended
MVP and excluded v1 features; top three architecture approaches; scored
comparison and sensitivity result; top reusable projects/services; buy/build
recommendations by subsystem; recommended job-feed strategy; recommended
social-publication strategy; recommended hosting/data-residency approach;
required roles and permission matrix; proposed domain entities and relationships;
external integration inventory; security/privacy requirements; estimated MVP
phases, effort ranges and recurring costs; technical risks; product risks; legal
questions; every unresolved decision Codex must ask the user; evidence confidence
per recommendation.

## Quality bar

- Every unstable/current claim has a direct source and access date.
- GitHub metrics are gathered at research time.
- Official sources outrank blogs and affiliate comparisons.
- Marketing claims are labeled as vendor claims.
- Each recommendation cites at least two relevant sources where practical.
- A final audit subagent checks source coverage, scoring arithmetic and contradictions.
- Research must compare enough options to establish market coverage.
