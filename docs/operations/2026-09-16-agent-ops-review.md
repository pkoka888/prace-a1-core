# Agent output, fleet state and automation review — 2026-09-16

**Status:** observed findings; implementation and validation are scoped below.
**Owner:** application engineering; infrastructure findings transfer to the
servers-infra operator. This report does not grant production authority.

## Result and evidence scope

The supplied Cline report mixes configuration, observation and acceptance.
Some recommendations are useful, but several suggested validators can return
zero without establishing correctness. A fresh fleet probe also disproves any
blanket healthy/deployed conclusion. Keep successful evidence where its exact
inputs still match; preserve failed attempts and missing coverage.

Application source at the beginning of this review: `995c945`, feature branch
`feat/prace-readiness-plan-2026-08-13`, with substantial inherited edits.
Infrastructure core: server61 `/workspace/servers-infra-core`, `8adc07d`, also
dirty. Offline Ansible evidence uses the **committed** core snapshot, not those
uncommitted changes. No inherited edits were adopted merely because they exist.

Private primary evidence: `runtime/portal/temporary/agent-ops-review-146a5181eec6/`.
Its health receipts contain exact commands, native exits, timestamps and inner
probe results. The initial server62 → server61 SSH connection is the controller
access path; subsequent fleet access uses the existing registered wrappers.
No credential payload, source scan or real employee content was sent to agents.
Three bounded subagents reviewed source claims, official framework documentation,
logging and Ansible source, and the synthetic workflow experiment.

During the review another active agent published `e7d3758`, `b055259` and
`a7e73f2` to the shared feature branch. The last commit included this review's
active-plan edits before their linked deliverables were integrated. This is
direct evidence that a prose directory grant does not isolate staging or
publication. Final integration therefore uses an isolated checkout. Future
handoffs must bind base revision, owned paths and receipts; only the primary
integrator stages/publishes, and a changed remote head triggers reconciliation.

## Correction to my earlier A1 statement

The earlier deterministic result is supported: render exit 0 in 45.1 seconds;
validate exit 0 in 101.2 seconds; 24 PDFs, 72 previews, three contact sheets,
`passed=true`, no set issues. Fresh verification at 18:19 UTC rechecked completed
canonical audit operations, generation evidence, dependency versions, source/PDF
hashes, manifest inputs, previews and contact bindings. All still match. This is
recorded in `a1-claim-reverification.json`; repeating the raster run would add no
new evidence for unchanged inputs.

The correct claim is **deterministic validation of these existing provisional
artifacts passed**. It is not all-page visual acceptance, human confirmation,
historical generator reproduction, official issuance or portal acceptance.
The renderer and mapper had changed since historical generation. The first
supplemental verification used the wrong contact receipt filename; that failure
was retained and the check corrected to canonical `contact-receipt.json`.

The original 30-second interruption had no recorded native exit code. Do not
invent one. The retained initial path attempts exited 2, and the requested
runtime preview path is rejected by the protected-output contract. A 300-second
budget is a practical example for this measured package, not a universal fix.
Separate tool wait intervals from process deadlines; retain PID/start identity,
phase progress, terminal exit and receipts before retrying. A timeout means an
unknown/incomplete outcome until process and artifact reconciliation establish it.

## Findings in Cline's proposed verification

The [source review](../research/2026-09-16-cline-claims-review.md) contains
synthetic reproductions and exact limits:

- `schema_validator.py` can accept empty JSON and report a blank three-page
  PDF with a warning and exit 0; that does not validate A1 content.
- `dual_framework.py` returns PARTIAL/0 without a second PDF and VERIFIED/0
  for the same PDF twice. It does not independently run both generators.
- `hardcode_checker.py` can return CLEAN/0 without the requested record or
  expected evidence. Its JSON may expose source values.
- The web-search stub has no sources; PARTIAL/0 is not external verification.
- Existing `scripts/run_release_reproducer.py` admitted protected runtime
  configuration from a Git tree. A bounded fix rejects protected locations and
  environment payloads **before any blob is read**. The new synthetic negatives
  also preserve normal source names and explicitly reviewable example templates.

The export repair is application implementation. It does not repair or endorse
the legacy helper CLIs, nor does it establish absence of secrets everywhere.
The canonical A1 publisher and QA remain the operational path.

## Fleet health observed on September 16

Scope comes from core `inventory/fleet.yml`: s60, s61, s62 and pve. The tombstoned
Windows VM remains outside managed scope. Four of four hosts answered. Disk
percentages below use fresh `df -P /`; an earlier statvfs probe measured space
unavailable to the caller and is retained separately, not used as the same metric.

| Host | Root disk | Observed state | Coverage limits / next owner |
|---|---:|---|---|
| s60 | 16% | No failed systemd units listed | Docker query exit 1: account lacks socket permission. Container/service and backup acceptance remain unverified; infra owner supplies the approved read path |
| s61 | 90% | Failed borgmatic backup/check/prune, MariaDB, Postfix, PostgreSQL 17 cluster and Redis units; 20 containers listed, four exited | Classify desired state before alerting or restarting; two exited entries are runner helpers. Investigate disk and recovery failures first; no cleanup authorized by size alone |
| s62 | 53% | Práce Gunicorn and borgmatic backup units failed; nginx/Alertmanager active; 13 containers Up | Up is not protocol or backup verification. Reconcile application listener/supervisor and backup failure |
| pve | 42% | No failed systemd units listed; pveproxy/pvedaemon/pvestatd active; `zpool status -x` says all pools healthy | Does not establish SMART history, backup freshness, restore correctness or all VM acceptance |

No service was restarted, database modified, firewall changed or backup pruned.
An installed-but-failed service is an observation, not proof the service is
still required. Infrastructure must reconcile it with current desired state.

### Práce route and build

Both `127.0.0.1:8001` and internal nginx `192.168.1.62:8098`, with the selected
Host header, returned HTTP 200 for `/health/`, `/readiness/` and
`/accounts/login/`. The JSON advertises synthetic mode, `real_data=false` and
build `g00786f74fb53` / commit `00786f74fb5321900f9f293f989447e5d7bd8016`.
That is different from the reviewed checkout; the selected systemd service is
still failed with MainPID 0. The HTTP `supervised=true` field cannot prove
systemd owns the listener. No authenticated PostgreSQL identity, browser journey,
restart persistence or approved release pin follows from these HTTP results.

### Website coverage

Legacy inventory has 31 site records, six explicitly disabled. We probed the 25
remaining declared hostnames from **server61**, using normal DNS, verified TLS,
one bounded GET of `/`, discarded bodies and no redirect following. Práce uses
the operator-selected `.expc.cz` hostname from core, not its historical site ID.

Four requests obtained HTTP responses: GitLab 302; status, test and traefik
okamih hostnames 404. The other 21 failed with DNS, TLS or timeout errors.
Detailed per-site results and the declared inventory are in `site-probes.json`
and `site-scope.json`. A 302 is not an authenticated journey; a 404 is not a
successful site assertion. These checks do not establish external-client
availability, since a server61 egress/hairpin path may behave differently.
The inventory's missing/incorrect expected-response contracts remain a gap.

## Infrastructure probe defects to repair before reuse

Inspected source, not a claim about every executed historical report:

1. Legacy `service-health-probe.sh` maps missing Docker output after suppressed
   SSH failure to PASS, defaults failed disk/systemd probes toward zero, disables
   TLS verification, and its JSON branch does not propagate failed-probe count.
   Its embedded host map also includes an undeclared retired target.
2. `fleetcmd` adds an out-of-inventory host. Do not use it for the reviewed fleet
   without reconciling that target and native per-host failures.
3. Core `fleet-g0-probe.sh` can print `g0_passed=true` and exit 0 while components
   are blocked; stopped VM presence and a recorded decommission decision do not
   establish running workload or physical storage health.
4. Registry-referenced contracts for `ansible-drift-check` and `fleetcmd` were
   absent at their declared paths. Registry labels are not execution proofs.
5. Existing fleet wrappers disable strict host-key checking; the controller SSH
   hop used strict checking. Harden wrapper verification in the infrastructure
   repository after reconciling known-host custody; do not bypass a mismatch.

These findings belong to the infrastructure source owner. This application
review does not silently modify the other repository or replace its registry.

## Logging and alert claims

The [logging review](../research/2026-09-16-logging-claims-review.md) confirms
matching rules for journal-tail, syslog/auth, PostgreSQL and nginx, and no
matching included rules for `servers-infra-sync.log`, `loki-disk-watch.jsonl`
and `ssh-security-monitor.log`. The latest scheduled logrotate service exited 0.
The unprivileged debug attempt exited 1 because it could not read state or enter
configured `su` contexts; this is a probe limit, not proof privileged rotation
failed. The initial unqualified command was not on PATH; absolute
`/usr/sbin/logrotate` exists. Being over a size threshold between daily timer
invocations alone does not prove rotation is broken.

Grouping and inhibition reduce notification noise. They do not prove the
monitored condition is true, metrics fresh, receiver delivery working or
false-positive rate acceptable. No notification was sent by this review.

## Deployment validation and its boundary

See the [offline Ansible review](../research/2026-09-16-ansible-validation-review.md)
for syntax checks, host selection, first failures and unsafe-task analysis.
It uses a pinned, nonsecret committed-source snapshot with network disabled.
Syntax/list-hosts evidence is not a fleet deployment or idempotence test.
All four syntax checks and their target listings exited 0; none selects pve.
An explicit pve selection returned exit 0 with zero matched hosts. Separately,
an embedded Python validator in the network-standards role failed parsing.
That defect is not caught by playbook YAML syntax validation.

The inspected legacy operator contract says: “MUTATING … propose only; human
applies”; core also remains in shadow mode without general production authority.
The user authorized investigation and deployment testing, but no specific
reviewed fleet change, canary, release revision and rollback has been selected.
Ansible `--check` can execute `check_mode: false` tasks and controller lookups;
`--diff` can disclose secret payloads. Therefore a blind all-role/all-host run
cannot be called a harmless deployment test. The next deliverable is a reviewed
role × target test matrix and disposable convergence, followed by one bounded
canary action if its existing or new authorization covers the exact action.

Still unverified: remote role convergence, second-run idempotence, canary apply,
handler/restart behavior, rollback, external-client protocol assertions, restore
of database plus protected files, the committed-source core browser workflow
on its intended PostgreSQL target, and Jan's acceptance. No green report here
closes those gates.

## Workflow, organization and next work

The [workflow contract](../architecture/agent-operations-workflow.md) and
[framework comparison](../research/2026-09-16-agent-messaging-frameworks.md)
keep canonical Python/Ansible executors and add a bounded **synthetic** LangGraph
experiment. MCP/A2A/CLI transport does not replace authorization, audit,
idempotency or evidence. The graph has no production executor or model provider.

Actual isolated runtime evidence: 35 integration cases passed before a reviewed
path-confinement correction; four affected path/demo checks passed afterwards.
The final CLI demo also exited 0, paused for a synthetic decision, reconciled an
after-commit exception and retained exactly two effects after duplicate resume.
Do not label this a complete rerun of the first suite against final bytes.
Receipts are in `runtime/portal/temporary/agent-ops-langgraph-demo-20260916/`.
The first run took 161.86 seconds; its cost is unprofiled, so filesystem load is
not established as the cause. Source/config and resolved dependency versions
are bound in the final receipt; canonical application dependencies are unchanged.

Installed CLI inspection found Cline 2.8.1. Its local help differs from the
current online reference (for example `--yolo` / `--auto-approve-all` versus the
documented `--auto-approve <boolean>`), so configure the installed interface.
The first Codex `--version` probe exceeded its 10-second diagnostic budget;
that is an incomplete version probe, not a tool failure diagnosis. No inference
session, authentication change or remote agent listener was started.

Use one versioned nonsecret workflow contract, one small experiment, focused
tests, linked research and the existing active plan. Private per-run receipts
stay under runtime; A1 artifacts retain their protected output path. Do not
reorganize historical evidence or create a second fleet inventory in this repo.
The [active REL/JAN plan](../../plans/2026-09-14-delivery-reliability-and-jan-v1.md)
owns the actionable TODOs; the [delivery record](git-delivery.md) separates
implementation, validation, publication, deployment and activation.
