# Project Migration Audit + Plan — 2026-08-30

**From:** primary agent (post-test-realignment session)
**To:** planning agent + Pavel (operator) + sysadmin
**Backup taken:** `/var/backups/sites/prace-v-nemecku.tar` (504 MB,
1842 entries, includes `a1/` `scans/` `output/` `evidence/` real data per
explicit operator instruction "tar actual").
**Status:** 8 commits pushed this session; 497 tests pass; pre-commit
hook blocks quarantined; PII gitignored; `.archive/` convention in place.

This document is the **planning input** for the project simplification +
dashboard-build cycle. It captures (a) the current state, (b) the goal
state the operator described in conversation, (c) the architectural
separation needed, (d) the sysadmin work to deploy it, and (e) the
phased migration path with rollback checkpoints.

The operator's stated goal (verbatim, paraphrased): *"we wanted to
create dashboard where we will be able to generate from scans of op,
zp to /var/www/prace-v-nemecku.tvoje.info/output/provisional a1 forms
and potentially edit workers data out there. I need to simplify whole
process so that it will reflect whole framework we did for generating
a1 forms, just for to be able to do it via web sites for client jan.
We don't want any validations from jan or pavel. We have too much
plans, etc... lets simplify."*

Key constraints from that goal:

1. **Output target is `output/provisional/`** — the existing
   A1-generation pipeline's destination. The dashboard must use it.
2. **Web-based, for client Jan** — replace the CLI / Plan R
   operator-flow with a UI flow.
3. **No Jan or Pavel validation gates** — drop the
   `certificate_reviewed`/`approved_for_pdf`/`validated_by_user`
   blocking flow. Generation runs end-to-end without human approval.
4. **Simplify** — fewer plans, fewer reviews, fewer gates, fewer
   changepackage checks where the dashboard doesn't need them.

---

## 1. Current State Audit

### 1.1 Tracked file distribution (458 tracked files)

| Directory | Files | Role |
|---|---:|---|
| `tests/` | 110 | Test suite (pytest, unittest) |
| `research/` | 89 | Plan AC market research (mostly quarantined) |
| `docs/` | 56 | Documentation: architecture, decisions, ops, plans, prototypes, release-1a, research, security |
| `scripts/` | 38 | A1 generation, validation, research, governance tooling |
| `portal/` | 34 | Django M2 prototype (Jan J1–J4 vertical slice) |
| `plans/` | 31 | 28 plan files + INDEX.md + audits/ |
| `config/` | 27 | A1 layout, institutions, free-model-eval, schemas |
| `cli-docs-update/` | 13 | CLI claim verification reports |
| `workflows/` | 9 | wf-a1, wf-ac, wf-af README + `.archive/` |
| `src/` | 5 | `free_model_eval/` + `invoice_ingestion/` (Plan AD contracts) |
| `.agents/` | 5 | Skill: `a1-pdf-production/` |
| `.opencode/` | 4 | Free-model-eval agents + market-research-evidence skill |
| `prototypes/` | 4 | Architecture prototype (adr001) |
| `planning/` | 4 | Catalog + ADR records (release1a, planning, research, free_model_eval) |
| `templates/` | 2 | A1 background PDF + placeholders JSON |
| repo root | 17 | README, AGENTS, CHANGELOG, prd, requirements, pytest.ini, etc. |

### 1.2 Untracked real-data directories (PII, gitignored)

| Path | Size | Role |
|---|---|---|
| `a1/` | 116 K | CSV review input + cohort.json + employees_normalized.json (PII, gated) |
| `scans/` | 8.6 M | OP / ZP scan JPEGs (PII) |
| `output/` | 608 M | A1 PDFs + previews + 25 stale backup dirs |
| `evidence/` | 40 K | OCR / OCR-suggestion evidence |
| `ocr/` | 100 K | OCR intermediates |
| `data/` | 8 K | Processed-images cache |
| `employees/` | 8 K | Reserved (employees/scans/ gitignored) |

### 1.3 Plans inventory (28 files)

| Bucket | Plans |
|---|---|
| **Architecture / Infra (keep, consolidate)** | E (architecture proofs, completed), L (operating model, active), M (planning cockpit, active), M2 (functional prototype sprint, active), AE (repository workflow, active), E-01 (env CI stabilization, planned) |
| **A1 / Workers (keep, consolidate)** | R (A1 production stabilization, completed; references `/2026/` cohort), Q (history remediation, accepted), AC (accounting automation, active; mostly quarantined output), AD (invoice ingestion foundation, active) |
| **Research / Validation (mostly archive)** | B (opencode cleanup workflows, historical), C (opencode research, historical), D (product research & deployment, superseded), G (German market, active parallel), I (marketing/business validation, superseded), J (data protection & legal, active parallel), P (payroll & finance, active parallel), F (Jan workflow discovery, active), H (UX/UI research, active), N (role/data discovery, active), O (database/transactions, active) |
| **Free-model eval / experiments (gate-quarantine)** | AF (free-model evaluation, active), AF2 (trace repair, blocked), AF2.1 (evidence integrity repair, active), AF2.2 (luna capsule isolation, active) |
| **Historical reference** | 2026-08-11-consolidated-roadmap (historical) |

**Proposed post-simplification set (target: 8 plans total):**

| New plan | Replaces | Status target |
|---|---|---|
| **PLAN-INFRA** | E + L + M + M2 + AE + E-01 | active (single source of truth for architecture, governance, infra) |
| **PLAN-A1** | R + Q | completed (single A1 production source) |
| **PLAN-WORKERS** | F + H + N + O | active (Jan-facing worker data flows) |
| **PLAN-INVOICE** | AD + AC + P (payroll subset) | active (invoice ingestion + accounting; AC stays experimental until Plan AC gates pass) |
| **PLAN-LEGAL** | G + I + J | active (German market, marketing, data protection — all parallel research) |
| **PLAN-FREE-MODEL** | AF + AF2 + AF2.1 + AF2.2 | active (single free-model evaluation track) |
| **PLAN-HISTORY** | B + C + 2026-08-11-consolidated-roadmap + D (superseded) | historical (single archive-style reference) |
| **plans/INDEX.md** | current INDEX.md | updated to list only the 8 plans above |

The remaining plan files move to `.archive/plans/<original-filename>` per
the archive convention. Each move gets a one-line note in CHANGELOG
referencing this audit.

### 1.4 Existing portal prototype (the dashboard starting point)

`portal/release1a/` is a Django 5.2 app with synthetic-only data flow.
**It already does most of what Jan needs:**

- **Models** (`portal/release1a/models.py`): Organization, Membership,
  Worker, Document, OcrProposal, Assignment — all `TenantModel`
  subclasses with organization-scoping.
- **Forms** (`portal/release1a/forms.py`): WorkerForm, DocumentUploadForm,
  OcrConfirmationForm, AssignmentForm, A1PrepareForm, A1ApprovalForm.
- **Views** (`portal/release1a/views.py`): 17 endpoints covering
  worker CRUD, document upload + OCR review, assignment CRUD, A1
  prepare + regenerate + detail, plus a `health` and `dashboard` view.
- **Templates** (`portal/templates/portal/`): 11 full pages + 7 HTMX
  partials, Czech-first.
- **Migrations** (`portal/release1a/migrations/0001_initial.py`).
- **Tests** (`tests/m2/`): 19 tests covering views + review fixes +
  vertical slice; all pass.
- **Settings** (`portal/settings.py`): DEBUG=True, SQLite at
  `db.sqlite3`, LANGUAGE_CODE="cs", LOGIN_URL="/login/",
  M2_SYNTHETIC_ONLY=True.

**What the M2 prototype does NOT yet do, that the dashboard needs:**

1. No URL wiring through the host (`prace-v-nemecku.tvoje.info`
   currently serves `public-site/index.html` placeholder only).
2. No gunicorn / WSGI deployment (no `wsgi.py`, no systemd unit, no
   `/dashboard/` route at the nginx vhost).
3. No integration with the A1-generation scripts
   (`scripts/generate_provisional_a1.py`,
   `scripts/finalize_a1.py`, `scripts/a1_quality_gate.py`).
4. `A1PrepareForm`/`A1ApprovalForm` carry the operator-gate model
   (`certificate_reviewed`, `approved_for_pdf`, `validated_by_user`).
   Per the operator's instruction these should not block generation.
5. No OCR pipeline integration (RapidOCR is in `requirements.txt` but
   the document-upload view only stores the file; it doesn't run OCR
   on the stored bytes).

---

## 2. Goal State — The Jan Dashboard

### 2.1 Functional scope (one screen per capability)

| URL | Capability | Owner | Notes |
|---|---|---|---|
| `https://prace-v-nemecku.tvoje.info/` | Public landing | static | existing `public-site/index.html`; replace with project-status mirror |
| `https://prace-v-nemecku.tvoje.info/login/` | Jan login | Django auth | synthetic-only `django-allauth[mfa]` already in `requirements.txt` |
| `https://prace-v-nemecku.tvoje.info/dashboard/` | Jan home | portal view | list of workers + recent scans + recent A1 cases + "Upload OP/ZP" CTA |
| `https://prace-v-nemecku.tvoje.info/workers/` | Worker list | portal view | sortable, filter by status, link to detail/edit |
| `https://prace-v-nemecku.tvo.info/workers/<id>/` | Worker detail | portal view | identity, residence, employment, documents, assignments, A1 cases |
| `https://prace-v-nemecku.tvoje.info/workers/<id>/edit/` | Worker edit | portal view | **no validation gate; direct save to `a1/`-style local store or `db.sqlite3`** |
| `https://prace-v-nemecku.tvoje.info/workers/new/` | New worker | portal view | form, no validation gate |
| `https://prace-v-nemecku.tvoje.info/scans/upload/` | OP / ZP upload | portal view | drag-drop, accepts JPEG/PNG/PDF; runs RapidOCR local; shows proposals inline |
| `https://prace-v-nemecku.tvoje.info/scans/<id>/` | Scan detail | portal view | original + OCR proposals + "Apply to worker" button |
| `https://prace-v-nemecku.tvoje.info/a1/` | A1 case list | portal view | status per case (draft, generated, downloaded) |
| `https://prace-v-nemecku.tvoje.info/a1/<id>/` | A1 case detail | portal view | preview + "Regenerate" + "Download" + provenance metadata |
| `https://prace-v-nemecku.tvoje.info/a1/<id>/regenerate/` | A1 regenerate | portal view | POST triggers the existing A1 scripts; writes to `output/provisional/`; no human-approval gate |
| `https://prace-v-nemecku.tvoje.info/health` | Health endpoint | portal view | returns 200 + JSON `{status: ok, version: …}` |
| `https://prace-v-nemecku.tvoje.info/ready` | Ready endpoint | nginx | existing nginx config; `return 200 "ready\n"` |
| `https://prace-v-nemecku.tvoje.info/dev/components/` | Dev component catalog | portal view | the M2 `app/dev/component-states/page.tsx`-style scaffold lives here |

### 2.2 What the dashboard does **not** include

- No `pavel_validates=True` gate anywhere; no `approved_for_pdf`,
  `validated_by_user`, `certificate_reviewed` flags blocking generation.
- No "two-person rule" for A1 outputs.
- No manager/admin role separation beyond organization membership
  (already handled by `require_org_membership` decorator).
- No audit-event human review (events are still recorded but not gated).
- No public access (all routes require Jan session).

### 2.3 Data flow on OP / ZP upload → A1 PDF

```text
Jan uploads JPEG at /scans/upload/
   ↓
Django view stores Document (sha256, organization, worker_link optional)
   ↓
RapidOCR runs locally (no API, no paid model)
   ↓
Proposals shown inline via HTMX (no page reload)
   ↓
Jan clicks "Apply to worker" or "Create new worker from this scan"
   ↓
Worker record updated (or created) — no approval gate
   ↓
A1 regenerate button → calls scripts/finalize_a1.py with the new worker row
   ↓
PDF written to output/provisional/A1_<worker_id>.pdf
   ↓
Jan clicks "Download" → serves the file from output/provisional/
```

### 2.4 What stays as CLI / background (not exposed in dashboard)

- `scripts/audit_agent_dirs.py`, `scripts/inventory_repository.py` —
  governance tooling; useful for planning agent but not Jan.
- `scripts/generate_planning_asset.py`, `scripts/generate_research_cockpit.py`
  — visual planning outputs; keep as artifacts.
- `scripts/collect_market_evidence.py`, `scripts/run_collector_*.py`,
  `scripts/capture_research_sources.py` — Plan AC research; only runnable
  when Plan AC gates pass.
- `scripts/run_free_model_eval.py` — free-model eval harness; only
  when an admin explicitly invokes.
- `scripts/a1_quality_gate.py validate / record-review` — visual QA
  for batches; remains a CLI tool because it requires hash-bound review.

---

## 3. Local Framework Separation

The simplified project splits into **three runnable layers** plus the
existing **CLI tools** that the planning agent / operator use.

### 3.1 Layer A — Web dashboard (Django)

- **Path:** `portal/release1a/` (existing).
- **WSGI entry:** new `portal/wsgi.py` (gunicorn target).
- **Settings:** `portal/settings.py` keeps `M2_SYNTHETIC_ONLY=True` for
  local dev; add `prace_v_nemecku.production_settings` for the host
  deployment (DEBUG=False, ALLOWED_HOSTS = ["prace-v-nemecku.tvoje.info"],
  SECRET_KEY from env).
- **Database:** `db.sqlite3` at repo root for local dev; production
  reuses `db.sqlite3` on the host (low-traffic Jan-only deployment).
- **Static:** `portal/static/` (currently inline; collectstatic → `staticfiles/`).
- **Process:** `gunicorn portal.wsgi:application` on 127.0.0.1:8001,
  reverse-proxied by nginx.

### 3.2 Layer B — A1 generation pipeline (CLI / library)

- **Path:** `scripts/a1_*.py`, `scripts/finalize_a1.py`,
  `scripts/generate_provisional_a1.py` (existing).
- **Status:** unchanged. The dashboard calls them via
  `subprocess.run([sys.executable, "scripts/finalize_a1.py", "prepare",
  "--employee", worker_id], check=True)` from the A1 regenerate view.
- **Output target:** `output/provisional/` (per operator instruction).
- **Workdir:** the web view sets `cwd=/var/www/prace-v-nemecku.tvoje.info`
  and inherits `A1_PRIVATE_DIR` env from systemd.

### 3.3 Layer C — Static placeholder + dev components

- **Path:** `public-site/` (existing).
- **Served by:** nginx directly, not Django.
- **Status:** Replace with a project-status mirror that links to the
  dashboard's `/login/` route and shows the latest commit SHA + last
  A1 generation timestamp (read from `output/provisional/` mtime).

### 3.4 Layer D — CLI / background tools (planning agent surface)

- **Path:** `scripts/` (everything except `a1_*` and `generate_provisional_a1.py`
  + `finalize_a1.py`).
- **Status:** remain runnable from the host shell for planning,
  validation, and one-off jobs. Not exposed via the dashboard.
- **Quarantined tools** (`scripts/validate_collector_execution_v12.py`,
  `scripts/run_collector_proposals_v12.py`,
  `scripts/run_ocr_benchmark.py`, `scripts/generate_research_cockpit.py`)
  stay quarantined until their gates pass.

### 3.5 File-reorganization proposal (post-simplification)

```
/var/www/prace-v-nemecku.tvoje.info/
├── AGENTS.md                              # operating model — keep
├── CHANGELOG.md                           # — keep
├── README.md                              # public-facing — keep, refresh
├── prd.md                                 # product reqs — keep
├── requirements.txt + requirements-lock.txt  # keep
├── pytest.ini, .pre-commit-config.yaml    # keep
├── .archive/                              # NEW: see .archive/README.md
├── docs/
│   ├── architecture/   (adr-001*)         # keep — single source
│   ├── decisions/     (ADR-*, register, brief)  # keep
│   ├── operations/    (incl. this audit, unblock reports, sysadmin findings)  # keep
│   ├── release-1a/    (catalog, packet, data-readiness)  # keep
│   ├── research/      (open-decisions + plan reviews + free-model reports)  # keep
│   ├── security/      (real-data-rules)   # keep
│   ├── plans/TODO_TRACKING.md             # archive (superseded by plans/INDEX.md)
│   ├── paddleocr/                         # archive (historical, marked)
│   ├── plans/                             # archive (legacy plan docs)
│   ├── prototypes/                        # keep
│   └── codex-planner-report-*             # archive
├── plans/                                  # simplified to 8 plans + INDEX.md (see §1.3)
├── .agents/skills/a1-pdf-production/        # keep
├── .opencode/skills/market-research-evidence/  # keep (experimental)
├── .opencode/agents/free-eval-*.md           # keep (experimental)
├── config/
│   ├── a1_layout.json, a1_provisional.json   # keep
│   ├── address_enrichment.json, employee_schema.json  # keep
│   ├── institution.json                       # keep
│   ├── institutions/ (10 cities)              # keep
│   ├── cli_verification_claims*               # keep
│   └── free-model-eval/ (schemas)             # keep
├── scripts/
│   ├── a1_core.py, a1_private.py, a1_quality_gate.py, finalize_a1.py,
│   │   generate_provisional_a1.py            # keep (Layer B)
│   ├── pre-commit, validate_change_packages.py, validate_planning.py,
│   │   validate_research_*.py, validate_approvals.py, validate_field_normalization.py,
│   │   inventory_repository.py, audit_agent_dirs.py, generate_planning_asset.py,
│   │   generate_approval_asset.py, generate_research_review_queue.py,
│   │   check_evidence_url.py, check_research_completeness.py,
│   │   check_m2_scaffold_gate.py,
│   │   run_architecture_proofs.py             # keep (governance / M2 gate)
│   ├── list_vision_models.py                  # keep (operator diagnostics)
│   ├── run_collector_fixture.py, run_collector_proposals.py,
│   │   normalize_datasets.py, evaluate_research_field_fixtures.py,
│   │   compare_research_runs.py, score_research_results.py,
│   │   capture_research_sources.py,
│   │   benchmark_groundtruth.py, collect_market_evidence.py,
│   │   create_synthetic_benchmark.py          # keep (Plan AC integrity lane)
│   ├── run_free_model_eval.py                 # keep (Plan AF)
│   ├── run_collector_proposals_v12.py,
│   │   validate_collector_execution_v12.py    # QUARANTINE (Plan AC frozen v1.2)
│   ├── run_ocr_benchmark.py                   # QUARANTINE (Plan AC)
│   ├── generate_research_cockpit.py           # QUARANTINE (Plan AC)
│   └── validate_ocr_proposals.py              # QUARANTINE (deferred per Plan R)
├── src/
│   ├── free_model_eval/                       # keep (Plan AF contracts)
│   └── invoice_ingestion/                     # keep (Plan AD contracts)
├── portal/
│   ├── settings.py, urls.py, wsgi.py (NEW)    # keep
│   ├── templates/portal/                      # keep (12 + 7 partials)
│   └── release1a/                             # keep (M2 prototype → dashboard)
├── tests/                                     # keep
├── workflows/                                 # keep
├── prototypes/                               # keep
├── cli-docs-update/                           # keep
├── planning/                                  # keep
├── templates/                                # keep (A1 background)
├── public-site/                              # REPLACE (project-status mirror)
├── a1/                                       # PROTECTED (PII, gitignored)
├── scans/                                    # PROTECTED (PII)
├── output/                                   # PROTECTED (PII; dashboard writes here)
├── evidence/, ocr/, data/, employees/, reports/  # PROTECTED
├── runtime/                                  # PROTECTED (portal runtime)
├── .history-remediation/                     # PROTECTED (history rewrite workspace)
└── docs/operations/operator-action-plan-2026-08-29.md  # NEW (operator inputs)

ARCHIVE (.archive/) — files moved out per .archive/README.md:
- 25 × output/provisional.backup-* → .archive/output/provisional.backup-*
- 21 × plans/*.md (see §1.3) → .archive/plans/<name>
- docs/plans/TODO_TRACKING.md → .archive/docs/plans/TODO_TRACKING.md
- scripts/a1_core.py.backup, scripts/portal/settings.py.bak
  → .archive/scripts/...
- .history-remediation/* stays in place but gitignored; the audit
  recommend moving to .archive/.history-remediation/ once Plan Q is
  fully closed (separate explicit decision).
- pre-rewrite/codex-unified-a1-core-20260812, pre-rewrite/master-20260812
  local branches remain in git (not in working tree); no action.
```

---

## 4. Sysadmin Deployment Spec (this server, `prace-v-nemecku.tvoje.info`)

### 4.1 Current host state (verified 2026-08-30)

- **OS:** Debian/Ubuntu (systemd `init`).
- **Web server:** nginx running; existing vhost
  `/etc/nginx/sites-enabled/prace-v-nemecku.tvoje.info.conf` listens on
  `192.168.1.62:8098` and serves `public-site/` (placeholder).
- **App server:** none running (the Django M2 prototype is not
  gunicorn-served yet).
- **Python:** `venv/` at the repo root, Python 3.13, deps pinned in
  `requirements.txt` + `requirements-lock.txt`.
- **Host IPs:** `192.168.1.62` (LAN), `100.81.67.93` (Tailscale).
- **Disk free:** 89 G on `/`; `/var/backups/sites/prace-v-nemecku.tar`
  is 504 MB (single full snapshot).
- **Other hosts on this box:** `adi`, `bagrplzen`, `budget`, `budgety`,
  `dev-bagrplzen`, `lukaspitrik`, `mapy`, `marketing`, `metabase`,
  `okamih-cz` — managed by Ansible; do not touch unrelated vhosts.

### 4.2 What sysadmin needs to deploy (post-Phase-4)

1. **Systemd unit for gunicorn** (new file
  `/etc/systemd/system/prace-v-nemecku-web.service`):

   ```ini
   [Unit]
   Description=Práce v Německu web dashboard (gunicorn)
   After=network.target

   [Service]
   Type=simple
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/prace-v-nemecku.tvoje.info
   Environment=A1_PRIVATE_DIR=/var/www/prace-v-nemecku.tvoje.info
   Environment=DJANGO_SETTINGS_MODULE=portal.settings
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/var/www/prace-v-nemecku.tvoje.info/venv/bin/gunicorn \
       --workers 2 --bind 127.0.0.1:8001 --access-logfile - \
       portal.wsgi:application
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

   Then `systemctl daemon-reload && systemctl enable --now
   prace-v-nemecku-web.service`.

2. **Nginx vhost** (replace
   `/etc/nginx/sites-enabled/prace-v-nemecku.tvoje.info.conf`):

   ```nginx
   # Managed by Ansible: prace-v-nemecku-site
   upstream prace_v_nemecku_app {
       server 127.0.0.1:8001 fail_timeout=0;
   }

   server {
       listen 192.168.1.62:8098;
       server_name prace-v-nemecku.tvoje.info;

       client_max_body_size 16m;   # allow OP/ZP uploads

       access_log /var/log/nginx/prace-v-nemecku.tvoje.info_access.log;
       error_log  /var/log/nginx/prace-v-nemecku.tvoje.info_error.log warn;

       add_header X-Content-Type-Options nosniff always;
       add_header X-Frame-Options DENY always;
       add_header Referrer-Policy no-referrer-when-downgrade always;
       add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'" always;

       location = /ready {
           default_type text/plain;
           return 200 "ready\n";
       }

       location = /health {
           proxy_pass http://prace_v_nemecku_app/health;
           proxy_set_header Host $host;
       }

       location /static/ {
           alias /var/www/prace-v-nemecku.tvoje.info/portal/static/;
           expires 30d;
           access_log off;
       }

       location /downloads/a1/ {
           alias /var/www/prace-v-nemecku.tvoje.info/output/provisional/;
           add_header Content-Disposition "attachment" always;
       }

       location / {
           proxy_pass http://prace_v_nemecku_app;
           proxy_set_header Host $host;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_redirect off;
       }

       location ~ /\.(archive|git|env|history-remediation) {
           deny all;
       }
   }
   ```

3. **File permissions** for `a1/`, `scans/`, `output/`, `evidence/`,
   `ocr/`: `chown -R www-data:www-data` on those directories (so
   gunicorn can read scans + write to `output/provisional/`). The
   `db.sqlite3` file needs the same.

4. **Python deps**: `venv/bin/pip install -r requirements-lock.txt`
   (already installed; just ensure no drift).

5. **Static collection**: `venv/bin/python manage.py collectstatic
   --noinput` after deploy.

6. **Migrations**: `venv/bin/python manage.py migrate` after deploy
   (creates the M2 portal tables in `db.sqlite3`).

7. **Health verification**: `curl -fsSL
   https://prace-v-nemecku.tvoje.info/health` should return
   `{"status":"ok",...}`; `curl -fsSL
   https://prace-v-nemecku.tvoje.info/ready` returns `ready\n`.

### 4.3 Firewall / exposure

- Listen on `192.168.1.62:8098` (LAN) only. Public exposure (Tailscale
  or Cloudflare tunnel) is a separate decision and not in scope.
- The host already has nginx vhosts for `bagrplzen.tvoje.info` etc.
  on the same box; sysadmin pattern is consistent.

### 4.4 Backup retention

- Daily full tar to `/var/backups/sites/prace-v-nemecku.tar` (cron or
  Ansible) — already includes real data per operator instruction.
- Retention: 7 daily + 4 weekly + 0 monthly (or per operator choice).
- The tar is **outside the project root** and contains real data; it
  must therefore be stored only on the host's encrypted volume, never
  mirrored to GitHub. (GitHub remote remains authoritative for the
  source tree but does NOT contain the real-data tar.)

---

## 5. Prototype URLs (existing + planned)

| URL | Status | Purpose |
|---|---|---|
| `https://prace-v-nemecku.tvoje.info/` | **Existing placeholder** | public landing (`public-site/index.html`); replace with status mirror |
| `https://prace-v-nemecku.tvoje.info/ready` | **Existing** | nginx `/ready` returns `ready\n` |
| `https://prace-v-nemecku.tvoje.info/health` | **Planned (Phase 4)** | gunicorn health endpoint |
| `https://prace-v-nemecku.tvoje.info/login/` | **Planned (Phase 4)** | Django auth, Jan session |
| `https://prace-v-nemecku.tvoje.info/dashboard/` | **Planned (Phase 4)** | Jan home |
| `https://prace-v-nemecku.tvoje.info/workers/` | **Planned (Phase 4)** | worker list |
| `https://prace-v-nemecku.tvoje.info/workers/<id>/` | **Planned (Phase 4)** | worker detail |
| `https://prace-v-nemecku.tvoje.info/workers/<id>/edit/` | **Planned (Phase 4)** | worker edit |
| `https://prace-v-nemecku.tvoje.info/workers/new/` | **Planned (Phase 4)** | new worker |
| `https://prace-v-nemecku.tvoje.info/scans/upload/` | **Planned (Phase 4)** | OP/ZP upload + OCR |
| `https://prace-v-nemecku.tvoje.info/scans/<id>/` | **Planned (Phase 4)** | scan detail + proposals |
| `https://prace-v-nemecku.tvoje.info/a1/` | **Planned (Phase 4)** | A1 case list |
| `https://prace-v-nemecku.tvoje.info/a1/<id>/` | **Planned (Phase 4)** | A1 case detail |
| `https://prace-v-nemecku.tvoje.info/a1/<id>/regenerate/` | **Planned (Phase 4)** | A1 regenerate (no gate) |
| `https://prace-v-nemecku.tvoje.info/downloads/a1/<filename>` | **Planned (Phase 4)** | A1 PDF download |
| `https://prace-v-nemecku.tvoje.info/dev/components/` | **Planned (Phase 4)** | component-state sandbox |

### 5.1 Local-dev URLs (not exposed externally)

- `http://127.0.0.1:8001/` — gunicorn upstream; never exposed.
- `http://127.0.0.1:41397/` — observed listening on the host; some
  agent tool, not part of this project; do not conflict.
- `http://127.0.0.1:8890/`, `:8891/`, `:19090/`, `:9115/` — also
  unrelated host services; do not conflict.

---

## 6. Migration Plan (phased)

The migration runs in **five phases**, each with a checkpoint and a
**rollback to `/var/backups/sites/prace-v-nemecku.tar`**. No phase
mutates the tar; the tar is the immutable baseline.

### Phase 1 — Audit + archive (this document)

- **Deliverable:** this audit + `.archive/` convention
  + updated `operator-action-plan-2026-08-29.md` with archive instead
  of delete.
- **Checkpoint:** `.archive/README.md` exists; tar exists at
  `/var/backups/sites/prace-v-nemecku.tar`; no tracked files changed
  in this phase (everything is untracked or gitignored).
- **Operator input:** review + sign off on `.archive/README.md`.
- **Rollback:** delete `.archive/`, restore working tree from tar
  if needed.

### Phase 2 — Consolidate plans

- **Action:** move 21 plan files (B, C, D, G, I, J, P, F, H, N, O,
  AF, AF2, AF2.1, AF2.2, 2026-08-11-consolidated-roadmap, AF) into
  `.archive/plans/`; create the 8-plan replacement set
  (PLAN-INFRA, PLAN-A1, PLAN-WORKERS, PLAN-INVOICE, PLAN-LEGAL,
  PLAN-FREE-MODEL, PLAN-HISTORY, plus the existing
  `plans/INDEX.md`).
- **Checkpoint:** `ls plans/` shows 8 plans + INDEX.md; `.archive/plans/`
  contains the 21 archived originals.
- **Operator input:** approve the 8-plan mapping; approve any name
  changes.
- **Rollback:** `mv .archive/plans/* plans/` to restore.

### Phase 2 environment and test validation (verified 2026-08-30)

- **Virtualenv:** `venv/` is the correct environment — AGENTS.md, all scripts,
  and the test suite reference it; `.venv` does not exist in this repo.
  `venv/bin/python -m pip check` reports no broken requirements, and every
  requirement in `requirements.txt` / `requirements-lock.txt` is installed at
  the pinned version (`jsonschema 4.26.0`, `Django 5.2.17`,
  `django-allauth[mfa] 65.19.1`, `django-q2 1.11.0`, `psycopg 3.3.4`,
  `cryptography 50.0.0`, `reportlab 5.0.0`, `pypdf 6.15.0`, `rapidocr 3.9.2`,
  `onnxruntime 1.29.0`, ...). No installation was needed.
- **Planing validator:** `scripts/validate_planning.py` → 24/24 passed on the
  consolidated 34-item catalog.
- **Full test suite:** green in batches (a single block exceeds 5 minutes
  because the Django M2 / release-1A tests cost ~15s each; run in the groups
  below):
  - `tests/test_validate_planning.py` — 36 passed.
  - A1 core/quality-gate/finalize/private (`test_a1_core`, `test_a1_quality_gate`,
    `test_a1_private`, `test_finalize_a1`) — 39 passed.
  - Free-model eval (contracts/events/isolation/preflight/scoring/af2/af21) — 58 passed.
  - `test_comprehensive` + `test_m2_scaffold_gate` + `test_architecture_proof_preflight`
    + `test_validate_approvals` + `test_audit_agent_dirs` + `test_gate1_security` — 45 passed, 1 skipped.
  - Invoice + `test_plan_ac_quarantine` + `test_verify_cli_claims`
    + `test_validate_change_packages` + `test_field_decision_fixtures` — 63 passed.
  - Research suite (collector, proposals, fixture, comparison, evidence, isolation,
    review-queue, benchmark) — 198 passed.
  - `test_collector_execution` + `test_collector_v12` + `tests/architecture/`
    + `tests/m2/` (Django) — 58 passed.
- **Reported non-blocking issues (attached, not skipped):**
  1. pypdf 6.15 deprecation: `test_finalize_a1` triggers
     `PageObject.replace_contents()` deprecation (removal in pypdf 7.0.0).
     Pinned at 6.15.0 so it is stable; revisit on the next pin bump.
  2. `scripts/validate_change_packages.py --json` exits 1 because two
     pre-existing untracked docs are unclassified
     (`docs/operations/operator-action-plan-2026-08-29.md`,
     `docs/operations/project-migration-audit-2026-08-30.md`). Informational;
     blocks a commit only if those paths become staged.
  3. A1 provisional regeneration stays fail-closed: `finalize_a1.py readiness`
     reports 17 employees, 17 blocked (per-row certificate/signatory/source
     fields not AUTHORITATIVE; `certificate_reviewed`, `approved_for_pdf`,
     `validated_by_user` not set) — expected per `AGENTS.md`, not a regression.
- **Operational smoke checks:** `generate_planning_asset.py --check` current;
  `run_free_model_eval.py verify-fixtures` exit 0; `git diff --check` clean.

### Phase 3 — Build the dashboard

- **Action:**
  1. Add `portal/wsgi.py` (gunicorn entry).
  2. Add `portal/production_settings.py` (DEBUG=False, env-driven
     SECRET_KEY, ALLOWED_HOSTS).
  3. Drop the approval-gate flags from
     `portal/release1a/forms.py::A1PrepareForm` and
     `A1ApprovalForm` (or remove `A1ApprovalForm` if it now has no
     purpose).
  4. Add the A1-regenerate view that calls
     `scripts/finalize_a1.py` via `subprocess.run` and writes to
     `output/provisional/`.
  5. Wire scan upload → RapidOCR → proposals inline.
  6. Add `downloads/a1/<filename>` Django view (or just use nginx
     alias from §4.2).
  7. Run migrations + collectstatic.
  8. Smoke-test in local dev (`runserver`).
- **Checkpoint:** local dev server serves all 14 URLs from §2.1.
  497+ tests still pass; new tests for the regenerate + download views
  added under `tests/portal/`.
- **Operator input:** test Jan's flow locally; sign off the UX.
- **Rollback:** revert Phase 3 commits; the dashboard is incremental
  on top of M2 so revert is one `git reset` away.

### Phase 4 — Deploy (sysadmin work per §4)

- **Action:** sysadmin applies §4.2 steps; agent smoke-tests `/health`,
  `/ready`, login, one A1 regenerate end-to-end.
- **Checkpoint:** `https://prace-v-nemecku.tvoje.info/health` returns
  `{"status":"ok"}`; one full Jan flow (upload → OCR → edit → regenerate
  → download) works.
- **Operator input:** operator + Jan verify on the live URL.
- **Rollback:** `systemctl stop prace-v-nemecku-web` + revert the
  nginx vhost to the placeholder; the working tree is unchanged.

### Phase 5 — Cleanup + archive remaining legacy

- **Action:**
  1. Archive `.kilo/`, `.opencode/bun.lock`, `.opencode/node_modules/`
     to `.archive/dotfiles/` if these remain unused after Phase 3.
  2. Archive `docs/paddleocr/` to `.archive/docs/paddleocr/`
     (already marked historical; just relocates it).
  3. Archive `docs/plans/TODO_TRACKING.md` to
     `.archive/docs/plans/TODO_TRACKING.md` (superseded by
     `plans/INDEX.md`).
  4. Remove `pre-rewrite/*` local branches (after explicit approval
     per AGENTS.md "Never … delete branches without separate exact
     approval").
  5. Final `tar` to `/var/backups/sites/prace-v-nemecku.tar`
     (post-cleanup snapshot).
- **Checkpoint:** all moves recorded in CHANGELOG; one final tar.
- **Operator input:** approve the cleanup list.
- **Rollback:** restore from final tar.

---

## 7. Risks + open questions

1. **Tarball contains real data** (per operator instruction). This is
   acceptable on the host's local backup volume but must not be
   mirrored off-host without explicit re-approval.
2. **No automated test for the Jan UX flow**. Phase 3 needs at least
   one integration test per URL (or one end-to-end with `playwright`
   if available; `.playwright-mcp/` is already in the tree).
3. **OCR pipeline integration is not yet built**. RapidOCR is in
   requirements but no view runs it. Phase 3 must wire this.
4. **A1 regen from web calls subprocess** — needs timeouts, error
   surfacing, and a "running…" UI state. Plan the worker model in
   Phase 3 (use `aiojobs` or sync Django view with timeout).
5. **Single-tenant deploy** — the M2 model uses `TenantModel`, but
   the dashboard exposes one org. No multi-org complexity for Jan's
   first deployment.
6. **Plan AC + Plan AD + Plan AF gates remain out of scope** — the
   dashboard does not need them; they stay quarantined.
7. **Plan R readiness blockers** — per the operator action plan, A1
   regen is blocked by per-row data gaps. Phase 3 should either (a)
   surface those gaps as warnings in the dashboard UI without
   blocking generation, OR (b) leave them as Plan R work
   independent of the dashboard. Recommended: (a) per the operator's
   "no validations" instruction.

---

## 8. Cross-references

- `AGENTS.md` — operating model, PII rules, hook contract.
- `CHANGELOG.md` `[Unreleased] — 2026-08-29` — session commits.
- `docs/operations/operator-action-plan-2026-08-29.md` — operator
  inputs (replaces `docs/research/2026-08-19-open-decisions-research.md`
  R-01..L-02 for operator purposes).
- `.archive/README.md` — archive convention.
- `change-packages.yml` — package gating (mostly preserved in Phase 2;
  the dashboard commits add no new packages, only refine paths).
- `plans/INDEX.md` — current plan catalog; Phase 2 rewrites this.
- `/var/backups/sites/prace-v-nemecku.tar` — immutable baseline.

---

*Prepared 2026-08-30 by primary agent. Next refresh after Phase 2
(plan consolidation) lands.*