# Original servers-infra-core review — verbatim received copy

Context host: **server61** (`/workspace/servers-infra-core`). Author: servers-infra-core
parallel review team. This file is an archival receipt of the message received by
the application project on host **server62** (`/var/www/prace-v-nemecku.tvoje.info`).
Do not mix the two project contexts. Nothing in this copy is an application-side
verification on server62.

The authoritative files remain on server61:

- `/workspace/servers-infra-core/docs/audits/2026-09-16-prace-layout-and-safe-merge.md`
- `/workspace/servers-infra-core/docs/runbooks/prace-v-nemecku-layout-agent-report.md`

## Received text (verbatim)

> Three parallel reviewers completed the checks. Keep `/etc/prace/env` separate from the canonical application checkout.
>
> Verified findings:
>
> - `/etc/prace/` contains only `env`; no application code needs moving.
> - Checkout `.env` contains tool credentials—a different purpose. Do not combine them.
> - Live Django and database secrets are identical.
> - The configured release pin mismatches the current manifest.
> - Port 8001 has user-session WSGI processes while systemd is failed; their database backend remains unverified.
> - The alternate `expc.cz` scaffold contains three directories and no files. Deletion safety remains unverified.
>
> I corrected the unsafe recommendations, redacted exposed credentials, and updated the plan, roadmap and response.
> **Credential rotation and production repairs remain pending.** No live files were moved or services changed.
>
> **Validation:** all 14 validators and **320 tests passed**.
>
> - [Full review and safe merge plan](/workspace/servers-infra-core/docs/audits/2026-09-16-prace-layout-and-safe-merge.md)
> - [Separate report and work order for the application agent](/workspace/servers-infra-core/docs/runbooks/prace-v-nemecku-layout-agent-report.md)

## Application-side disposition

Received and reviewed on server62 on 2026-09-16. Accepted as an evidence-bound,
server61-owned review. The application project independently re-verified the
shared-secret equality claim on server62 (sha-256 boolean-only comparison, values
never printed or stored); all other findings were cross-checked against local
diagnostics where available. See
[`REPORT-prace-application-s62.md`](REPORT-prace-application-s62.md) for the
application-side verification matrix and next actions.