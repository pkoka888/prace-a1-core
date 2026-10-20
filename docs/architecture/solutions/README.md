# Architecture solutions — index

Status: HEAD `9a11260` (2026-09-20). Each report is a `*-architecture-solution.md`
per requested surface; extra solutions carry a variant suffix.

| Report | Answers |
|---|---|
| `site-fo-architecture-solution.md` | FO = static placeholder; served target open; Release-2 boundary |
| `site-bo-architecture-solution.md` | BO J1–J4 portal: routes, services, models, auth, storage |
| `scan-process-architecture-solution.md` | `scans/` → `document_core` → intake → BO review chain |
| `ocr-canonical-architecture-solution.md` | RapidOCR primary + Tesseract fallback + human confirmation |
| `ocr-variants-architecture-solution.md` | Local vs vision-LLM vs Paddle vs LangGraph; combination recommendation |
| `a1-canonical-overlay-architecture-solution.md` | Canonical `a1_core` overlay chain + §5 policy + storage contracts |
| `a1-variants-architecture-solution.md` | All 6 A1 paths (`-overlay/-placeholder/-incremental/-jansa1/-dbdraft/-orchestrated`) + disposition |
| `a1-topic-data-architecture-solution.md` | A1 data architecture as six topics with one owner each (certificate, person, employer/role/situation, activity, institution, provenance) + the employer-as-organization decision |

Authorities reused (linked, not copied): `AGENTS.md`, `roadmap.md`,
`docs/architecture/{A1_FRAMEWORKS,readme-a1-forms,project-directory-map}.md`,
`docs/architecture/release-1a-*.md`, `.agents/skills/a1-pdf-production/SKILL.md`,
vision/free-model research, `scripts/a1_discover.py` inventory.

Known limitations (all reports): synthetic-only evidence; served-FO, intended-target
PostgreSQL acceptance, Jan acceptance, and backup/restore remain open per roadmap;
official A1 issuance is out of v1 scope.
