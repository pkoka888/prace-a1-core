# Report — servers-infra-core review of the Práce layout (host server61)

- Project/context host: **server61**, checkout `/workspace/servers-infra-core`
- Reviewed-receiver host: **server62**, `/var/www/prace-v-nemecku.tvoje.info` (the application project)
- Reporting date: 2026-09-16 Europe/Prague; observations UTC on 2026-09-15/16
- Scope: review of the servers-infra-core deliverable referenced below; read-only. No live file on either host was moved or changed by this review.

## Deliverable reviewed

servers-infra-core parallel-review product, committed on server61 (`f8280118`):

- `docs/audits/2026-09-16-prace-layout-and-safe-merge.md` (71 lines)
- `docs/runbooks/prace-v-nemecku-layout-agent-report.md` (59 lines)
- Receipted evidence tree under `evidence/reviews/2026-09-16-prace-layout/`

The full audit text and the application-agent work order were read in full. Verbatim
received copy archived at
[`ORIGINAL-servers-infra-core-review-s61.md`](ORIGINAL-servers-infra-core-review-s61.md).

## Assessment (application-side review)

The deliverable is well-structured and discipline-consistent on its own host:

- **Leading decision is correct**: keep `/var/www/prace-v-nemecku.tvoje.info` as the canonical checkout; do not merge `/etc/prace/env` into the checkout `.env`. The audit correctly separates the checkout path from the public hostname question.
- **Evidence quality is high**: per-command `host`+`cwd`+UTC receipts, native exits, bounded inventory (1,382 metadata entries, 35 explicit exclusions), and no claim of full-content privacy coverage.
- **Security handling is correct from the application perspective**: the shared-secret equality (`PRACE_SECRET_KEY` == `PRACE_DB_PASSWORD`) is emitted as a boolean only; a plaintext credential literal in a newer draft was redacted locally with a redaction receipt; forward of old unredacted versions is explicitly blocked.
- **Broken-recipe findings match local facts** on server62:
  - `docs/operations/wsgi-deployment-recipe.md:53,55` name `/etc/prace/secret.key` and `/etc/prace/manifest.sha256`;
  - `docs/operations/delivery-1-postgres-handoff.md:169` names the secret-key file;
  - privileged inventory on server62 confirms neither file exists under `/etc/prace/` (only `env`). These recipes must be corrected (owner: application project).
- **HBA finding matches local catalog metadata**: `local all all peer` precedes the Práce md5 record (first-match shadowing of the socket path).

## Items the audit flags but does not claim as proved

These are correctly bounded and should stay open on server62 application-side too:

- Provisioning actor/run chronology and exact creation revision.
- TCP password failure and SIGKILL cause (systemd records signal 9; no DB/login experiment was run).
- Actual DB backend/authenticated identity of the stray user-session WSGI processes (DB var names absent; absence does not prove SQLite).
- Latest release-manifest approval and the correct repin.
- Full effective permissions and public-hostname selection.
- Cross-host deployment absence; deletion safety of the empty `expc.cz` scaffold.

## What the audit does NOT do (correctly)

- Does not move `/etc/prace` content into the checkout; does not merge runtimes; does not propose a bulk filesystem move or a Git merge of unrelated repositories.
- Does not authorize a service restart, credential rotation, HBA change, live manifest rewrite, process stop, or scaffold deletion — those remain production operations for the relevant operational authority.
- Does not claim application acceptance from its own 320 tests / 14 validators (those validate the servers-infra-core repository structure, not the application checkout or live recovery).

## Required follow-ups landing on the application project (server62)

Driven by this audit and implemented/lodged in
[`REPORT-prace-application-s62.md`](REPORT-prace-application-s62.md):

1. Correct the phantom-file recipe references (`wsgi-deployment-recipe.md`,
   `delivery-1-postgres-handoff.md`, `technical-needs-sysadmin-2026-09-12.md`).
2. Reconcile the temporary public hostname (`prace-v-nemecku.expc.cz`) in the
   application recipes and request docs, keeping the checkout path separate.
3. Update application skills to document the infra-owned `/etc/prace/env`
   EnvironmentFile contract and the unresolved credential/provenance state.
4. Log the shared-secret exposure as an open rotation item on server62; do not
   forward unredacted copies.
5. Keep JAN-01–04, committed-source/business acceptance and PG5 restoration
   requirements in force.

## Unresolved (owned by server61 infrastructure or operator)

- Persist distinct authoritative secrets; handle the exposure response and old-credential rejection.
- Select the approved release pin; diagnose SIGKILL independently from HTTP 500.
- Establish one supervisor and one OCR owner for the live listener/root.
- HBA reconciliation only if transport/principal tests justify it (md5 line must not be blindly moved above peer).
- Import/reconcile the untracked legacy runtime role on a scoped branch; import proves future reproducibility, not history.

## Verification note

No application suite was run for this report; this review is documentation/review
validation only. Independent local verification of select claims appears in the
application report; shared-secret equality was re-verified on server62 with a
sha-256 boolean-only comparison (values never printed or stored).