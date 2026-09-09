# Prompt for the Práce application agent on s62

Work inside `/var/www/prace-v-nemecku.tvoje.info`. Review and independently test the infrastructure deliveries against this application's actual requirements. Fix scoped application tests/integration defects you can reproduce; return infrastructure-owned defects as precise work orders. Preserve ongoing dirty/untracked work and the existing activation gates.

## Read first

Read this project's AGENTS.md, roadmap.md, plans/INDEX.md, PLAN-INFRA, docs/operations/runtime-manifest.md, the release inventory work order and applicable real-data rules. Then read the neighboring receipt files in this delivery directory: `INFRA-HANDOFF.md`, `OCR-ROLLOUT.md`, `HOST-READINESS.md`, `SECRETS-DATABASE.md`, `VALIDATION.json`. These are infrastructure snapshots, not application authority or deployment approval. Recheck state before making claims.

Infrastructure commits: `29885b74` + `350fe134` diagnostic contracts; `1a8fdefa` public/private separation; `3e552bce` exact configuration permissions; `38140b36` optional OCR and public APT-key repair. Infrastructure branches remain local/unmerged. Do not assume an unrelated installed diagnostic script matches those revisions.

## What was delivered and independently checked

- Public nginx holding page is separated from Django: `/` and `/ready`200; tested private paths404 through s61 HTTPS, certificate validation enabled. The public `/ready` proves only placeholder liveness.
- `.env`0600 pavel:www-data, contents untouched. This does not prove a future dedicated service identity has the correct access.
- Tesseract5.5.0 with ces/deu/eng/osd installed through scoped Ansible; RapidOCR3.9.2/ONNX1.29.0 already present. Both executed four fixed synthetic PNGs inside isolated network namespaces. Both made language errors; no automatic application fallback was wired.
- Expired public GitLab Runner repository metadata key refreshed after full fingerprint/expiry validation. Strict APT refresh passed. No GitLab credentials, deploy keys or container configuration changed.
- Package and key Ansible second applies changed0. Post-install Python pip check, nginx, public/private routing and permissions passed.
- Ten application readiness tests passed with disposable in-memory DB and network disabled. Existing Playwright1.62/Chromium launched and rendered a synthetic DOM offline. This is browser tooling proof, not login/MFA/J1–J4 acceptance.
- SOPS delivery, native PostgreSQL provisioning, migrations, durable runtime supervision and real recovery remain unimplemented or unproven as described in the receipts.

## Execute the application review

1. **Bind evidence to source and environment.** Record timestamp, HEAD and modified/untracked source scope without dumping sensitive path inventories or document contents. HEAD32daa23 alone does not include the tested application delivery. Inspect the current runtime manifest and keep production/test/synthetic-review databases distinct.

2. **Dependencies and OCR.** Run `venv/bin/python -m pip check`, `tesseract --version`, `tesseract --list-langs`. Verify the actual application's selected model files, hashes and read access. Use the existing document-core adapters and synthetic fixtures to run RapidOCR and Tesseract with network disabled, bounded execution and no model downloads. Add RapidOCR to the existing benchmark candidate list and replace its nonexecuting placeholder with honest executed results where in scope. Compare Czech/German/mixed text, skew, dates/identifiers and representative PDF rasterization; record field errors, per-engine latency and memory. Installed Tesseract does not cause the app to invoke it: define/test the adapter, unavailable/failed-primary behavior, fallback failure, timeout and manual-review state. Avoid silently accepting low-quality OCR, inferring model agreement as truth or introducing a replacement framework.

3. **Readiness and database tests.** This command was inspected and rerun successfully by infrastructure:

   ```bash
   env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_USER \
     PYTHONDONTWRITEBYTECODE=1 DJANGO_SETTINGS_MODULE=portal.settings_document_tests \
     timeout 180 unshare --user --map-root-user --net \
     venv/bin/python -m django test tests.m2.test_readiness --noinput -v 1
   ```

   Recheck the settings source before running it. It selects in-memory SQLite when PostgreSQL test variables are absent, with disposable storage/cache. Extend focused tests for actual storage/model/release/timeouts as appropriate. Preserve DB-down503, pending migrations503 across all installed apps, sanitized failures, unsafe methods and no-cache behavior. Never run bare `migrate`, `--fake`, a persistent seed/reset script or destructive schema repair to make readiness green. Read-only persistent preflight requires an explicitly identified target and secure configuration; protect SQLite from accidental file creation if the target is missing. PostgreSQL transition tests use a disposable project-owned cluster and historical MigrationExecutor states.

4. **Browser tests.** Inspect existing Python/Node smoke code before execution. Fix the Python smoke test's false pass: urllib follows redirects and the script accepts anonymous `/review/`200. Assert the redirect/login destination and absence of protected content; test that an intentionally exposed review page fails the check. Do not call HTTP-only checks Playwright tests. Use actual Chromium for unauthenticated access, invitation-only login, TOTP, logout, organization isolation, protected upload/download, OCR proposal review and relevant J1–J4 flows. Test mobile/desktop and console/page errors. Existing Node smoke requires SYNTHETIC_REVIEW_LOGIN/PASSWORD/TOTP; obtain only authorized synthetic credentials through the approved mechanism, never log them or reset an existing account for convenience. Prevent raw console errors, screenshots, traces, videos, HTML or storage state from capturing secrets/real data. Capture only reviewed synthetic artifacts. Report unsupported journeys as NOT_RUN, not PASS.

5. **Runtime/access.** A disposable development-server smoke on loopback can be used with an explicitly isolated test DB/settings and guaranteed cleanup, if the app test contract supports it. Do not bind0.0.0.0, reuse a persistent verification DB implicitly, start a durable host service or activate real inputs. Verify actual loopback `/health/` and `/readiness/` separately from public nginx `/ready`. Confirm no Django listener becomes reachable through the public apex. Do not mark `real_data=false` as proof of isolated storage: inspect configuration and test forbidden access. Host/TLS/private-route changes return to infrastructure.

6. **Permissions and logs.** As the actual intended identity, test access to synthetic read-only inputs/models and write-only required runtime/cache/storage paths. Never weaken `.env`, make model/config directories world-writable or recursively chown the project. Log correlation IDs, engine/version, duration and sanitized reason codes; not OCR text, tokens, filenames containing personal data or document fields. Generate a nonsecret marker; ask infrastructure to correlate it in Loki and validate rotation/alerts. A browser console without errors is not server-log coverage. Absence of logs or insufficient journal permission is UNKNOWN/PROBE-BLOCKED, not healthy.

7. **SOPS and database contract.** Read SECRETS-DATABASE.md. SOPS is planned controller-side decryption with only required fields delivered to the chosen runtime identity. Do not copy private age keys/full vaults to s62 or core; do not use shell eval/source on decrypted data; do not expose secrets in argv, diffs, debug, caches or reports. Do not implement a second secret store in the application. Supply names/types/requiredness only, then test missing/invalid configuration with dummy values. Infrastructure must provide actual secret references, protected files and identities before claiming deployed SOPS use. Keep schema migration, SQLite→PostgreSQL data transfer and restore as separately rehearsed procedures. Never attach to another application's DB or start an unidentified native cluster. Supply socket/host/db/user/SSL and migration-role requirements without passwords.

8. **Infrastructure return contract.** Specify the exact synthetic target; complete immutable release inventory; settings/entrypoint/static contract; runtime identity; protected read/write roots; model manifest; inline versus worker execution (Q_CLUSTER/dispatch currently absent); upload/page/pixel/time/concurrency limits; health semantics and timeouts; DB source/target identities and migration frontier; coherent DB/files recovery assertions; proposed numeric RPO/RTO, retention and notification ownership. Engineering/infrastructure choose technical defaults; Jan confirms business workflow facts. Separate proposals from accepted settings.

## Return deliverables

Write a scoped application review report in the project's normal operations/review documentation. For each requirement use PASS / FAIL / BLOCKED / NOT_RUN, with exact command, exit code, UTC timestamp, source identity and artifact path. Include:

- Reproduced defects and fixes with focused regression evidence.
- Real OCR/Playwright results, including errors and limitations.
- Confirmed versus missing SOPS, DB, routing, permissions and logging interfaces.
- Updated runtime manifest and a prioritized infrastructure work order for remaining host-owned tasks.
- Clear gate status: no automatic ENG-001, REV-002, REV-003, A1 promotion or real-data activation from these checks.

Do not commit/push application changes unless separately authorized. Do not send credentials, scans or full runtime logs back to infrastructure. Keep this receipt directory unchanged; put your review results in separate application-owned files.
