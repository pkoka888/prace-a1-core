# Report — Práce application project (host server62)

- Project/context host: **server62**, checkout `/var/www/prace-v-nemecku.tvoje.info`
- Related infra review host: **server61**, `/workspace/servers-infra-core` (see
  [`REPORT-servers-infra-core-s61.md`](REPORT-servers-infra-core-s61.md))
- Date: 2026-09-16 Europe/Prague
- Scope: application-side verification matrix, temporary public-hostname decision,
  doc corrections applied, and next actions. No live host configuration, service or
  database was changed.

## Operator decision — temporary public hostname

The server61 review confirms the canonical **checkout** is `/var/www/prace-v-nemecku.tvoje.info`
(operator-declared; matches the Git root and systemd `WorkingDirectory`). A checkout
directory does not choose a public hostname.

Operator instruction on 2026-09-16: proceed temporarily with the **`prace-v-nemecku.expc.cz`**
hostname. This matches the existing provisioned surface on server62:

- nginx vhost `prace-v-nemecku.expc.cz.conf` (`server_name prace-v-nemecku.expc.cz`;
  private listener 192.168.1.62:8098 → 127.0.0.1:8001)
- `/etc/prace/env` `PRACE_ALLOWED_HOSTS=prace-v-nemecku.expc.cz,localhost,127.0.0.1`

Application recipes and request docs therefore reference **`prace-v-nemecku.expc.cz`**
as the temporary public hostname while the checkout path stays
`/var/www/prace-v-nemecku.tvoje.info`. This is a temporary documented decision, not a
DNS/proxy/CSRF change; the infra response-v1 contract remains the authority for the
final hostname reconciliation.

## Local verification matrix (application-side re-check of the s61 findings)

| s61 finding | Local check on server62 | Result |
|---|---|---|
| `/etc/prace/` contains only `env` | `ls -la /etc/prace/`; dir 0750 root:prace-synthetic, file 0640 844 B | Confirmed |
| No `secret.key` / `manifest.sha256` siblings | find over `/etc/prace` | Confirmed absent |
| Checkout `.env` = separate tool credentials | `/var/www/prace-v-nemecku.tvoje.info/.env` — 14 tool/Telegram names, 0600 pavel:www-data | Confirmed separate purpose |
| Live Django secret equals DB password (boolean) | sha-256 boolean-only comparison of `PRACE_SECRET_KEY` vs `PRACE_DB_PASSWORD` | Confirmed equal; values never printed/stored |
| Configured release pin mismatches current manifest | env pin `d88b17ad…` vs `.release_manifest.sha256` `93dd105f…` and manifest-agreeing marker | Confirmed mismatch (stale pin) |
| Port 8001 held by user-session WSGI while systemd failed | PID 2681143 + children 2681150/2681151 in `user.slice/user-1000` cgroup, supervised-synthetic settings; no `PRACE_DB_*` in environ; unit `prace-v-nemecku-gunicorn.service` failed (earlier signal 9) | Confirmed; DB backend itself remains unproved (no login experiment run) |
| Alternate `expc.cz` scaffold: 3 dirs, no files | `/var/www/prace-v-nemecku.expc.cz/runtime/portal/supervised-synthetic/` empty scaffold | Confirmed; deletion safety still unverified |

## Corrections applied in this increment (docs only)

1. `docs/operations/wsgi-deployment-recipe.md` — replaced phantom
   `/etc/prace/secret.key` and `/etc/prace/manifest.sha256` reads with the actual
   variable names and the systemd `EnvironmentFile=/etc/prace/env` contract; temporary
   hostname updated to `prace-v-nemecku.expc.cz`.
2. `docs/operations/delivery-1-postgres-handoff.md` — same phantom-file correction in
   the lifecycle block; temporary hostname updated.
3. `docs/operations/technical-needs-sysadmin-2026-09-12.md` — treated 0600 vs 0640 as
   explicit identity/access policy, not an automatic defect; aligned the environment
   delivery expectations with the observed `/etc/prace/env` (0640 root:prace-synthetic,
   systemd EnvironmentFile).
4. Skills — `postgres-ops/SKILL.md` and `synthetic-portal-delivery/SKILL.md`: document
   the infra-owned `/etc/prace/env` contract and the unresolved credential/provenance
   state; separate approved live runtime from disposable fixtures; forbid secret
   copies/hashes, automatic repins, password resets from generic login failure, and
   stale-PID kill commands.
5. Archival: servers-infra-core original review and both host-labeled reports now live
   under `docs/operations/2026-09-16-layout-review/`.

## Open items (unchanged by this increment — documented, not executed)

- **Shared-secret exposure**: `PRACE_SECRET_KEY == PRACE_DB_PASSWORD` in
  `/etc/prace/env`. Rotation and session/signing impact reconciliation remain open and
  are operator-owned. Do not forward unredacted copies.
- **Release pin**: identify the approved release and manifest derivation before repinning.
- **Supervision**: one owner for the live listener/root; the stray user-session process
  group on 8001 must not be killed by PID guessing — operator adopts/converges via the
  documented stop/rollback path.
- **Credentials/HBA**: INFRA-PG-01 remains open; md5 record must not be blindly moved
  above the peer catch-all. No login experiment or HBA change was performed.
- **JAN-01–04 / committed-source / business acceptance / PG5 restoration** remain in force.
- Alternate-scaffold deletion remains conditional on emptiness + reference/process checks
  + approved disposition.

## Validation / evidence

Documentation/review validation only for this increment: planning validator, staged
whitespace check, relative-link checks over the touched documents, and the project's
commit hook checks for the staged packages. No application or live-services suite was
run or claimed; the s61 320-test/14-validator results validate the servers-infra-core
repository, not this checkout.

## Next owner

Operator: hostname/DNS/proxy reconciliation decision, credential rotation, approved
release pin, one-supervisor adoption, HBA reconciliation if justified. Application
engineering: JAN-03/JAN-04 toward one committed-source core acceptance run; then
operator/JAN-restart evidence and PG5 restore verification.