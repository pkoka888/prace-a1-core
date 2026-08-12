# Plan C — Decision Inputs for Codex

> **Status: Historical/incomplete — do not execute.** Plan C was superseded by
> the active plans in `plans/INDEX.md`. Retained as provenance only.

> STATUS: scaffold. Privacy remediation and the A1 release gate must pass before
> this research is finalized. Items marked `[RESEARCH]` need Codex to complete with
> primary sources (official docs, provider terms) and access dates. No employee PII
> and no paid API fallback are used in this research.

## 1. Personas (product/market)

- **Candidate (Czech job-seeker / self-employed):** needs a clear, confirmed A1
  copy and plain-language status. Must never see other candidates' data.
- **Czech operator:** runs issuance, reviews scanned identity documents, approves
  release. Least-privilege; auditable actions only.
- **Tenant-scoped German partner company:** receives only its own candidates'
  confirmations; cannot see cross-tenant data.

## 2. Competitors / references `[RESEARCH]`

- Compare 2–3 EU A1/E101 issuance assistants and form-filling SaaS.
- Inputs: feature set, data-residency posture, pricing model, openness of APIs.
- Record source URL + access date per competitor.

## 3. Job-feed and social publishing terms `[RESEARCH]`

- Distinguish **consuming** (reading) vs **posting** (publishing) for each
  platform (e.g., official job boards, LinkedIn, social). Verify current API
  availability and ToS.
- Only integrate channels with verified, permissioned APIs. No scraping or
  browser bots where permission is unclear. Record URL + access date.

## 4. Open-source shortlist `[RESEARCH]`

- PDF: pypdf / reportlab (already used); consider WeasyPrint for HTML→PDF if a
  web layer appears.
- OCR: RapidOCR v3 (selected in pivoting plan) — confirm license and model
  redistribution terms.
- Object storage: MinIO or a EU-hosted S3-compatible store for PII documents.
- Record license + access date for each.

## 5. GDPR counsel questions (draft, for Czech/German counsel)

- Controller vs processor roles for operator vs German partners.
- Cross-border transfer basis (CZ→DE) for identity documents and A1 artifacts.
- Retention/deletion lifecycle for OP/ZP scans and generated A1 forms.
- Lawful basis for storing scans; subject-access and erasure handling.
- Whether recruitment/identity-document collection is necessary and proportionate.
- These are **questions**, not legal conclusions. Route to counsel.

## 6. Cost model (draft)

- One-time: remediation, history rewrite, QA harness, font bundling.
- Recurring: restricted storage, hash/audit compute, model calls (free-tier only
  per AI policy), optional human review.
- No paid LLM fallback; Codex subscription is the only authorized paid AI access.

## 7. Architecture comparison (draft ADR)

Scored 1–5 (higher better) on: privacy/least-privilege, reproducibility,
tenant isolation, operability, cost.

| Option | Privacy | Reproducibility | Tenant isolation | Ops | Cost | Total |
|--------|---------|----------------|-----------------|-----|------|-------|
| A. Bounded internal service (canonical scripts + hash QA) | 5 | 5 | 3* | 4 | 4 | 21 |
| B. Tenant-scoped SaaS (per-org data + object storage) | 5 | 4 | 5 | 3 | 3 | 20 |
| C. n8n orchestration + external storage (no new app) | 3 | 3 | 3 | 2 | 5 | 16 |

\* A becomes 5 with enforced org/record scoping before any web launch.

**Recommendation (draft):** Adopt A as the immediate, privacy-safe baseline
(canonical scripts already exist and are deterministic + hash-verified). Gate any
move to B on the architecture decision record and the missing Plan C research. Do
not scaffold a frontend/backend until the ADR is reviewed.

## 8. Go/No-go gates before any deployment

- [ ] Privacy remediation + history rewrite verified and force-pushed.
- [ ] A1 release gate green (font bundled+hashed, birth-number checksum, QA
      manifest includes source/code/template/layout hashes).
- [ ] employee_multi_state checkbox geometry resolved (or kept disabled).
- [ ] 11 records have reviewed Section 4 fields; promotion evidence present.
- [ ] ADR reviewed; no public URLs for PII; short retention/deletion lifecycle.
