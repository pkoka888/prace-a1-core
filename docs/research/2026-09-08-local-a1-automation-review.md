# Review — 2026-09-08 local A1 automation plan

**Reviewed plan:** `plans/2026-09-08-local-a1-automation.md` (commit `dc358fb`,
2026-09-08).

**Scope.** Plan structure, naming/storage, gaps against authoritative sources
(Django, Python, GDPR, Czech ÚOOÚ, ČSSZ), and audit of the project's opencode
skills and current implementation state. The plan is a *proposed implementation
contract*, not an implemented command. This review does **not** authorise,
amend, or implement it.

**Method.** The plan was read alongside its parents (`PLAN-WORKERS`,
`PLAN-WORKERS-MIGRATE-TO-DB`, `PLAN-A1`, `2026-09-06-ocr-shared-core-local-web`)
and the existing implementation (`portal/release1a/{models,services,document_intake,j4_artifacts,document_storage}.py`,
`scripts/finalize_a1.py`, `.agents/skills/a1-pdf-production/SKILL.md`,
`.opencode/skills/market-research-evidence/SKILL.md`, `docs/security/real-data-rules.md`).
Three parallel research passes pulled authoritative citations from
docs.djangoproject.com, docs.python.org, eur-lex.europa.eu (GDPR), the Czech
ÚOOÚ document, and the ČSSZ ePortal service page.

---

## 1. Summary

The plan is **structurally coherent** with its parents and consistent with the
existing intake pipeline. It correctly leans on already-implemented building
blocks (`validate_content`, `intake`, `execute_run`, `persist_proposals`,
`known_workers`, `attach_a1_artifact`, `j4_artifacts.publish_artifact`) and
defers the missing draft/BO confirmation contract to J4. The "verification
without blocking the batch" framing is the right idea.

**However, the plan contains concrete gaps and one concrete conflict that an
implementer would hit on day 1:**

1. The proposed storage paths **do not match** the `ProtectedDocumentStorage`
   regex, so the coordinator would either need a new storage backend or to
   bypass storage entirely.
2. There is **no `Batch`/`Inbox` model** in `portal.release1a`; the
   `IntakeSession` model is per-worker, not per-batch.
3. There is **no `Draft` status** on `A1Case`; the readiness flag is binary
   (`BLOCKED`/`READY`) and `validated_by_user` lives only on the CSV review
   row.
4. The `system_worker` actor is declared with an **empty capability set** in
   `services.py:44`; no current path lets a non-user satisfy `require_capability`.
5. The `a1/runs/<run_uuid>/` path collides with the `a1/_archive/` reservation
   in `PLAN-WORKERS-MIGRATE-TO-DB.md`.
6. The skill `.agents/skills/a1-pdf-production/SKILL.md` describes a
   **single-batch** CLI flow (`scripts/generate_provisional_a1.py`) and does
   not cover inbox/draft/BO vocabulary.
7. The plan does not reference the **GDPR controller/processor allocation**,
   the **Art. 30 records-of-processing obligation**, the **Art. 22 (Recital 71
   e-recruiting) safeguard** in the matching flow, or the **Czech OP-copy
   statutory ban** (`§ 15a odst. 2 zák. č. 328/1999 Sb.`).
8. **The data shape does not match the plan.** Of 44 canonical CSV
   columns (`scripts/finalize_a1.py:46-58`), only 5 map directly to
   current model fields. The other 39 (worker nationality/sex/insurance/
   address/document fields, Section 4 employment fields, Section 5
   activity fields, certificate dates/signatory, source-status markers,
   review flags) have no home in `portal.release1a`. The only populated
   database (`runtime/portal/synthetic-review/db.sqlite3`) is missing
   migrations 0010-0013 and has never run the OCR pipeline. See §13.

The remainder of this document lists each finding with citations and recommended
amendments. None of the recommendations is implemented here.

---

## 2. Plan structure and parent alignment

### 2.1 Strengths

- **Status flag** correctly distinguishes "proposed implementation contract"
  from implemented code; preserves parent status of `PLAN-WORKERS`,
  `PLAN-WORKERS-MIGRATE-TO-DB`, `PLAN-A1` (line 3-7).
- **No new top-level catalog entry**; reuses DB-MIG-1…7 and J2/J4 (line 7).
- **Delivery order** matches the existing dependency graph: synthetic J2 →
  DB-MIG-1/2/5 (identity mapping) → DB-MIG-3/4 + J4 draft contract → BO
  confirmation → DB-MIG-6/7 (line 143-153).
- **Hard rules** preserved: `A1_PRIVATE_DIR` is mandatory; CSV/JSON become
  archive-only after DB-MIG-7; the renderer reads from `scripts/a1_core.py`
  (line 75, 115).
- **One source of truth** statement (line 32-44) correctly distinguishes
  authoritative DB rows from derived JSON/CSV exports.
- **Worker identity / OCR overwrite rule** ("confirmed fields remain intact;
  changed values become proposed corrections", line 65) is consistent with
  `services.py:230-237` (`WorkerIdentityRevision` chain).
- **Section 5 policy** (line 70-72) matches `config/a1_provisional.json` and
  `scripts/a1_core.py` semantics.
- **Verification without blocking the batch** (line 87-104) is the right
  framing; it keeps BO confirmation separate from machine checks.

### 2.2 Structural gaps

| # | Gap | Plan line | Notes |
|---|---|---|---|
| G-01 | No **rollback / crash-recovery semantics** are specified for the coordinator itself | 144 | Step 5 (delivery order) says "per-record retry/resume" but no DB-level idempotency contract is given. |
| G-02 | **No idempotency-key design** for the coordinator | — | Without a `Batch` row keyed by an external batch UUID, a re-run may double-process an inbox. |
| G-03 | **No rollback path** for an `A1Case` written from OCR proposals | — | The plan says "Autoatically refresh only the unconfirmed proposal/draft revision" (line 65) but does not define how a malformed OCR batch is undone. |
| G-04 | **No actor model for system actions** | 65, 78 | `services.py:44` declares `system_worker: set()` (no capabilities). A batch run has no `user.pk`; the plan must define either a system actor or an authorised user. |
| G-05 | **Section 5.1 blank / 5.2 default** is repeated (line 70-72) but the canonical CSV column is not named | 70 | `scripts/finalize_a1.py:185-209` shows `activity_name`, `activity_address` are required readiness fields; the plan's "Scans do not supply missing employment facts" (line 69) should explicitly cite the CSV column set. |
| G-06 | **The plan is silent on the `Activity-Profile-EMPLOYEE` vs `self_employed` split** beyond "Keep employee and self-employed profiles distinct" (line 71) | 71 | `Worker.activity_profile` is binary (`employee`/`self_employed`, `models.py:109`). The matching flow must branch on it; the plan says only "obvious" things. |
| G-07 | **No DB-MIG milestone assignment** for the J4 draft contract | 147 | Step 3 says "J4 draft contract" but DB-MIG-3/4 only mention "direct shared-core rendering from explicit pending/confirmed snapshots" — the "draft" status is undefined. |
| G-08 | **No acceptance gating for A1REPAIR** interaction | 147 | `plans/2026-09-06-a1-evidence-status-repair.md` (A1-REPAIR-1…7) is not cross-referenced. The provisional package is currently blocked (25/25 rows per the 2026-09-06 baseline in `roadmap.md:328`). Any new automation must defer until repair acceptance. |

### 2.3 Items the plan states but does not design

- "Atomic batch publication" (line 47-48) — only "ready marker" is named; the
  file-system atomicity pattern (write-to-staging → fsync → rename) is not.
- "Uniqueness constraints and revision checks to prevent race duplicates"
  (line 67) — no specific constraint is named.
- "Deterministic and visual checks … snapshot/template/layout/renderer/QA
  hashes" (line 80) — `scripts/a1_quality_gate.py` is referenced indirectly
  via `scripts/a1_core.py` only.
- "Reserve generated numbers in the database transaction and reuse them on
  retries" (line 77) — no model column or unique-constraint design.

---

## 3. Naming / storage audit

### 3.1 Conflicts with existing code

`ProtectedDocumentStorage.path` (`portal/release1a/document_storage.py:13-16`)
rejects every key that is not:

```
(?:documents|generated)/[a-f0-9]{32}(?:/[a-f0-9]{64})?\.(?:source|json|png)
```

The plan's storage table (`plans/2026-09-08-local-a1-automation.md:120-128`):

| Plan path | Existing constraint | Conflict |
|---|---|---|
| `runtime/portal/documents/<document_uuid>/<version_uuid>.<ext>` | Top level must be `documents/` or `generated/` and a 32-hex token; the `<document_uuid>/<version_uuid>` shape is allowed only as `documents/<32hex>/<64hex>.(source\|json\|png)` | **Conflicts.** The plan's `<document_uuid>/<version_uuid>` cannot be a `<32hex>/<64hex>` pair unless the regex is widened. |
| `runtime/portal/generated/<artifact_uuid>/document.pdf` | Top-level prefix must be `documents\|generated`; suffix must be `.source\|json\|png`; `.pdf` is rejected | **Conflicts.** PDFs are stored today by `j4_artifacts.publish_artifact` (`portal/release1a/j4_artifacts.py:69-118`) into a separate staging path under `<j4-staging-dir>/artifact.pdf` and renamed, **bypassing** `ProtectedDocumentStorage.path`. |
| `runtime/portal/previews/<artifact_uuid>/page-001.png` | Top-level prefix must be `documents\|generated`; `previews/` is rejected | **Conflicts.** Page previews are stored today by `publish_artifact` (`j4_artifacts.py:86-91`) into the same staging path. |
| `ocr/<run_uuid>/result.json` | Top-level prefix must be `documents\|generated` | **Conflicts with the canonical run-result store.** Today's OCR runs write `generated/<token>.json` (`portal/release1a/document_intake.py:212`), key `generated/<32hex>.json`. The repo-root `ocr/` directory is gitignored and only holds ad-hoc OCR results. |
| `a1/runs/<run_uuid>/` | The migration plan reserves `a1/_archive/` (`plans/PLAN-WORKERS-MIGRATE-TO-DB.md:80-81`) | **Naming collision.** Both plans reserve a different gitignored `a1/` subtree. |
| `scans/inbox/<batch_uuid>/<upload_uuid>.<ext>` | `scans/` is permitted by `real-data-rules.md` §5, but `inbox/` is not enumerated | **Needs §5 amendment.** `real-data-rules.md` §5 (line 81-94) lists `a1/`, `scans/`, `ocr/`, `evidence/`, `output/`, `runtime/portal/{quarantine,documents,generated,previews,temporary}`. The inbox subdir must be added or explicitly carved out. |

### 3.2 Recommended amendments

1. **Align plan paths with `ProtectedDocumentStorage` regex**, or open an
   explicit ADR to widen the regex. The plan's coordinator must not write
   storage keys that `ProtectedDocumentStorage.path` will reject on round-trip.
2. **Replace `ocr/<run_uuid>/result.json`** with the existing canonical key
   `generated/<attempt_token>.json` (today's `document_intake.py:212`).
   Cross-references like "OCR results: `ocr/<run_uuid>/result.json`" must
   inherit the actual storage, not invent a parallel tree.
3. **Use `<artifact_uuid>.pdf` (single token, not `<artifact_uuid>/document.pdf`)**
   to match today's `j4_artifacts.publish_artifact` convention, or open a
   dedicated ADR for previews.
4. **Resolve `a1/runs/` vs `a1/_archive/`** by deleting `a1/runs/` from the
   plan. Per `PLAN-WORKERS-MIGRATE-TO-DB.md`, the legacy CSV/JSON are
   archive-only after DB-MIG-7. A new "runs" subtree in the same parent is
   confusing and may make the freeze ambiguous.
5. **Add `scans/inbox/<batch_uuid>/` to `real-data-rules.md` §5** before the
   coordinator implementation, so the manifest/ready-marker path is
   policy-supported. Until then the inbox path is an undocumented sink.

---

## 4. Model gaps against `portal/release1a/models.py`

### 4.1 No batch model

Grep across `portal/release1a/models.py` and migrations:

```
$ grep -E 'Batch|Inbox' portal/release1a/*.py portal/release1a/migrations/*.py
(no matches)
```

The only `IntakeSession` (`portal/release1a/models.py:235-254`) is per-worker,
per-purpose (`A1`, `ASSIGNMENT`, `PAYROLL`), with `DRAFT` / `INTAKE_COMPLETE`
/ `MERGED` / `ARCHIVED` states. It is created **after** upload (`intake_views.py:87`),
not before. The plan's step 1 ("Uploader writes temporary files and atomically
publishes a manifest/ready marker") has no model.

**Recommendation.** Add a `Batch` model before any coordinator code. Minimal
fields: `id` (UUID4), `organization`, `uploader_actor_ref`, `manifest_path`,
`ready_at`, `state` (`CLAIMED`, `RUNNING`, `COMPLETED`, `FAILED`,
`PARTIAL`), `idempotency_key` (`unique=True` with `(organization, id)`),
`created_at`. The `IntakeSession` should FK back to `Batch` so existing
per-worker intake sessions can be grouped.

### 4.2 No draft status on `A1Case`

`A1Case.Readiness` is binary:

```python
class Readiness(models.TextChoices):
    BLOCKED = "blocked", "Blokováno"
    READY = "ready", "Připraveno"
```

(`portal/release1a/models.py:158-162`)

There is no `DRAFT` or `UNVERIFIED` status. The closest existing signal is
`visual_confirmed` (`models.py:180-190`, migration 0012), but that is a
post-attachment BO confirmation, not a draft status.

`scripts/finalize_a1.py:362-363` enforces `validated_by_user=1` before
`attach_a1_artifact` proceeds (`portal/release1a/services.py:295-298`). The
plan's "unverified draft with immutable input snapshot" (line 110) needs a new
state. Three options:

1. New `A1Case.Readiness.DRAFT` plus `A1Case.draft_created_at`, `draft_source_hash`.
2. Reuse the existing `source_snapshot_json` + `is_stale` as draft markers and
   add `draft_only=True` (cheaper).
3. A separate `A1CaseDraft` model (most isolated, easiest to migrate later).

The plan's wording ("reuse the core renderer through that service with a
visible UNVERIFIED DRAFT notice and separate draft status", line 109-110) does
not pick one.

### 4.3 `system_worker` actor has no capabilities

`portal/release1a/services.py:44`:

```python
"system_worker": set(),
```

Every audit `actor_ref` is `f"user:{user.pk}"`. There is no precedent for a
non-user actor passing `require_capability`. The plan's coordinator will need
either:

- A privileged user invoked by cron / systemd (re-uses the role capability
  map), **or**
- A `system` actor with a documented capability set that includes
  `worker:create`, `document:upload`, `a1:prepare_draft`, `a1:read`,
  `audit:read` (and explicit denial of `a1:approve`).

Without this, the coordinator has no way to call `prepare_a1` (line 142) and
`attach_a1_artifact` (line 271) — both `require_capability(...)`.

### 4.4 No state-machine tests for the planned lifecycle

`tests/test_j4_minimum.py` and `tests/m2/test_j4_delivery.py` cover
`BLOCKED`/`READY` and `visual_confirmed` toggle, but no test asserts a
`draft → verified → confirmed` (or `pending → ready → confirmed`) transition
on `A1Case`. Any state added by the coordinator must come with a state-machine
test (per `AGENTS.md` "Migration transition tests must use Django historical
app states through MigrationExecutor").

---

## 5. Django / Python authoritative gaps

### 5.1 `select_for_update` portability

The plan needs cross-process mutual exclusion for "Claim only complete
batches" (line 47). `select_for_update()` is silently a no-op on SQLite:

> "SQLite does not support the `SELECT ... FOR UPDATE` syntax. Calling it
> will have no effect."
> https://docs.djangoproject.com/en/stable/ref/databases/#queryset-select-for-update-not-supported

Acceptance runs on SQLite will pass; production on PostgreSQL will lock. The
acceptance-command text must run against the same backend the coordinator will
ship on. Per `AGENTS.md`, synthetic acceptance is also permitted on fresh
PostgreSQL test DBs.

### 5.2 Idempotency

`get_or_create()` is "the recommended way to handle upserts" but under
MySQL repeatable-read may raise `IntegrityError`. For OCR/inbox runs, the
canonical pattern is a unique constraint + atomic insert:
https://docs.djangoproject.com/en/stable/ref/databases/#mysql-isolation-level

The plan's "repeated batch causes no duplicates" acceptance item (line 158)
must be implemented as `unique=True` on `(organization, batch_idempotency_key)`
with `F()`-style atomic counter increment, not `get_or_create()`.

### 5.3 Atomic file publish

The plan says "atomically publish a manifest/ready marker" (line 47) without
naming the pattern. The Python-canonical pattern is:

```python
fd, tmp = tempfile.mkstemp(prefix=".manifest-", dir=root)
os.write(fd, payload); os.fsync(fd); os.close(fd)
os.replace(tmp, final_path)  # atomic on POSIX
```

> "Rename the file or directory src to dst. … `os.replace` can be used to
> atomically replace dst with src."
> https://docs.python.org/3/library/os.html#os.replace

> "Creates a temporary file in the most secure manner possible. There are no
> race conditions … assuming that the platform properly implements the
> `os.O_EXCL` flag."
> https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp

`j4_artifacts._write` (`portal/release1a/j4_artifacts.py:45-50`) already
implements this correctly. The coordinator should reuse `_write` and the
publication lock at `j4_artifacts.py:104-111` (`fcntl.flock`) rather than
inventing a parallel mechanism.

### 5.4 Management command surface

The plan names `venv/bin/python manage.py a1_process_inbox` (line 20). The
canonical place is `portal/release1a/management/commands/a1_process_inbox.py`,
next to the existing `activate_reviewer.py`. Per
https://docs.djangoproject.com/en/stable/howto/custom-management-commands/ :

- `add_arguments` only parses CLI; no work belongs there.
- Use `CommandError` for failures ("the preferred way to indicate that
  something has gone wrong").
- Use `self.stdout` / `self.stderr`, never `print`.
- Built-in flags `--verbosity`, `--no-color`, `--traceback`,
  `--skip-checks`, `--database` are auto-added; design around them.
- Consider `@no_translations` if the command writes translated DB rows in
  bulk.

### 5.5 `STORAGES` setting

Django 4.2+ replaced `DEFAULT_FILE_STORAGE` with the `STORAGES` setting:
https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-STORAGES

The plan does not mention which storage backend will host the new paths
(inbox, batch receipts, draft PDFs). If the coordinator writes outside
`ProtectedDocumentStorage`, an explicit `STORAGES` entry is needed.

---

## 6. GDPR / Czech DPA authoritative gaps

### 6.1 Controller / processor allocation not stated

`AGENTS.md` and `real-data-rules.md` describe purpose, retention, audit, but
not the GDPR Art. 4(7)/(8) allocation. Without it, Art. 28 contract terms
and Art. 33 breach routing have no addressee.

> "processes the personal data only on documented instructions from the
> controller… [and] takes all measures required pursuant to Article 32."
> (Art. 28(3)) — https://eur-lex.europa.eu/eli/reg/2016/679/art_33/oj/eng

> "Each controller … shall maintain a record of processing activities under
> its responsibility." (Art. 30(1))
> https://eur-lex.europa.eu/eli/reg/2016/679/art_30/oj/eng

> "Each processor … shall maintain a record of all categories of processing
> activities carried out on behalf of a controller." (Art. 30(2))
> https://eur-lex.europa.eu/eli/reg/2016/679/art_30/oj/eng

OP/ZP processing is non-occasional; the Art. 30 record is mandatory
regardless of the ≥250-employee threshold.

**Recommendation.** Designate roles explicitly in `PLAN-INFRA` (or this plan's
parent): the operator ("Jan"/the company) is the **controller** for the worker
database and A1 artifacts; `portal.release1a.services`, the OCR core, and the
coordinator are **processors** acting on documented controller instructions.
Reference this from DB-MIG-1, OCR-CORE-1, DB-MIG-5.

### 6.2 Art. 22 / Recital 71 in the matching flow

> "such as automatic refusal of an online credit application or e-recruiting
> practices without any human intervention." — Recital 71
> https://eur-lex.europa.eu/eli/reg/2016/679/art_22/oj/eng

The plan's step 5 ("An exact, consistent strong identifier may link a proposal
to an existing worker … A new, unambiguous identity may create a draft
worker", line 60-63) is **solely automated** worker-to-cohort matching.
Recital 71 names "e-recruiting practices without any human intervention"
verbatim as a target of Art. 22.

**Recommendation.** Bind `match_proposal → human-reviewed → CONFIRMED` as a
hard lifecycle. The plan's "verification without blocking the batch" (line
87-104) is the correct idea but does not enforce it as a state-machine
constraint. Add a test that no `Worker` row may be created by a batch
without a corresponding `WorkerIdentityRevision` whose `confirmed_by` is a
non-null user. The current `services.py:230-237` chain already does this
when the proposal is *confirmed*; the plan must not let the matching flow
skip confirmation.

### 6.3 Czech OP/ZP statutory ban

> "stanovují příslušné zákony zákaz pořizovat jakýmikoliv prostředky kopie
> těchto průkazů bez prokazatelného souhlasu občana, kterému byl průkaz
> vydán…" (§ 15a odst. 2 zák. č. 328/1999 Sb.; § 2 odst. 3 zák. č. 329/1999 Sb.)
> — p. 6, https://uoou.gov.cz/media/clanky/dokumenty/prokazovani-totoznosti-a-zpracovani-osobnich-udaju-1.pdf

> "zákon o občanských průkazech výslovně zakazuje shromažďovat, ukládat,
> upravovat nebo pozměňovat, předávat, šířit, zveřejňovat, uchovávat,
> kombinovat, blokovat nebo likvidovat strojově čitelné údaje vedené
> v občanském průkazu, popřípadě v kontaktním elektronickém čipu…" — p. 10,
> same source.

The plan stores "Accepted original scans" (`runtime/portal/documents/<document_uuid>/<version_uuid>.<ext>`,
line 122) without:

- a legal-basis statement per purpose (Art. 6(1)(b)+(c) per the Czech DPA's
  Q&A on employee data, https://uoou.gov.cz/verejnost/qa-otazky-a-odpovedi/k-vyzadovani-souhlasu),
- a test that the OCR pipeline drops MRZ / contactless chip data, and
- a record-of-processing entry referencing the OP/ZP source.

**Recommendation.** Add a unit test that the OCR output for a synthetic Czech
OP contains exactly the agreed fields (surname, given_name, dob, OP number,
OP expiry, issuing authority) and **nothing** from the back / MRZ. The ÚOOÚ
p. 10 ban is unconditional; a pipeline that retains MRZ is non-compliant.

### 6.4 Czech DPA data minimisation

> "Pořizováním kompletních kopií dokumentů a jejich ukládáním do evidence
> může docházet k porušování zásady minimalizace, vzhledem k tomu, že
> dokumenty obsahují i další osobní údaje pro stanovený účel nikoli
> nezbytné." — p. 9,
> https://uoou.gov.cz/media/clanky/dokumenty/prokazovani-totoznosti-a-zpracovani-osobnich-udaju-1.pdf

> "Možné porušení zásady minimalizace … bývá někdy řešeno pořízením kopie
> pouze části dokladu se zakrytím nepotřebných údajů např. pomocí šablony…"
> — p. 9, same source.

> "Je odpovědností správce, aby si uložil a dále zpracoval pouze ty údaje
> na občanském průkazu … které jsou k jeho účelu zpracování osobních údajů
> nezbytné." — p. 10, same source.

The plan stores **full OP/ZP originals** under `runtime/portal/documents/...`.
Per the ÚOOÚ, this is the prima facie minimisation violation unless
documented purpose binds every field and a record-of-processing entry names
them.

**Recommendation.** Justify each retained field by purpose, in the same
document as the Art. 30 record. Add a "fields-kept vs fields-needed" test
for the OCR output.

### 6.5 Art. 33 / 34 breach runbook not in plan

> "the controller shall without undue delay and, where feasible, not later
> than 72 hours after having become aware of it, notify the personal data
> breach to the supervisory authority…" (Art. 33(1))
> https://eur-lex.europa.eu/eli/reg/2016/679/art_33/oj/eng

> "The processor shall notify the controller without undue delay after
> becoming aware of a personal data breach." (Art. 33(2)) — same source.

`real-data-rules.md` §11 describes incident response but does not name the
72-hour clock or the controller-route. The plan adds a new automated batch
processor (a processor) and does not mention notification routing.

**Recommendation.** Add an explicit Art. 33 procedure to the plan (or
reference `real-data-rules.md` §11 with the 72-hour clock added). Add a test
that simulates a leaked inbox path and asserts the audit event contains the
required breach-record fields (Art. 33(5)) — without leaking PII content.

### 6.6 Art. 32 regular testing

> "a process for regularly testing, assessing and evaluating the
> effectiveness of technical and organisational measures for ensuring the
> security of the processing." (Art. 32(1)(d))
> https://eur-lex.europa.eu/eli/reg/2016/679/art_32/oj/eng

Passing tests is not enough; the TOMs themselves must be regularly tested.
The plan's "acceptance commands" (line 158-163) are not a substitute.

**Recommendation.** Add an annual TOM-test calendar (or reference
`real-data-rules.md` §11) covering encryption-at-rest verification, key
rotation, restoration drill, quarterly access review, and breach-response
table-top.

### 6.7 Pseudonymisation

> "the processing of personal data in such a manner that the personal data
> can no longer be attributed to a specific data subject without the use
> of additional information, provided that such additional information is
> kept separately…" (Art. 4(5)) —
> https://eur-lex.europa.eu/eli/reg/2016/679/art_32/oj/eng

> "The application of pseudonymisation to personal data can reduce the
> risks to the data subjects concerned and help controllers and processors
> meet their data-protection obligations." (Recital 78) — same source.

The plan says "Stored filenames use UUIDs; names and readable titles appear
in BO" (line 117). This is correct but incomplete: filenames, OCR output
JSON keys, A1 row identifiers, and the inbox path are all part of the
"additional information" chain. They must be the only chain; a name → UUID
mapping table must live in the encrypted, separately-stored worker record.

**Recommendation.** Adopt the existing opaque-key convention (UUID4 for
storage keys, opaque `actor_ref=f"user:{user.pk}"` in audit events) as the
canonical pseudonymisation scheme. Add a test that no audit event, no log
line, no JSON dump contains a worker surname, OP number, or birth date.

---

## 7. ČSSZ authoritative gap

> "Spuštění vyžaduje přihlášení."
> https://eportal.cssz.cz/web/portal/-/sluzby/zadost-o-urceni-pouzitelnych-pravnich-predpisu-pro-zamestnance-pojistenec

> "Zpracování služby nebylo úspěšné? Důvodem jsou zřejmě chybné vstupní
> údaje. Službu spusťte znovu s opravenými údaji." — same source

The ČSSZ ePortal A1 service is **interactive** (login required) and
**non-idempotent** (re-launch on bad input, not re-submit). The plan's
coordinator is local batch preparation; it does **not** submit to ČSSZ, so
this is not a blocker. But the plan should explicitly say so, because the
"J4 minimum" → "ENG-001" → "REV-002" gate sequence (`roadmap.md:320`)
includes an eventual ČSSZ submission step that is not idempotent and
requires authenticated user launch.

**Recommendation.** Add a single line: "The coordinator prepares the local
application only; ČSSZ submission remains an authenticated ePortal launch
by Jan and is not idempotent. Re-launch on bad input is the ČSSZ-blessed
recovery path; no batch de-duplication key is sent upstream."

---

## 8. Skill audit

### 8.1 `.agents/skills/a1-pdf-production/SKILL.md`

The skill (45 lines) covers the **single-batch CLI flow**:

- Inputs: `$A1_PRIVATE_DIR/a1/review.csv` + `$A1_PRIVATE_DIR/a1/cohort.json`
  (line 12-13).
- Entry point: `scripts/generate_provisional_a1.py` (line 19).
- Output: `output/provisional/` (line 23).

It does **not** cover the proposed `a1_process_inbox` coordinator. Gaps:

- No inbox-claim pattern.
- No worker-matching-from-evidence pattern.
- No UNVERIFIED DRAFT contract.
- No BO confirmation / immutable revision flow.
- No `manage.py a1_process_inbox` surface.

The references `field-policy.md`, `mcp-contract.md`, `visual-qa.schema.json`
also do not mention inbox/draft/BO vocabulary.

**Recommendation.** If the plan is accepted, the skill needs a parallel
section ("Batch intake to draft coordinator") that points to the new
management command and explicitly preserves the existing
"single-batch CLI" path. Without it, an agent using the skill will follow
the CLI path and miss the coordinator.

### 8.2 `.opencode/skills/market-research-evidence/SKILL.md`

This is the Plan PLAN-INVOICE / Plan AC skill. It is **not relevant** to
A1/portal. The plan does not cite it. No action required.

### 8.3 Customise-opencode skill

Not applicable — the plan does not modify opencode configuration.

---

## 9. Cross-plan interaction

### 9.1 PLAN-WORKERS-MIGRATE-TO-DB (`plans/PLAN-WORKERS-MIGRATE-TO-DB.md`)

- DB-MIG-1…7 milestones are referenced (line 7, 144-153). Good.
- The `a1/_archive/` reservation (DB-MIG-6) conflicts with the plan's
  `a1/runs/<run_uuid>/` (see §3.1 above).
- DB-MIG-5 ("reads `a1/review.csv` + `a1/cohort.json` once, writes DB rows
  with provenance hashes") needs Art. 5(1)(c) justification (the legacy
  files contain PII: rodná čísla, OP numbers, full names, dates of birth).
  The migration plan is silent on Art. 30 and on the pseudonymisation of
  the source columns.

### 9.2 PLAN-A1 (`plans/PLAN-A1.md`)

- Provisional regeneration is **blocked** at 25/25 rows per the 2026-09-06
  baseline (`roadmap.md:328`). Any new automation must defer until
  A1-EVIDENCE-STATUS-REPAIR acceptance.
- The canonical evidence pipeline (`scripts/a1_core.py`,
  `scripts/finalize_a1.py`, `scripts/a1_quality_gate.py`) is the only
  authoritative rendering path; the plan respects this (line 75).
- The plan's "machine actor is never recorded as the human verifier"
  (line 104) is consistent with `real-data-rules.md` §4.

### 9.3 PLAN-REAL-DATA

- Activation gate (§14 of `real-data-rules.md`) is not touched by this plan;
  the coordinator must fail closed on `REAL_DATA_ACTIVATION_REQUIRED`
  (`portal/release1a/document_intake.py:64-66`) until the gate is opened.

### 9.4 A1-EVIDENCE-STATUS-REPAIR (`plans/2026-09-06-a1-evidence-status-repair.md`)

A1-REPAIR-1…7 are not cross-referenced. The plan's "unverified draft"
contract must not bypass them; in particular, A1-REPAIR-3 ("canonical
employee support") and A1-REPAIR-4 ("reviewed-input preservation") are
directly relevant.

---

## 10. Recommended amendments (summary, ordered)

The following amendments are recommendations only; none is implemented here.
The plan remains a proposal; nothing changes about parent statuses, catalog
IDs, or activation gates.

1. **Storage paths**: align with `ProtectedDocumentStorage` regex or open
   an ADR; replace `ocr/<run_uuid>/result.json` with the canonical
   `generated/<token>.json`; remove `a1/runs/<run_uuid>/` to avoid the
   collision with `a1/_archive/`; add `scans/inbox/<batch_uuid>/` to
   `real-data-rules.md` §5.
2. **Batch model**: add `Batch` (UUID4, organisation, manifest_path, state,
   idempotency_key unique per organisation) before any coordinator code;
   have `IntakeSession` FK back to `Batch`.
3. **Draft status**: pick one of (a) new `A1Case.Readiness.DRAFT`,
   (b) `draft_only=True`, (c) `A1CaseDraft` model. Add state-machine tests
   on MigrationExecutor.
4. **System actor**: add explicit `system` role with capability set
   including `worker:create`, `document:upload`, `a1:prepare_draft`,
   `a1:read`, `audit:read`; explicit denial of `a1:approve`.
5. **Idempotency**: `unique=True` on `(organization, batch_idempotency_key)`
   with `F()`-style atomic counter; not `get_or_create()`.
6. **`select_for_update` portability**: acceptance commands must run
   against the same backend the coordinator will ship on
   (PostgreSQL per `AGENTS.md`).
7. **Atomic publish**: reuse `j4_artifacts._write` and
   `j4_artifacts.publish_artifact` lock; `tempfile.mkstemp` + `os.replace`
   for the manifest/ready marker.
8. **Management command**: implement under
   `portal/release1a/management/commands/a1_process_inbox.py`; thin adapter
   only; `CommandError` for failures; `self.stdout` / `self.stderr`;
   design around the auto-added `--verbosity` / `--database` /
   `--skip-checks` flags.
9. **GDPR roles**: add explicit controller/processor allocation in
   `PLAN-INFRA` (or this plan's parent); Art. 30 record-of-processing;
   Art. 32(1)(d) TOM-test calendar; Art. 33 72-hour clock.
10. **Art. 22 / Recital 71**: bind `match_proposal → human-reviewed →
    CONFIRMED` as a hard lifecycle; add a test that no `Worker` row may be
    created by a batch without a corresponding `WorkerIdentityRevision`
    whose `confirmed_by` is non-null.
11. **Czech OP/ZP compliance**: legal-basis citation (Art. 6(1)(b)+(c));
    MRZ/chip-drop test; fields-kept vs fields-needed test; reference to
    § 15a odst. 2 zák. č. 328/1999 Sb. and § 2 odst. 3 zák. č. 329/1999 Sb.
12. **Pseudonymisation**: name the opaque-UUID scheme as the GDPR Art. 4(5)
    pseudonymisation; add an audit/log test for absence of names, OP
    numbers, birth dates.
13. **ČSSZ acknowledgement**: add a one-line note that ČSSZ submission is
    non-idempotent and remains an authenticated ePortal launch.
14. **Skill update**: if the plan is accepted, extend
    `.agents/skills/a1-pdf-production/SKILL.md` with a "Batch intake to
    draft coordinator" section.
15. **Cross-reference**: add links from this plan to
    `2026-09-06-a1-evidence-status-repair.md` (A1-REPAIR-1…7) and to
    `real-data-rules.md` §14.

### Data-shape amendments (from §13 diff)

16. **DB-MIG-1 worker columns.** Add to `Worker` (or a related identity
    model): `nationality`, `sex`, `insurance_number`, address fields,
    `id_document_type`, `id_document_number`. Without these, "DB is
    single source of truth" cannot be true for 6 of the 7 worker
    identity CSV columns.
17. **DB-MIG-2 A1Case columns.** Add to `A1Case`: `document_id`,
    `start_date`, `end_date`, `issue_date`, `signed_by`,
    `activity_source`, `activity_source_status`, `certificate_source`,
    `certificate_source_status`, `signatory_source`,
    `signatory_source_status`, `validated_by_user`. The readiness gate
    (`scripts/finalize_a1.py:183-235`) reads all of these from the CSV
    today; the migration must move them onto the model before
    `finalize_a1.row_to_form()` can be re-pointed at the DB (DB-MIG-3).
18. **Assignment fields.** Add `Assignment.role_label`,
    `Assignment.partner_name`, `Assignment.overlap_with` (FK or join
    table), and the `a1_period_ambiguous` boolean. Today the DB
    `activity_label` is empty for all 5 records; fixture `role` values
    are lost.
19. **DB-MIG migration upgrade.** Run `manage.py migrate` against
    `runtime/portal/synthetic-review/db.sqlite3` to apply migrations
    0010-0013 before any coordinator work. The DB currently stops at
    migration 0009; columns like `is_stale`, `source_snapshot_json`,
    `visual_confirmed*`, `evidence_*`, `receipt_*`, `notes` do not
    exist.
20. **Synthetic acceptance must rebuild the DB.** The current seed in
    `runtime/portal/synthetic-review/db.sqlite3` was authored
    independently of `tests/fixtures/release_1a/workers.json` (the
    worker names match but `activity_profile` does not). Synthetic
    acceptance must rebuild the DB from the fixtures in one
    transaction, not assume the current seed is correct.
21. **Synthetic acceptance must seed OCR.** The synthetic-review DB
    has 4 documents and 0 OCR runs. The plan's step 4 cannot be
    exercised without `Document → DocumentVersion → OcrRun` rows; the
    acceptance must seed or assert the result of seeding.
22. **Institution profile completion.** Two profiles (`kladno`,
    `usti-nad-labem`) still have `code: TBD`; one (`louny`) is
    `NEEDS_VERIFICATION`. The plan must not assume institution profile
    readiness is satisfied. Any synthetic cohort that references
    those OSSZ branches will fail readiness.
23. **Reuse `scripts/seed_release1a_dev.py`.** The seed script exists
    at `scripts/seed_release1a_dev.py` but the plan does not reference
    it. Either name it as the canonical loader or name a replacement
    so the synthetic acceptance can be reproduced from a fresh DB.
24. **`Worker.state` vs fixture `status` vocabulary.** The plan should
    pick one. `Worker.state` is `draft`/`active`/`archived`; the
    fixture uses `active`/`inactive`. The current synthetic DB seed
    uses `draft` for all four records even though three fixture
    records are `active`. This is not a blocking issue, but the plan's
    acceptance must specify the expected value.

---

## 11. What the plan does well

To avoid the impression that this review is only critical:

- The "verification without blocking the batch" framing (line 87-104) is
  the correct separation of machine checks from BO confirmation.
- The status disclaimer ("proposed implementation contract, not an
  implemented command or activation", line 3) correctly preserves the
  parent plans' status.
- The hard rule "never auto-merge workers" (line 62) and "Confirmed fields
  remain intact; changed values become proposed corrections" (line 65)
  are consistent with `services.py:230-237` and `real-data-rules.md` §6.
- The acceptance line "all sensitive reads/exports are audited" (line 162)
  is the right place to add the Art. 32(1)(d) cadence.
- The plan correctly defers the draft service contract (line 109-112) rather
  than claiming it exists.

---

## 12. Sources

### Django / Python

- https://docs.djangoproject.com/en/stable/howto/custom-management-commands/
- https://docs.djangoproject.com/en/stable/howto/custom-management-commands/#accepting-optional-arguments
- https://docs.djangoproject.com/en/stable/howto/custom-management-commands/#command-exceptions
- https://docs.djangoproject.com/en/stable/howto/custom-management-commands/#management-commands-and-locales
- https://docs.djangoproject.com/en/stable/ref/django-admin/
- https://docs.djangoproject.com/en/stable/ref/django-admin/#django-admin-help
- https://docs.djangoproject.com/en/stable/topics/db/transactions/
- https://docs.djangoproject.com/en/stable/ref/databases/#transactions
- https://docs.djangoproject.com/en/stable/ref/databases/#queryset-select-for-update-not-supported
- https://docs.djangoproject.com/en/stable/ref/databases/#row-locking-with-queryset-select-for-update
- https://docs.djangoproject.com/en/stable/ref/databases/#mysql-isolation-level
- https://docs.djangoproject.com/en/stable/ref/models/expressions/#django.db.models.F
- https://docs.djangoproject.com/en/stable/ref/settings/#std-setting-STORAGES
- https://docs.djangoproject.com/en/stable/ref/files/storage/
- https://docs.python.org/3/library/tempfile.html
- https://docs.python.org/3/library/tempfile.html#tempfile.mkstemp
- https://docs.python.org/3/library/tempfile.html#tempfile.mktemp
- https://docs.python.org/3/library/os.html#os.replace
- https://docs.python.org/3/library/os.html#os.fsync

### GDPR

- https://eur-lex.europa.eu/eli/reg/2016/679/art_4/oj/eng (Art. 4(5), (7), (8), (12))
- https://eur-lex.europa.eu/eli/reg/2016/679/art_5/oj/eng (Art. 5(1)(c), (f); 5(2))
- https://eur-lex.europa.eu/eli/reg/2016/679/art_22/oj/eng (Art. 22 + Recital 71)
- https://eur-lex.europa.eu/eli/reg/2016/679/art_25/oj/eng (Art. 25(2))
- https://eur-lex.europa.eu/eli/reg/2016/679/art_28/oj/eng (Art. 28(3))
- https://eur-lex.europa.eu/eli/reg/2016/679/art_30/oj/eng (Art. 30(1), (2))
- https://eur-lex.europa.eu/eli/reg/2016/679/art_32/oj/eng (Art. 32(1)(a), (b), (d); Recital 78)
- https://eur-lex.europa.eu/eli/reg/2016/679/art_33/oj/eng (Art. 33(1), (2), (5))

### Czech DPA (ÚOOÚ)

- https://uoou.gov.cz/verejnost/qa-otazky-a-odpovedi/k-vyzadovani-souhlasu
- https://uoou.gov.cz/media/clanky/dokumenty/prokazovani-totoznosti-a-zpracovani-osobnich-udaju-1.pdf

### ČSSZ

- https://eportal.cssz.cz/web/portal/-/sluzby/zadost-o-urceni-pouzitelnych-pravnich-predpisu-pro-zamestnance-pojistenec

### Project documents

- `plans/2026-09-08-local-a1-automation.md` (reviewed)
- `plans/PLAN-WORKERS.md`
- `plans/PLAN-WORKERS-MIGRATE-TO-DB.md`
- `plans/PLAN-A1.md`
- `plans/2026-09-06-ocr-shared-core-local-web.md`
- `plans/2026-09-06-a1-evidence-status-repair.md`
- `plans/INDEX.md`
- `roadmap.md`
- `AGENTS.md`
- `docs/security/real-data-rules.md`
- `docs/operations/git-delivery.md`
- `portal/release1a/models.py`
- `portal/release1a/services.py`
- `portal/release1a/document_intake.py`
- `portal/release1a/document_storage.py`
- `portal/release1a/j4_artifacts.py`
- `portal/release1a/management/commands/activate_reviewer.py`
- `scripts/finalize_a1.py`
- `.agents/skills/a1-pdf-production/SKILL.md`
- `.opencode/skills/market-research-evidence/SKILL.md`

---

## 13. Reality check — current DB / JSON / CSV state vs the plan

This section compares the canonical, synthetic data sources in the
project (the public `tests/fixtures/release_1a/` corpus, the public
`config/institutions/` corpus, the `tests/fixtures/release_1a/review_orgonik_zivot.csv`
fixture, and the two local SQLite databases) against the data shape the
plan assumes. **All numbers are read from local files and databases at
review time** — no real-data paths were opened.

### 13.1 Database landscape

Two local SQLite databases exist:

| File | Settings module | Owner | Size | Last modify |
|---|---|---|---|---|
| `db.sqlite3` (root) | `portal.settings` | default / developer | 581 KB | 2026-09-07 |
| `runtime/portal/synthetic-review/db.sqlite3` | `portal.settings_synthetic_review` | synthetic-review env | 618 KB | 2026-09-07 |

Both are gitignored. PostgreSQL settings live only in
`portal/settings_document_tests.py` and are used for disposable test
clusters (no persistent PostgreSQL backend is configured).

**`db.sqlite3` (root):** migrations applied, **all release1a_* tables
are empty** (0 workers, 0 documents, 0 OCR runs, 0 cases, 0
assignments, 0 organisations, 0 users). The root DB is an empty
migration-target, not a populated database.

**`runtime/portal/synthetic-review/db.sqlite3`:** populated with seed
data from the synthetic acceptance run, but stopped at migration **0009**.
Migrations `0010_a1case_j4_minimum.py` … `0013_alter_a1case_visual_confirmed_by.py`
exist on disk and are recorded as code-only (per
`plans/PLAN-A1.md:78-127` and `docs/operations/git-delivery.md:5-9`),
but **none of those columns** exist in this database:

| Migration on disk | Column(s) introduced | Present in synthetic-review DB? |
|---|---|---|
| `0010_a1case_j4_minimum.py` | `A1Case.source_snapshot_json`, `A1Case.is_stale`, `A1Case.receipt_build_id`, `A1Case.receipt_git_commit`, `A1Case.notes` | **No** |
| `0011_a1case_artifact_evidence.py` | `A1Case.artifact_reference`, `A1Case.artifact_dependencies`, `A1Case.prepared_artifact_hash` change | `prepared_artifact_hash` only |
| `0012_a1case_confirmation_evidence.py` | `A1Case.visual_confirmed*`, `A1Case.evidence_documents`, `A1Case.evidence_notes` | **No** |
| `0013_alter_a1case_visual_confirmed_by.py` | `visual_confirmed_by` reverse relation | **No** |

`PRAGMA table_info('release1a_a1case')` confirms only the original
columns plus `prepared_artifact_hash`. **Any code path added by the
plan that reads `is_stale`, `source_snapshot_json`, `visual_confirmed*`,
or `evidence_*` will raise `OperationalError: no such column` against
this database.** Before any coordinator work, the synthetic-review DB
must run `makemigrations` (it is already in sync per `git-delivery.md:83`)
**and `migrate`** to apply migrations 0010-0013.

### 13.2 Synthetic-review DB contents (the only populated database)

| Table | Rows | Notes |
|---|---|---|
| `release1a_organization` | 3 | `org-synthetic-alpha` (TESTOVACÍ s.r.o.), `org-synthetic-beta` (FIKTIVNÍ Bau GmbH), `org-synthetic-gamma` (UKÁZKOVÁ Agentura a.s.) |
| `auth_user` | 7 | 1 active superuser (`pav.kaspar@gmail.com`); 6 inactive synthetic reviewers |
| `mfa_authenticator` | 1 | one TOTP enrollment |
| `release1a_membership` | 7 | all `active=1`; role distribution: 2× admin, 4× operator, 1× viewer |
| `release1a_worker` | 4 | **all `state='draft'`**; **all `activity_profile='employee'`** |
| `release1a_assignment` | 5 | **all `state='planned'`**; **all `activity_label=''`** |
| `release1a_a1case` | 2 | both `readiness='blocked'`, `prepared_artifact_hash=''`, `external_status='not_submitted'`, `source_hash='synthetic'` (placeholder) |
| `release1a_document` | 4 | `opaque_key` set; **no associated `OcrRun`, no `DocumentVersion`, no `DocumentClassification`** |
| `release1a_ocrrun` | 0 | **the canonical intake pipeline has not been run against this DB** |
| `release1a_documentversion` | 0 | |
| `release1a_documentclassification` | 0 | |
| `release1a_fieldproposal` | 0 | |
| `release1a_fielddecision` | 0 | |
| `release1a_documentregionassociation` | 0 | |
| `release1a_workeridentityrevision` | 0 | |
| `release1a_intakesession` | 0 | |
| `release1a_intakesession_ocr_runs` | 0 | |
| `release1a_reviewtask` | 0 | |
| `release1a_statusevent` | 0 | |
| `release1a_auditevent` | 2 | |
| `release1a_authauditevent` | 83 | login / TOTP / authorisation activity |
| `release1a_release1areview` | 12 | 4 sections × 3 sessions |
| `release1a_release1areviewsession` | 3 | |
| `release1a_release1aacceptance` | 0 | REV-002 has never been recorded |

The synthetic-review DB is a **review-shell, not an intake DB**. The
J2/OCR pipeline has never been exercised on it. This is consistent with
the roadmap's "M2 review environment implemented; broader M3 OCR
workflow pending" status (`roadmap.md:149`).

### 13.3 Synthetic fixtures vs DB

The fixtures under `tests/fixtures/release_1a/` (declared synthetic by
`manifest.json:5-23` and the `_identifier_expectation` / `_fiction`
keys per record) describe a richer data shape than the DB:

**Workers (`workers.json`, 4 records) vs `release1a_worker` table (4 records):**

| Field | Fixture (`workers.json`) | DB model (`Worker`) | Match? |
|---|---|---|---|
| id / organisation_id | `worker-synthetic-01`, `org-synthetic-alpha` | integer PK, FK to `Organization` | DB drops the synthetic slug |
| first_name / last_name | ✓ | `given_name`, `family_name` | ✓ |
| birth_date | ✓ | ✓ | ✓ |
| **nationality** | `"CZ"` / `"DE"` | — | **Missing in DB** |
| **personal_id_number** (rodné číslo / Personalausweis) | `"9001010007"`, `"DE-SYNTH-080392"` | — | **Missing in DB** |
| **id_document_type** | `"občanský průkaz"`, `"Personalausweis"` | — | **Missing in DB** |
| **id_document_number** | `"SYNTH-OP-001"` … | — | **Missing in DB** |
| **address: street / city / postal_code / country** | ✓ (nested) | — | **Missing in DB** |
| **status** | `"active"` / `"inactive"` | `state` enum: `draft` / `active` / `archived` | partial (different vocabulary) |
| **employment_type** | `"OSVČ"` / `"zaměstnanec"` | `activity_profile` enum: `employee` / `self_employed` | partial (different vocabulary) |
| created_at | `"2026-04-01"` | — | **Missing in DB** |

Comparing the **values** of the 4 shared records:

| Worker | Fixture employment_type | DB activity_profile | DB state |
|---|---|---|---|
| `worker-synthetic-01` Novotný | `OSVČ` | `employee` ⚠ | `draft` |
| `worker-synthetic-02` Králová | `zaměstnanec` | `employee` ✓ | `draft` |
| `worker-synthetic-03` Müller | `zaměstnanec` | `employee` ✓ | `draft` |
| `worker-synthetic-04` Dvořák | `OSVČ` | `employee` ⚠ | `draft` |

Two workers' `activity_profile` does **not** match the fixture
(`Novotný`, `Dvořák`). All four are `draft` even though the fixture
declares three as `active` and one as `inactive`. The DB row count
matches but the values diverge — the synthetic-DB seed was authored
independently of `workers.json`.

**Assignments (`assignments.json`, 5 records) vs `release1a_assignment`
table (5 records):**

| Field | Fixture | DB | Match? |
|---|---|---|---|
| id | `asgn-synthetic-01` | integer PK | DB drops slug |
| worker_id, organisation_id | ✓ | FK | ✓ |
| workplace | ✓ | `workplace_label` | ✓ |
| **role** | `"Elektrikář"`, `"Svářeč"`, `"Tischler"` | `activity_label` (always empty) | **Values differ** |
| **partner_name** | ✓ | — | **Missing in DB** |
| start_date / end_date | ✓ | `start` / `end` | ✓ |
| **status** | `"active"` / `"planned"` | `state` enum (`planned`, `active`, `completed`, `cancelled`) | **All 5 are `planned`** in DB |
| **overlap_allowed** | ✓ | — | **Missing in DB** |
| **a1_period_ambiguous** | ✓ | — | **Missing in DB** |
| **overlap_with** (FK to other assignment) | `asgn-synthetic-04.overlap_with=asgn-synthetic-01` | — | **Missing in DB** |
| created_by / created_at | ✓ | — | **Missing in DB** |

The DB `activity_label` column is **always empty**. The `role` /
`partner_name` fields are lost. The `overlap_with` reference in
`assignments.json:62` (fixture 4 overlaps with fixture 1, intentionally)
has no DB counterpart — the plan's "Assignment overlap" service
(`portal/release1a/services.py:99-106`) cannot reason about ambiguity
without an overlap-pair column or a join table.

### 13.4 CSV column set vs Worker / Assignment models

`scripts/finalize_a1.py:46-58` declares 44 CSV columns
(`CSV_FIELDS`). Grouped by purpose and compared to model fields:

| CSV column | Purpose | Worker / Assignment model column |
|---|---|---|
| `employee_id` | worker PK | `Worker.id` (FK) |
| `source_scans` | scan references | | |
| `surname`, `given_name`, `dob`, `birth_place`, `nationality`, `sex`, `insurance_number` | worker identity | `Worker.family_name`, `Worker.given_name`, `Worker.birth_date` only (3 of 7) |
| `street`, `house_number`, `city`, `district`, `postal_code`, `country_code` | worker residence | | **No model column exists** |
| `status_profile` | self-employed vs posted | `Worker.activity_profile` (different vocabulary) |
| `activity_name`, `activity_address` | Section 5 policy | | **No model column exists** |
| `employment_id` … `employment_country_code` (7 cols) | Section 4 employment | | **No model column exists** |
| `resolved_ossz`, `institution_profile` | institution | | **No model column exists** (referenced by `attach_a1_artifact` via `validate_review`) |
| `document_id` | certificate number | `A1Case` has none; lives only in CSV |
| `start_date`, `end_date`, `issue_date`, `signed_by` | certificate dates + signatory | | **No model column exists** |
| `identity_reviewed`, `certificate_reviewed`, `approved_for_pdf`, `pdf_created`, `validated_by_user` | review flags | `A1Case.readiness` + `A1Case.external_status` only |
| `activity_source` / `*_source_status` (×3 subjects) | authoritative source markers | | **No model column exists** |
| `comments` | human note | `A1Case.notes` |

**Conclusion of the diff:** of 44 CSV columns, only **5** map directly
to model columns (`Worker.given_name`, `Worker.family_name`,
`Worker.birth_date`, `Worker.activity_profile`, `A1Case.readiness`).
The other 39 columns have no home in the current `portal.release1a`
schema. The plan's claim that "A1 generation reads a single source of
truth — the same records the dashboard displays and the operator edits
through the worker detail view" (`plans/PLAN-WORKERS-MIGRATE-TO-DB.md:14-15`)
is **not yet true** at the schema level. DB-MIG-1/2 are the right
milestones for these columns but the plan does not enumerate them.

### 13.5 Canonical review CSV (orgonik_zivot fixture)

`tests/fixtures/release_1a/review_orgonik_zivot.csv` is a 4-row CSV
formatted exactly to `CSV_FIELDS`. All four rows are
`employee_multi_state` and use `validated_by_user=0` and
`*_source_status=PROVISIONAL`. None passes the readiness gate defined
in `scripts/finalize_a1.py:183-235` (every row has at least the
`activity_source_status != AUTHORITATIVE` blocker, the
`identity_reviewed/certificate_reviewed/approved_for_pdf/validated_by_user`
blockers, and the missing `issue_date`/`signed_by` blockers). This is
the correct shape for the gate but the `_orgonik_zivot` PDF artefacts
under `tests/fixtures/release_1a/orgonik_zivot_pdfs/` were generated
when the gate was less strict.

`tests/fixtures/release_1a/workers_orgonik_zivot.json` and
`assignments_orgonik_zivot.json` extend the corpus with another set of
4 workers / 4 assignments in the same family
(`SYNTHETICKÁ PRACOVNÍ AGENTURA s.r.o.`), using
`status_profile=employee_multi_state`. They are **not** in the
synthetic-review DB.

### 13.6 Institution profile coverage

`config/institutions/*.json` (11 profiles):

| Profile | Code | `review_status` |
|---|---|---|
| brno | `613` | `VERIFIED` |
| decin | `511` | `VERIFIED` |
| frydek-mistek | `886` | `VERIFIED` |
| kladno | `TBD` | `PROVISIONAL` |
| louny | `TBD` | `NEEDS_VERIFICATION` |
| most | `557` | `VERIFIED` |
| novy-jicin | `888` | `VERIFIED` |
| plzen | `444` | `VERIFIED` |
| praha | `511` | `VERIFIED` |
| teplice | `558` | `VERIFIED` |
| usti-nad-labem | `TBD` | `PROVISIONAL` |

Totals: **8 VERIFIED, 2 PROVISIONAL, 1 NEEDS_VERIFICATION**.

`scripts/finalize_a1.py:36-45` `PROFILE_BY_OSSZ` references 8 OSSZ
codes; all 8 have a profile on disk (no gap). The Louny and Ústí
nad Labem entries are **not yet final** (`code: TBD`, status
`NEEDS_VERIFICATION` / `PROVISIONAL`); readiness will reject rows that
reference them unless the operator populates `code` and re-verifies.

The top-level `config/institution.json` file is **VERIFIED PRODUCTION
DATA** (file self-description, line 1) for the current Teplice-issued
package (`OSSZ Teplice`, certificate `N65021S558/2025/DE`, valid
`26.09.2025 → 25.09.2026`, signed by Milena Vitíková,
issued `20.10.2025`). The CSV_FIELDS row values for `resolved_ossz`,
`institution_profile`, `start_date`, `end_date`, `issue_date`,
`signed_by` are sourced from this file when the row matches
`OSSZ Teplice` (`scripts/finalize_a1.py:115-150`). The `provision`
flag in `load_profile(..., provisional=True)` (line 252-273) allows
placeholder fields in `load_profile` but readiness still rejects rows
with `*_source_status != AUTHORITATIVE` regardless of provision.

### 13.7 Implications for the plan

These are the data-shape implications for the plan, **not** amendments:

1. **DB-MIG-1 must enumerate the missing worker columns.** The plan
   says "Reuse Worker, Document, DocumentVersion, OcrRun, FieldProposal,
   FieldDecision, WorkerIdentityRevision, Assignment and A1Case"
   (plan line 35-36). Of the 39 CSV columns with no model home, **at
   least the following are required for the plan to satisfy its own
   "single source of truth" claim**:
   `Worker.nationality`, `Worker.sex`, `Worker.insurance_number`,
   `Worker.address_*`, `Worker.id_document_*`, `Worker.status`
   (re-named from `state`), and either a separate
   `WorkerActivity` model or new columns on `Worker` for
   `activity_name` / `activity_address`. Until those land, the
   coordinator will write to `Worker` but lose 6 of 7 identity columns.

2. **DB-MIG-2 must enumerate the missing A1Case columns.** The plan
   must add `A1Case.document_id`, `A1Case.start_date`, `A1Case.end_date`,
   `A1Case.issue_date`, `A1Case.signed_by`, `A1Case.activity_source*`,
   `A1Case.certificate_source*`, `A1Case.signatory_source*`. Today
   these all live only in the CSV; the readiness gate reads them from
   the CSV (`scripts/finalize_a1.py:185-205`) and would reject any
   `A1Case` row that does not have a matching CSV row.

3. **`Assignment` is missing `role`, `partner_name`, `overlap_with`,
   `a1_period_ambiguous`.** The plan's "Resolve assignment and A1
   inputs from existing records or explicit operator defaults" (plan
   line 68) does not name where `role` (the Section 4 job title)
   goes. Today `Assignment.activity_label` is always empty in the DB
   (see §13.3). The plan must add `Assignment.role_label`,
   `Assignment.partner_name`, and either an `Assignment.overlap_with`
   FK or a join table.

4. **The synthetic-review DB will not accept the proposed code.** All
   proposed coordinator paths that touch `A1Case.is_stale`,
   `A1Case.source_snapshot_json`, `A1Case.visual_confirmed*`,
   `A1Case.evidence_*`, `A1Case.notes`, `A1Case.receipt_*` will fail
   with `OperationalError` against this DB until migrations 0010-0013
   are applied. The plan does not mention the migration step.

5. **The synthetic fixtures and the synthetic-review DB are not in
   sync.** Worker `activity_profile` and `state` differ from
   `workers.json`; `Assignment.activity_label` is empty for all 5
   records; only `Worker.given_name/family_name/birth_date` and the
   date range match. The plan should not assume the DB and fixtures
   are interchangeable; its synthetic acceptance must rebuild the DB
   from `tests/fixtures/release_1a/` and the institution profiles in
   one transaction, not rely on the current seed.

6. **No OCR runs exist in the synthetic-review DB.** The plan's
   "automated processing" (plan step 4) cannot be exercised against
   this DB without first seeding `Document → DocumentVersion → OcrRun`
   rows. The plan's synthetic acceptance must include that seeding
   step or assert the result of seeding, not just inspect an empty
   table.

7. **The synthetic-DB seed was authored independently of
   `workers.json`.** The fact that the four worker names match but
   `activity_profile` does not suggests a hand-rolled `loaddata` /
   shell session rather than a fixture-driven loader. The plan should
   name the loader it expects (`scripts/seed_release1a_dev.py` exists
   at `scripts/seed_release1a_dev.py`; the plan does not reference it).

8. **Institution profile coverage is complete but `code: TBD` blocks
   final approval.** Two of 11 profiles (`kladno`, `usti-nad-labem`)
   have placeholder codes; one (`louny`) is `NEEDS_VERIFICATION`.
   The plan should not assume institution profile readiness is
   satisfied; rows referencing these OSSZ branches will fail
   readiness until the operator completes them.

---

## 14. Conclusion

The plan is **structurally sound but operationally incomplete**. Its
narrative is correct; its implementations collide with the existing
storage layer, lack the data-model primitives it depends on, and do not
name the GDPR/Czech-law commitments the new automated processor must
satisfy. The §13 diff confirms that **39 of 44 CSV columns have no
model home** and that the only populated database is a review-shell
that has never run the OCR pipeline and is missing migrations 0010-0013.

With the 15 amendments in §10 applied, plus the 8 data-shape additions
in §13.7, the plan becomes implementable. Without them, the first day
of implementation will surface every one of the conflicts named above.

No status, gate, or catalog entry has been changed by this review. The
plan remains a proposal; the implementation contract is unchanged.