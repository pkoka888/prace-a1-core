# Sysadmin Readiness Report — server62

**Date:** 2026-08-12
**Scope:** Repository-safe handoff for Plan K and the current M0–M1A stage.
**Evidence:** Live host checks performed on 2026-08-12; volatile facts require
sysadmin re-verification before a production change.
**Privacy:** This report intentionally excludes credentials, account membership,
internal addresses, firewall details, token scopes, environment-variable
inventories, and unrelated tenant information.

## Current conclusion

The host is not ready for portal deployment. This does not block synthetic portal
scaffolding once the M1A product and architecture gates pass. It does block a
production deployment or new real-data portal activation.

The most immediate operational risk is storage capacity: the root filesystem was
measured at approximately 93% used with about 6.7 GiB available. The host is
multi-tenant, so capacity cleanup, expansion, service changes, and maintenance
windows require coordination with the sysadmin and other service owners.

## Verified baseline

| Area | 2026-08-12 observation | Required disposition |
|---|---|---|
| Operating system | Debian 13; time synchronization active | Keep patching and restart evidence in the as-built record |
| Capacity | Root filesystem about 93% used | Define a threshold and forecast; expand or safely reclaim space before deployment work |
| Host security | SSH, default-deny firewall, intrusion prevention, and log rotation active | Verify the project-specific exposure after services exist |
| Monitoring | Metrics/log components present; alert delivery is not wired end to end | Add tested disk, certificate, and service alerts with an owner |
| PostgreSQL | Native packages and a cluster exist, but the cluster was down | Configure only after the application design selects roles, paths, and lifecycle |
| Reverse proxy path | The existing shared routing pattern was not healthy end to end | Repair and prove the shared path before treating it as a portal pattern |
| DNS | The project apex resolved to the fleet public endpoint; the proposed portal subdomain did not | Confirm the desired hostname and routing ownership before DNS or TLS changes |
| TLS | No project certificate was verified | Issue only after routing and hostname decisions; test renewal and failure response |
| Email/alerts | No working alert-delivery path was demonstrated | Select and test a relay/contact path when pilot notifications require it |
| Malware scanning | No scanner integration was demonstrated | Treat as measured deployment hardening; never expose uploads publicly |
| Service isolation | No dedicated project service identity was demonstrated | Create least-privilege non-login identities and protected directories before deployment |
| Backups | No project backup is enabled | Preserve the accepted controlled-pilot risk; make an explicit durability decision before later production/public release |

Installed libraries support the canonical Python A1 workflow. Ghostscript remains
an additional parser/validation gate where the workflow calls for it; its presence
does not replace deterministic PDF and visual verification.

## Repository-history status

Plan Q remote replacement completed on 2026-08-12 under explicit approval. At
verification time, both published branches and the remote default branch resolved
to sanitized checkpoint `c01aa2b5139e15518b02b09e1296e1377e034cea`.

The completed evidence included:

- an exact intended-tree comparison;
- a full reachable-object sensitive-path inventory;
- an official checksum-verified Gitleaks scan and detection canary;
- atomic force-with-lease replacement of the two approved remote branch refs;
- fresh-clone tests, link checks, sensitive-path checks, and secret scanning;
- local rollback refs and preserved pre-rewrite local branches.

No repository bundle or bare-clone backup was created because that would duplicate
the PII-bearing history. The protected, gitignored remediation workspace and local
rollback refs are not publication sources. Do not push pre-rewrite branches or
rollback refs. Do not run garbage collection or delete those recovery anchors
without a separate retention decision and exact approval.

## Plan K actions

1. Agree a capacity threshold and produce evidence that measured pilot growth fits
   within it; expand storage or safely reclaim space if it does not.
2. Repair and verify the shared reverse-proxy route before adding a portal route.
3. Confirm the portal hostname, DNS owner, routing owner, and certificate owner.
4. Define dedicated service/database identities, protected paths, local-only
   bindings, restart behavior, and least-privilege permissions.
5. Wire and test operational alerts, including disk, certificate, and service
   failure, with named operational ownership held outside this repository.
6. Specify proxy/application upload limits and temporary-space controls before
   enabling document uploads.
7. Record patching, recovery, release rollback, certificate-renewal, and incident
   procedures in the deployment as-built report.
8. Keep the controlled pilot's no-backup limitation explicit. If backups are later
   authorized, require encryption, database/file consistency, retention, failure
   alerts, and a demonstrated restore.

## Gates and boundaries

- No host package installation, service restart, DNS/TLS change, firewall change,
  account creation, or backup activation is authorized by this report.
- No portal production deployment or new real-data upload is allowed until the
  activation gate in
  [`docs/security/real-data-rules.md`](../security/real-data-rules.md) passes.
- Synthetic scaffolding still depends on the M1A gates in [`roadmap.md`](../../roadmap.md),
  not on completion of all Plan K production work.
- The authoritative operational requirements and exit gate remain in
  [`Plan K`](../../plans/2026-08-12-plan-k-server62-readiness.md).
