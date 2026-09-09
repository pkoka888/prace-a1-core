# Application review of infrastructure delivery — 2026-09-07

Parent: PLAN-INFRA; related OCR-CORE-7/12/13/14 and existing J2/J4 checks.
Implementation: scoped fixes integrated, uncommitted. Synthetic acceptance: results
below. Deployment: BLOCKED. The original checksummed packet is unchanged.

## Source identity and receipts

HEAD `32daa23a217039ccf79a25027481e1d582b64d25` is only the base; the tested tree
is dirty and untracked dependencies are included. A 334-file safe source inventory
was captured at 02:45:45 UTC in
`runtime/portal/infra-review-20260907/source-inventory.json`, SHA-256
`07adbee4d26af593f5b3096b7478ca7bb4d13b62dcd5a13c43e6e6793bebcf24`.
It covers application/scripts/tests/config/templates/planning, not private data or
unknown research. This metadata snapshot is not approval to publish every file.
Dependencies are separately inventoried; engine receipts bind models and fonts.
After an authorized release, rerun from the exported Git object before claiming
release completeness. Test receipts concern the actual working source, not HEAD.

Browser receipt: `runtime/portal/infra-browser-6cbeae7c90da4cc6aa9ed15b7333251c/receipt.json`,
SHA-256 `7ba3ac898f0a39b376121d35a2bad71b992eaa7e5b0f06656c65a4335e183828`.
Local monitoring operation ID `accdcdaf-08dc-424e-bd7e-63d89714ad94`, emitted at
02:42:11 UTC, is in `marker.json`. It has not been correlated by infrastructure.

## Findings and corrections

- Six packet checksums match. Infrastructure's core 104 tests/14 validators and
  Ansible/APT/idempotency receipts remain attributed evidence from its repository;
  they were not rerun as application tests or treated as deployment approval.
- Fixed the Python smoke's false pass: anonymous `/review/`200 now fails. The test
  requires a same-origin login redirect and login form, with a negative exposed-page
  fixture. HTTP probes are labelled separately from actual Chromium execution.
- Replaced smoke startup against persistent verification settings with a disposable
  browser harness. It creates fictional accounts/TOTP and isolated storage/database,
  blocks external browser requests and runs in an offline namespace with loopback.
- Fixed `ocr_field_review` URL keyword `pk` → `document_pk`, matching the view and
  both queue templates. The former route could raise TypeError/NoReverseMatch.
- Added opt-in normalized Tesseract and two-attempt local fallback modules. Intake
  still selects RapidOCR. Failure/timeout/low-quality outcomes remain proposals or
  failures; no engine agreement is identity or acceptance evidence. The fallback is
  restricted to a single-threaded Linux CLI process and not wired into Django.
- Replaced the benchmark's nonexecuting placeholder with fixed synthetic execution
  and engine/decoder/font/model/source hashes. Other benchmark candidates stay
  NOT_RUN; this is not invoice-benchmark certification or calibrated OCR accuracy.
- Existing synthetic review settings inherit shared document storage/cache and
  DEBUG=True. A separate SQLite file and synthetic marker do not prove isolation.
  This target is not cleared for startup; use disposable tests until confined
  supervised settings and infrastructure permissions are implemented.
- Packet broker claim corrected: django-q2 dependency exists, but no Q_CLUSTER or
  dispatch exists. A lease is not a hard OCR timeout. No queue provisioning is requested.

## Acceptance evidence

All data is generated fiction. Commands used the repository venv and no provider
calls. Review date is 2026-09-07 UTC. Primary run artifacts are under
`runtime/portal/infra-review-20260907/`; engine receipts have their own run UUIDs.
Recorded log collection times are not invented process start times. No full-repo
PASS claim is made. The live persistent release verifier was NOT_RUN.

| Requirement | Status | Result / artifact |
|---|---|---|
| Packet integrity | PASS | sha256sum -c SHA256SUMS: 6/6, exit 0 |
| Python dependencies | PASS | pip check exit 0, no broken requirements; dependencies.json |
| OCR binary/languages | PASS | Tesseract 5.5.0, ces/deu/eng/osd; RapidOCR 3.9.2 / ONNX 1.29.0 |
| Local configuration permission metadata | PASS | .env mode0600, pavel:www-data, link count1; no content read |
| A1 synthetic regressions | PASS | 157 tests, 19 subtests, 62.23s; a1.log; exit0 |
| Affected M2/readiness regressions | PASS | 43 tests, 96.951s; m2.log; exit0 |
| Fresh/historical PostgreSQL | PASS | 15 tests, 49.167s; postgres.log; exit0; disposable cluster only |
| Model/migration drift | PASS | makemigrations --check --dry-run: no changes, exit0 |
| HTTP false-pass regression | PASS | 6 tests, 3.29s; exit0 |
| Document core / HTTP / benchmark regressions | PASS | 119 tests, 107.90s; document-core-accepted.log; exit0 |
| Actual Chromium | PASS scoped journey | 1 integrated test, 22.607s; source-bound browser receipt |
| Planning / approvals | PASS | 24/24 checks; 34 catalog IDs; 9 approval records; assets current |
| Actual OCR | PASS execution only | Five fixed cases per engine; receipts below |
| Public HTTPS routing from this session | BLOCKED | public-edge.json: all probes PROBE_BLOCKED; no TLS bypass |
| Service identity access, SOPS, native DB | NOT_RUN | Target/provisioning not established; pavel access is not service proof |
| Loki, rotation, alerts | BLOCKED | Local marker only; external correlation absent |
| Durable supervision, restore, production migrations | NOT_RUN | Separate infrastructure authorization and target required |
| Full J4/release acceptance | NOT_RUN | Focused tests do not open ENG-001/REV gates |

Primary commands (stdout/stderr captured only for synthetic tests):

```bash
sha256sum -c SHA256SUMS  # cwd: docs/operations/infra-review-20260907T0230Z
venv/bin/python -m pip check
tesseract --version
tesseract --list-langs
stat -c 'mode=%a owner=%U group=%G links=%h' .env
env -u A1_PRIVATE_DIR timeout 300 venv/bin/python -m pytest -q tests/test_a1_stabilization.py tests/test_finalize_a1.py tests/test_a1_employee_delivery.py tests/test_a1_quality_gate.py tests/test_a1_core.py tests/test_a1_private.py tests/test_validate_approvals.py tests/test_a1_cli_journey.py tests/architecture/test_a1_boundary.py tests/test_release_verifier.py
env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_USER PYTHONDONTWRITEBYTECODE=1 DJANGO_SETTINGS_MODULE=portal.settings_document_tests timeout 240 unshare --user --map-root-user --net venv/bin/python -m django test tests.m2.test_readiness tests.m2.test_views tests.m2.test_review_fixes tests.m2.test_release1a_vertical --noinput -v 1
timeout 180 venv/bin/python scripts/test_document_intake.py
env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_USER DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m django makemigrations --check --dry-run
venv/bin/python -m pytest -q tests/test_playwright_smoke.py
```

Public probes used Python urllib with default certificate validation and 10-second
per-request timeout, recording only status for `/`, `/ready`, `/health/`,
`/readiness/`, `/review/`, `/accounts/login/`, `/documents/intake/`. They produced
PROBE_BLOCKED at 02:39:11 UTC. The probe collector exit0 means collection completed,
not routing passed. The infra packet's s61 results remain historical evidence.

## OCR observations

Final fixed-corpus receipts:

- RapidOCR: `runtime/portal/infra-ocr-6ad1cdbe-2921-4ba4-9086-db9b76a06feb/receipt.json`,
  02:43:09 UTC; 0/15 exact labelled-string mismatches, 5.05–6.71s/case,
  initialization1.40s, parent peak RSS549828KiB.
- Tesseract: `runtime/portal/infra-ocr-0f26d57f-450a-4131-96a1-3352cfe22818/receipt.json`,
  02:43:37 UTC; 1/15 mismatch (label capitalization on skewed image),
  0.67–0.84s/case, initialization0.09s, parent RSS114924KiB,
  child peak114720KiB. RSS is process high-water measurement, not per-case allocation.

Cases cover Czech/German/mixed labels, dates, synthetic identifiers, 3° skew and
PDF rasterization. Exact-string presence is a narrow smoke metric, not semantic
field accuracy or document classification acceptance. Earlier exploratory corpus
results and the infrastructure's separate four images contain other errors and
are not comparable accuracy scores. Model hashes match the packet. Keep RapidOCR
default; faster Tesseract is optional, not a reason to waive confirmation.

## Browser acceptance and limits

Real Chromium passed one integrated journey (22.607s, final run began 02:44:24 UTC) using disposable synthetic
settings, a new random-password account and actual TOTP authentication. It covers
health/readiness over loopback, anonymous login routing, invitation-only login UI,
desktop/mobile review layout, organization isolation, synthetic image upload with
real RapidOCR, OCR review URL reverse/GET, association, exact ALFA proposal and
explicit field confirmation, original byte-exact download, foreign-organization
source denial, logout and anonymous download denial. Browser console/page errors
are checked before intentional denied-resource probes; no screenshots, traces,
raw exceptions or persisted credentials are retained.

Invitation issuance and MFA enrollment UI are NOT_RUN (fixture enrollment is not
UI enrollment). J3/J4 creation/approval, final certificate and full release journeys
are NOT_RUN. A test listener with cleanup proves neither a durable supervisor nor
public edge denial. The namespace group mismatch encountered while adding upload
coverage was corrected only on newly created disposable test directories; existing
runtime ownership was preserved.

An initial expanded pytest command failed collection because a new fallback test
used a src import without the repository's standard namespace. It was corrected;
the failed run remains `document-core.log` (exit2), superseded by the final rerun.
No conditional skips or environment PYTHONPATH workaround hide this defect.
A subsequent offline combined run returned 1 failed/118 passed because loopback
was down inside its namespace, preventing the HTTP fixture connection. It is
retained as `document-core-final.log` (exit1). The accepted command explicitly
raises only namespace loopback, leaving outbound network unavailable.

## Remaining work and ownership

The [return work order](../operations/infra-return-work-order-2026-09-07.md) gives
technical proposals, configuration names/types and ownership. Next application
work is confined supervised settings and dummy-value tests, complete bounded
storage/model/release preflight and minimum J4. Infrastructure then supplies an
identified service/DB/secret/access/logging/recovery target under separate approval.
Jan supplies missing/conflicting facts and one consolidated factual confirmation;
application preparation and official A1 issuance remain separate.

No new framework, provider integration, real-data regeneration, file reorganization,
commit, push, host-service change or persistent DB migration occurred in this review.
Retain 34 catalog IDs and existing child task IDs. No automatic ENG-001, REV-002,
REV-003, A1 promotion or real-data activation follows from these results.

## Additional executed commands

```bash
timeout 180 unshare --user --map-root-user --net sh -c 'ip link set lo up && PYTHONDONTWRITEBYTECODE=1 venv/bin/python scripts/playwright_smoke.py'
node --check scripts/smoke_synthetic_review_ui.mjs
env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 timeout 180 unshare --user --map-root-user --net venv/bin/python scripts/run_ocr_benchmark.py --engine rapidocr
env PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 timeout 180 unshare --user --map-root-user --net venv/bin/python scripts/run_ocr_benchmark.py --engine tesseract
env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_USER timeout 240 unshare --user --map-root-user --net sh -c 'ip link set lo up && venv/bin/python -m pytest -q tests/test_document_core tests/test_playwright_smoke.py tests/test_benchmark_experimental.py'
venv/bin/python scripts/generate_planning_asset.py
venv/bin/python scripts/validate_planning.py
venv/bin/python scripts/validate_approvals.py
git diff --check
```

The legacy Node credential-dependent journey was NOT_RUN; syntax validation is
not its functional acceptance. The Python Playwright journey provides the actual
browser evidence. The full live release verifier remains NOT_RUN.

Final acceptance receipt: `runtime/portal/infra-review-20260907/acceptance.json`, collected 2026-09-07T02:49:07.839205+00:00. All listed final commands exited0; the two superseded combined test runs remain recorded above. Planning assets regenerated after source updates; final relative links, packet checksums and diff checks pass. The 334 inventoried source files were rehashed with zero changes after capture.
