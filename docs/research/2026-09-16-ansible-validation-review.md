# Offline Ansible validation review — 2026-09-16

Status: offline syntax and target-selection evidence, plus source findings.
No deployment, live check-mode run, service restart, secret decryption, SSH,
network request or package/collection installation was performed.

The primary provided a reviewed, non-PII source snapshot of server61 core commit
`8adc07d677ef6abb27c9f530f7ad331c6584b76e`: 47 files in total, comprising
`ansible/` and `desired-state/package-versions.yml`. Remote uncommitted changes are excluded.
The snapshot was unchanged after execution, verified against its original file
hash manifest. Findings below apply to these bytes, not automatically to the live
fleet or remote dirty working tree.

## Executed results and coverage

Installed runner: `/usr/bin/ansible-playbook`, Ansible core `2.19.4`, system Python
`3.13.5`. Every actual Ansible check ran under `unshare -Urn`, with no network,
explicit static inventory, explicit snapshot roles, system collection paths,
memory-only facts and no optional callback integration. Nothing executed a task.
The actual offline controller was server62, not the inventory's nominal s61;
`ansible_connection: local` was inspected but never used to run a host task.

Final commands ran **18:20:47–18:21:00 UTC** on 2026-09-16.

| Playbook | `--syntax-check` native exit | `--list-hosts` native exit | Selected hosts per play |
|---|---:|---:|---|
| `control-plane-recovery.yml` | 0 | 0 | `s61` |
| `drift-check.yml` | 0 | 0 | `s60`, `s61`, `s62` |
| `netbox.yml` | 0 | 0 | `s61` |
| `vscode-server.yml` | 0 | 0 | Both plays select `s60`, `s61`, `s62` |

Role-to-target matrix for the four inspected entry points. “Selected” describes
offline play selection only; no role was applied.

| Role or inline task set | s60 | s61 | s62 | pve |
|---|---|---|---|---|
| `host_foundation` via control-plane recovery | — | Selected | — | — |
| `netbox` via NetBox playbook | — | Selected; task bodies gated by `netbox_apply` | — | — |
| Package facts/assertions in drift playbook | Selected | Selected | Selected | — |
| Inline VSCode tasks in its two plays | Selected | Selected | Selected | — |
| Standalone `vscode_server` role implementation | Not referenced | Not referenced | Not referenced | Not referenced |
| `network_standards` role | Not referenced | Not referenced | Not referenced | Not referenced |
| `host_firewall` role | Not referenced | Not referenced | Not referenced | Not referenced |

The inventory contains `pve` in the separate `hypervisor` group. None of these
four playbooks selects it. This is a coverage gap for an “all four hosts” claim,
not a reason to deploy the s61-only NetBox role to unrelated hosts.

An explicit negative coverage probe used
`drift-check.yml --list-hosts --limit pve`: **native exit 0, `hosts (0)`**.
Successful process exit therefore cannot establish target coverage. A workflow
must compare actual targets against the approved expected set for that specific
operation and treat missing required hosts as incomplete evidence.

## First failures and corrected execution environment

Original command receipts remain intact:

1. At 18:18:30–18:18:33 UTC, all eight original invocations exited **5** because
   this installed Ansible rejects `ANSIBLE_CONFIG=/dev/null` as an unsupported
   configuration filename. No playbook had been validated by those attempts.
2. The primary authorized an equivalent explicit empty owned `ansible.cfg`.
   At 18:19:31–18:19:48 UTC, syntax/selection checks exited 0, with warnings:
   namespace UID mapping caused an attempted default Ansible-home creation to
   fail, and an empty `ANSIBLE_LOG_PATH` resolved to a directory.
3. Final execution set `ANSIBLE_HOME` to the private owned check directory and
   omitted the empty `ANSIBLE_LOG_PATH`. All nine final commands exited 0 with
   empty stderr. No source change was needed. Both prior sets remain evidence.

The final command shape was:

```text
/usr/bin/unshare -Urn /usr/bin/ansible-playbook \
  -i <snapshot>/ansible/inventory/hosts.yml \
  <snapshot>/ansible/playbooks/<playbook>.yml --syntax-check
```

`--list-hosts` replaced `--syntax-check` for target inspection; the negative case
also specified `--limit pve`. The command cwd was the explicit snapshot root.
Final environment selected the owned `ansible.cfg`, private `ANSIBLE_HOME` and
`ANSIBLE_LOCAL_TEMP`, snapshot `ANSIBLE_ROLES_PATH`, system
`ANSIBLE_COLLECTIONS_PATH`/`ANSIBLE_LIBRARY`, `ANSIBLE_CACHE_PLUGIN=memory`, YAML
inventory only, default stdout callback, disabled callback loading and retry
files, and `PYTHONDONTWRITEBYTECODE=1`.

The private evidence directory is
`runtime/portal/temporary/agent-ops-review-146a5181eec6/ansible-offline-checks/`.
It contains original `commands.json`, intermediate `retry-commands.json`, final
`final-commands.json`, `source-manifest.json`, and per-command stdout/stderr.
Each command receipt records argv, cwd, UTC start/end, native exit and output
hashes. No secret payload is present. The source snapshot and checks remain
protected runtime artifacts and must not be staged.

## Findings requiring infrastructure follow-up

The following paths refer to the server61 source repository, not this application
repository's source tree.

| Severity | Finding | Required next evidence or correction |
|---|---|---|
| High | `ansible/inventory/hosts.yml` sets `s61` to `ansible_connection: local`. Running these playbooks from another controller would target that controller for s61 tasks. NetBox and control-plane tasks use privilege escalation. | Registered runner must bind and verify controller identity, source revision, inventory and exact targets before any live command; an inventory label alone is insufficient. |
| High | No playbook covers `pve`; the explicit pve drift probe exits 0 with zero targets. | Track pve as untested for these workflows. Use its separately authorized management procedure and expected coverage; fail automation on missing required hosts. |
| Medium | VSCode playbook disables facts but uses `ansible_env.HOME` and `ansible_user_id`; the snapshot inventory does not supply either. Syntax checks do not resolve this runtime dependency. | Supply explicit nonsecret target-user/home variables or gather the required facts; test on an isolated representative host. |
| Medium | VSCode synchronization uses `delegate_to: localhost`, `mode: pull`, an s61-prefixed source, and an unqualified destination. Its purported “skip reference host” assertion has `never` tags and does not remove s61 from default execution. | Verify controller/source/destination behavior in an isolated two-target test. Do not infer remote-to-remote deployment from the task name. Resolve reference-host exclusion explicitly. |
| Medium | `changed_when: false` masks actual writes in VSCode directory creation/recursive ownership tasks and `host_firewall/tasks/docker-user.yml` chain creation. NetBox `docker compose up -d` and its force-recreate handler report changed for every successful command; firewall flush/apply commands also always change. | Use truthful change reporting and relevant idempotent modules/conditions. Record first-run and repeat-run effects; `changed=0` or `changed_when` is not a no-mutation guarantee. |
| Medium | `network_standards/tasks/validate.yml` embeds `[assert ... for ...]`, which is invalid Python. An offline AST parse reproduced `SyntaxError`, native exit **1**. | Repair the embedded validation and add a direct regression. This task file is not imported by the four checked playbooks, so their syntax passes do not cover it. |
| Medium | `network_standards/tasks/enforce.yml` applies `failed_when: false` to its verification command. Its degraded-storage task only prints a skip message; the separate `standards_apply=false` condition is what currently ends s62 processing. | Verification failures need an explicit failed/unproven outcome. Make the degraded-storage guard enforce the intended boundary independently of another flag. |
| Medium | NetBox SOPS decryption runs on the controller. Secret-related templates and API/cache commands use `no_log`, but some runtime secrets are passed through command arguments. A task named “no plaintext secrets” actually checks that encrypted markers are absent. | Preserve protected controller execution and output suppression; assess process-argument exposure and use safer credential transport where supported. Correct the misleading validation name. No secret or SOPS file was read here. |
| Medium | Firewall rollback timing is described in README instructions but not implemented in the inspected role. The role can flush/replace firewall rules; NetBox restart handlers can recreate a service. | Prove backup, timed rollback, service/routing postflight and rollback cancellation under a scoped infrastructure execution receipt before acceptance. |
| Medium | Package drift code uses exact package/version matching while policy prose permits security-track upgrades. Overrides change versions but not package names, despite prose describing `docker.io` on some hosts and a `docker-ce` declaration. | Reconcile package identity, minimum-versus-exact version policy and host applicability using current operator-owned facts. This review did not gather package facts. |
| Low | The NetBox playbook comment recommends `inventory/fleet.yml`, which the drift playbook explicitly identifies as metadata rather than an Ansible inventory. NetBox role README still describes restic while current tasks/templates configure borgmatic. | Update operational instructions to the actual inventory and backup implementation before using them as runbooks. |

There are no `check_mode: false` overrides or Jinja `lookup()`/`query()` calls in
the inspected source. This observation is useful for screening but does not prove
that a future `--check` run is read-only: module behavior, dynamic includes,
controller actions, templating, registered results and imported roles still need
their own review. No live check-mode command was run here.

The snapshot contains the referenced hidden `.env.j2` **template**, which was not
rendered. It intentionally lacks `desired-state/host-foundation.yml`,
`desired-state/network-standards.yml` and `desired-state/host-firewall.yml`; their
absence describes this bounded export, not proof they are missing in server61's
full repository. Syntax checking does not load all dynamic variable files or
prove their contracts. All 33 YAML files in the snapshot parsed as YAML; this did
not catch the embedded Python error. `ansible.posix.synchronize` resolved during
the local VSCode syntax check, but dependency availability on the intended
controller was not tested and no collection was installed.

The embedded-Python failure has its own private
`network-validator-python.json` command receipt and stdout/stderr. The probe only
parsed the command string with `ast.parse`; it did not execute that command or
open its referenced policy path.

## Evidence still required

| Scope | Status after this review | Next owner |
|---|---|---|
| Exact snapshot identity, YAML and four playbook syntax checks | Recorded; syntax passes, separate embedded Python failure retained | Primary integrates findings; infrastructure repairs affected role |
| Expected host coverage | Observed for four playbooks; pve absent, zero-host negative reproduced | Infrastructure runner owner |
| Full dependency/config/template rendering | Not tested; bounded snapshot omits some dynamic policy inputs | Infrastructure owner, reviewed full-source candidate |
| SSH, privilege escalation and controller/delegation targeting | Not tested | Infrastructure owner, scoped registered checks |
| Services, sites, TLS and authenticated application behavior | Not tested by these offline commands | Infrastructure and application owners |
| Live `--check` behavior on each intended host | Not tested or authorized by this delegated task | Infrastructure owner, operation-specific boundary review |
| Apply, second-run idempotence and side-effect verification | Not tested | Operator-authorized infrastructure change |
| Handler execution, restart persistence and rollback | Not tested | Infrastructure owner and operator |
| Backup consistency, restore, recovery time and recovery data loss | Not tested; a configured backup hook is not a restore test | Backup owner with an isolated restore target |

For automation, record separate outcomes for syntax, coverage, environment,
dependency resolution, runtime behavior, idempotence, rollback and restore.
Operator waiting points belong before unapproved live host changes or expanded
targets, with an exact source/inventory/action/rollback proposal. Existing scoped
authorization should be reused; an offline exit 0 must never create deployment
or acceptance authorization. Parent execution plans remain the source of work
ownership; this report does not add a second deployment scheduler.
