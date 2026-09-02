# Synthetic Release 1A Review Environment — Runbook

**Purpose:** Run the synthetic M2 review environment on s62, seed it with fixture data, and enable Jan to observe J1–J4 via the `Kontrola Release 1A` acceptance screen.

**Scope:** This runbook covers the review environment only. It does **not** authorize public routing, Tailscale exposure, real-data access, or production deployment.

**Environment:** s62 (`192.168.1.62`), operator account `pavel`.

---

## Prerequisites

- Repository at `/var/www/prace-v-nemecku.tvoje.info` (already present on s62).
- `venv` with dependencies installed: `venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt`.
- Secrets directory gitignored, `runtime/portal/` gitignored (already confirmed).

---

## Step 1 — Generate the review secret (once)

```bash
cd /var/www/prace-v-nemecku.tvoje.info
./scripts/generate_synthetic_review_secret.sh
```

Output: prints the SHA-256 of `secrets/synthetic_review.key` and the command to run the server.

Example output:
```
Generated: .../secrets/synthetic_review.key
SHA-256 of file:
a1b2c3d4...
To start the review server, run:
  export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
  export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
  python manage.py runserver 127.0.0.1:8000 --noreload
```

**The secret is never printed. The file is mode 600.**

---

## Step 2 — Run database migrations

```bash
export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
venv/bin/python manage.py migrate
```

This creates the DB at `runtime/portal/synthetic-review/db.sqlite3`.

---

## Step 3 — Seed fixture data (idempotent)

```bash
export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
venv/bin/python scripts/seed_release1a_dev.py --dry-run   # verify hashes first
venv/bin/python scripts/seed_release1a_dev.py --apply     # write data
```

Checks:
- Manifest SHA-256 hashes verified for all 7 fixture files.
- `M2_SYNTHETIC_ONLY = True` gate passes.
- Protected-path containment guard active.
- `Membership.mfa_verified` never read for authorization.

Re-running with `--apply` is safe (uses `update_or_create`).

---

## Step 4 — Activate Pavel's reviewer account (once)

```bash
export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
venv/bin/python manage.py activate_reviewer --email pavel-reviewer@example.invalid
```

Output: prints a one-time invitation URL.

```
Invitation for: pavel-reviewer@example.invalid
URL (valid 24h, single-use):
  http://127.0.0.1:8000/accounts/activate/<uuid>/

Suggested initial password (change after first login):
  Abc123xyz...
```

**The URL is valid for 24 hours, single-use.** The operator copy-pastes the URL into a browser connected to the s62 SSH tunnel (Step 6).

Jan's account (`jan-reviewer@example.invalid`) stays inactive until the stable review URL is approved.

---

## Step 5 — Verify automated readiness

```bash
cd /var/www/prace-v-nemecku.tvoje.info
./scripts/verify_synthetic_review_readiness.sh
```

This runs 10 checks (CSRF, allauth MFA wiring, fixture hash integrity, pytest suite results, gitignore coverage). Writes `runtime/portal/synthetic-review/readiness.json`. The `/review/check-answers/` page reads this file; if it is missing or older than 1 hour, the **Schválit Release 1A** button is disabled with a message.

Re-run after any code change that might affect the checks.

---

## Step 6 — Start the review server

```bash
export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

**No public or Tailscale routing is configured. The server binds loopback only.**

---

## Step 7 — Access the review environment

From a local machine with SSH access to s62:

```bash
ssh -L 8000:127.0.0.1:8000 pavel@192.168.1.62
```

Then open in a browser:

```
http://127.0.0.1:8000/
```

Log in with the activated reviewer account (Pavel sets password on first visit). Allauth will redirect to TOTP enrollment before any portal view is accessible.

---

## Step 8 — Jan observes J1–J4 via Kontrola Release 1A

Navigate to `/review/`. Four sections:

1. **Pracovník** — worker CRUD (J1)
2. **Dokument a kontrola OCR** — document upload + OCR confirmation (J2)
3. **Přiřazení** — assignment create/edit (J3)
4. **Příprava a kontrola A1** — A1 preparation (J4)

Each section has **Začít / Pokračovat / Dokončeno / Vyžaduje opravu** buttons.

When all four are **Dokončeno**, go to `/review/check-answers/`. The page shows:
- Four section results
- Automated readiness verdict (from `readiness.json`)
- Scope and exclusions (synthetic prototype only; real-data activation excluded)
- **Schválit Release 1A** button (enabled only if all sections DONE and readiness passed)

Jan clicks **Schválit Release 1A**. An immutable `Release1aAcceptance` record is written with git commit hash, clean/dirty state, build ID, and session UUID.

The receipt at `/review/receipt/` shows the approval. If the server code changes after this, the receipt shows a "Schválení je zastaralé" badge — a new approval is required against the new build.

---

## Step 9 — Accessibility checks (optional, for Jan's browser journey)

```bash
./scripts/axe_check.sh
```

Requires the review server to be running. Writes `runtime/portal/synthetic-review/axe.json`. Confirmed WCAG 2.2 A/AA violations block the approval button. Warnings and tool notices are listed in the receipt.

---

## Wiping the review DB

To start fresh:

```bash
rm -rf runtime/portal/synthetic-review/
export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
export DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review
venv/bin/python manage.py migrate
venv/bin/python scripts/seed_release1a_dev.py --apply
./scripts/verify_synthetic_review_readiness.sh
```

The `runtime/portal/synthetic-review/` directory is gitignored — wiping it never touches the repository.

---

## Rotating the review secret

```bash
./scripts/generate_synthetic_review_secret.sh
# Read the new SHA-256 to verify integrity
# Restart the server with the new secret:
export SYNTHETIC_REVIEW_SECRET=$(cat secrets/synthetic_review.key)
# ... restart runserver
```

---

## Separately authorized next steps (not in this runbook's scope)

| Next step | Authorization required |
|---|---|
| Stable HTTPS review URL via Traefik (`prace-v-nemecku-internal.tvoje.info`) | Separate infrastructure approval (D2) |
| Public routing / Tailscale exposure | Separate infrastructure approval |
| Real-data portal activation | `real-data-rules.md` + DEC-012 |
| GitLab-CI activation | Plan AE / DEC-016 |
| Production deployment | Separate operator + sysadmin gate |
