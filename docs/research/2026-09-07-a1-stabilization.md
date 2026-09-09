# A1 stabilization acceptance — 2026-09-07

Working-tree implementation on `feat/prace-readiness-plan-2026-08-13`, starting
HEAD `32daa23`. This report supersedes the stabilization-complete claim reviewed
against the initial **5 failed / 33 passed** acceptance run. It does not supersede
human evidence decisions, open engineering gates, or deployment authorization.

## Implemented result

| Area | Behavior and evidence |
|---|---|
| Audit | One full operation UUID; required configured organization and effective OS actor; typed metadata allowlist; locked append preserves existing events and concurrent writers. Partial writes roll back only the current append. An interrupted existing log fails closed. |
| Operation receipts | Required running/completed/failed receipts under protected `a1/receipts/`, mode 0600. Context/write failures block processing. CLI boundaries sanitize malformed JSON, missing policy fields and unexpected errors. Staging is registered before later processing can fail, including interruptions. |
| Publication | Every output confined to the configured protected output subtree; no implicit outside-root allowance. Symlink components, input overlap, existing packages and final destinations are rejected. Exclusive staging and per-destination locks publish a whole directory. Original inputs and previous packages are preserved. |
| Completion failure | Newly published packages are withdrawn if completion persistence fails. If the filesystem also prevents withdrawal, a failed recovery-required receipt and sanitized error are attempted; no success is claimed. QA refuses packages without both a completed generation receipt and terminal completed audit event. |
| QA | All-page fresh decoded RGB pixel comparison at recorded DPI, entirely in memory. Protected render/contact receipts bind PDFs, previews and contact sheets. CLI validation requires the generation manifest and exact PDF hashes, completed receipt and terminal audit evidence; visual recording rechecks these bindings. Whole audit-log hashes are deliberately not dependencies because later events append to that log. |
| Canonical evidence | All three profiles retain explicit activity and employment requirements, independent country values, AUTHORITATIVE sources and acceptance flags. Readiness reports cannot overwrite review, normalized inputs, operator configuration or institution profiles. Louny remains NEEDS_VERIFICATION with an empty full-verification date. |
| Approval scope | New audit/path helpers join existing source-review dependency coverage; a synthetic Git test proves untracked helpers block clean review evidence. No approval flags were changed. |
| Tests and paths | CLI fixtures have unique fictional people and exact cohort/source agreement. Valid generated PDFs replace M2 PDF stubs. Test settings isolate database, cache and fallback storage; original/derivative paths remain distinct. |
| Operator workflow | Technical routing is automatic; Jan supplies missing or conflicting facts and confirms a consolidated summary. Application preparation, submission authorization and issued A1 evidence remain separate. The interface is a subsequent deliverable. |

The repaired three-page template remains unchanged by this stabilization patch.
Its 2,800,789-byte file hash matches the existing repair receipt; that receipt records
six page/DPI comparisons with zero changed pixels outside the repaired interiors.
No compression rewrite or real employee package regeneration was performed.

## Acceptance commands and results

All listed tests use fictional fixtures. These results concern the working tree,
not a committed release or a deployed service.

```bash
venv/bin/python -m pytest -q tests/test_a1_stabilization.py tests/test_finalize_a1.py tests/test_a1_employee_delivery.py tests/test_a1_quality_gate.py tests/test_a1_core.py tests/test_a1_private.py tests/test_validate_approvals.py tests/test_a1_cli_journey.py tests/architecture/test_a1_boundary.py tests/test_release_verifier.py
venv/bin/python -m pytest -q tests/test_document_core
venv/bin/python scripts/test_document_intake.py
DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m django test tests.m2.test_review_fixes tests.m2.test_views tests.m2.test_release1a_vertical --noinput -v 1
DJANGO_SETTINGS_MODULE=portal.settings_document_tests venv/bin/python -m django makemigrations --check --dry-run
venv/bin/python scripts/validate_approvals.py
venv/bin/python scripts/validate_planning.py
git diff --check
```

- Focused A1/QA/approval/boundary/verifier tests: **157 passed, 19 subtests passed**.
- Document core: **75 passed**, including actual local RapidOCR execution.
- PostgreSQL intake: **15 passed** in the final isolated PostgreSQL rerun (34.032s), including historical `0007 → 0009` states.
- Affected M2 portal suites: **33 passed** in the final isolated rerun (90.605s), with explicit storage/cache isolation.
- Model/migration drift: **no changes detected**, using test settings.
- Approval register: **PASS, 9 records**. Planning: **24/24**, 34 catalog IDs retained; planning/approval assets current; final diff and source-link checks pass.

The CLI journey produces three synthetic profile PDFs, nine previews and three
contact sheets at 200 DPI, then requires QA PASS and hash-bound receipts. Separate
pixel tests cover 144/200/300 DPI, re-encoded identical PNGs, last-page changes and
missing/stale artifacts. Concurrency tests use independent processes. Injected
failures cover append I/O, receipt replacement, package publication, completion
audit and rollback; there is no claim of surviving arbitrary storage loss.

An earlier expanded test run was stopped with exit 143 after the pre-existing
release-verifier test invoked the live verification harness and broader tests,
including a route back into verifier testing. That harness invokes recreation of
its in-repository **synthetic verification database**. This interrupted run is
excluded from acceptance. The test now exercises the actual main/exit logic with
isolated dependencies and a guard against subprocess re-entry; its seeder test
inspects the adapter through a mock and no longer requires a pre-seeded database.
This is not evidence that the full live ENG-001 verifier passes.

## Remaining work and operational limits

- Bounded stabilization has passed the listed final isolated reruns and
  planning synchronization. PLAN-A1 and the broader repair child remain active.
- Next engineering work is minimum J4: stored snapshots/artifacts, protected
  preview/download paths and staleness/state behavior. Preserve the sequence
  functioning prerequisites including J4 → ENG-001 → REV-002 → remaining gates → REV-003.
- Authoritative employee/employer/institution/certificate reconciliation remains
  separate from these synthetic tests. No date, identity, certificate or YES flag
  was invented or repaired in private inputs by this patch.
- The actual deployed service/database was not identified or migrated. Fresh and
  historical PostgreSQL migration tests do not establish deployment status.
- Interrupted operations leave a running or failed receipt until recovery; a
  failed completion is never enough for QA acceptance. Manual intervention after
  storage failure belongs to the administrator, not Jan. SIGKILL and storage-loss
  recovery are not equivalent to the caught-interruption tests.
- No commits, pushes, provider calls, framework changes, file reorganization or
  production deployment are part of this delivery. Unknown research artifacts
  remain classified through read-only work orders before any moves or deletion.

## Authoritative direction and handoff

The [operator contract](../architecture/operator-a1-workflow.md) follows the
[ČSSZ application/issuance distinction](https://www.cssz.gov.cz/web/cz/podani-zadosti-o-urceni-prislusnosti-883-2004-987-2009)
and [official application instructions](https://eportal.cssz.cz/documents/20122/35811/SZZVPP_pokyny.pdf/57daae1d-f7a8-7512-c5c1-7a3b5f9e10ca?t=1652879516928).
The retained ONNX backend follows [RapidOCR installation guidance](https://rapidai.github.io/RapidOCRDocs/main/en/install_usage/rapidocr/install/);
installing Tesseract would not repair this pipeline. Historical migration tests
follow [Django's historical-model contract](https://docs.djangoproject.com/en/5.2/topics/migrations/).

Use the [updated work orders](../operations/opencode-work-orders/README.md) for
independent review, explicitly scoped implementation/tests and release inventory.
The [canonical command guide](../../readme-employees-to-a1-form.md) now describes
unique packages, operator context, protected receipts and failure recovery.
