# PostgreSQL reconciliation report for servers-infra-core — 2026-09-15

**Purpose:** report for the `servers-infra-core` infrastructure team. The user
forwards this file manually; nothing is sent automatically. It is self-contained:
the application team provides no passwords, password hashes, record contents,
executable password-reset commands or blame. This report updates, but does not
replace, [the infrastructure request](servers-infra-core-postgresql-request.md)
(v1.0), whose YAML template remains the required response contract.

---

## 1. Observation window and evidence quality

- **Observed:** 2026-09-15, Europe/Prague (CEST). Exact clock times for the
  individual probes are not reproduced here; run the verification commands in
  §3 and return their outputs with timestamps.
- **Independently checked in this observation** (read-only probes of service
  state, process environment and one authentication attempt against the
  configured application): the PostgreSQL/systemd state in §2.1, the
  application authentication failure in §2.2, and the Gunicorn supervision
  mismatch in §2.3.
- **Agent-reported claims from earlier sessions** (not independently
  re-verified here, and not treated as facts): any statement about who deployed
  what, when; any claimed OOM event; any claimed historical absence of
  databases or roles. §4 lists corrections to these claims.
- Everything in this report is diagnostic. No host change was made by the
  application team; host writes remain sysadmin-owned.

## 2. Observed state

### 2.1 PostgreSQL and systemd

- A PostgreSQL cluster **was observed running** on 2026-09-15.
- A `gunicorn` systemd unit for the prace application **was observed in a
  failed state** (`systemctl` shows the unit failed; unit logs were not
  exhaustively read in this pass).
- Separately started `gunicorn` processes **were observed running** while
  carrying **no PostgreSQL target variables** (`PRACE_DB_NAME/USER/HOST/PORT`
  absent from their environment). Such processes cannot be serving the
  intended PostgreSQL target, whatever else they serve.

### 2.2 Application authentication

- A login attempt against the running application using the **configured**
  application credentials **failed**. The failure shape (authentication
  redirect versus hard error) is an application-side question under JAN-01;
  this report records only that configured authentication did not succeed.
- No credential values, hashes or reset commands are included here, by design.

### 2.3 Supervision mismatch

- One failed systemd unit and independent stray `gunicorn` processes
  simultaneously exist. This is exactly the "same process supervised through
  two mechanisms" hazard the infrastructure request asked to avoid (request
  item 6). Until reconciled, "the service is up" and "the unit is failed" are
  both true at once and neither describes the intended runtime.

### 2.4 Shared application/test ownership and directory permissions

- The application's settings module separates runtime, migration and test
  access **by configuration**, but the separation is not yet validated
  (application-side defect, JAN-04). Unless separated, one database role
  would serve the web runtime, migrations and test runs together.
- The project checkout is documented as owned `pavel:www-data` with `0750`
  directories / `0640` files, and private runtime directories as `0700`
  (settings-enforced). These permissions come from the earlier sysadmin
  readiness documents and the settings contract; **fresh verification of
  actual current ownership/modes is requested** (§3 item 4), including parent
  traversal rights for service users (the earlier `/var/log/` traversal
  failure remains a known pattern).

### 2.5 Observed endpoints — diagnostic facts only

These are what was observed reachable during the 2026-09-15 pass. **They are
not required deployment choices**; infrastructure selects the final endpoints,
ports and transport:

- Public route: `prace-v-nemecku.tvoje.info` terminates TLS on the s61 edge and
  forwards to the s62 backend, which served the static holding page.
- A locally bound Gunicorn HTTP listener serving the Django application was
  reachable on the host and rejected the configured login.
- No endpoint observed in this pass demonstrated a working PostgreSQL-backed
  application session.

## 3. Requested actions (servers-infra-core)

1. **Reconcile authoritative credentials.** Identify the authoritative secret
   references for the application's database role; return secret *references*
   only (never values). Do not rotate or reset anything on the strength of this
   report alone.
2. **Separate runtime, migration and test access.** Provide distinct access for
   the web runtime, migrations and automated tests. Tests must use an
   explicitly isolated disposable target and must never point database
   creation, truncation or cleanup at the operator database.
3. **Reconcile process supervision.** One supervisor for the WSGI application
   (and separately for the sequential OCR worker). Stop or properly adopt the
   stray `gunicorn` processes; make the systemd unit's state and the actual
   runtime agree.
4. **Assess directory ownership and access.** Verify current ownership/modes of
   the application checkout, its private runtime tree, PostgreSQL log/state
   directories, and parent traversal for the intended service identities.
5. **Return backup/restore and monitoring responsibilities** per the
   infrastructure request: backup method consistent with PostgreSQL (no
   ordinary live data-directory copies), retention, recovery objectives,
   restore evidence on a disposable target, and basic service/storage/
   connection/backup-failure monitoring.

## 4. Corrections to earlier assumptions

- **Current empty tables do not prove historical absence.** A stopped or
  failed cluster, or an insufficiently privileged role, cannot enumerate
  databases. Earlier "no prace database exists anywhere" statements described
  the observation conditions, not established history.
- **Signal 9 does not establish OOM.** A `SIGKILL` is consistent with many
  causes (manual kill, supervisor, cgroup limit, kernel OOM killer). Without a
  kernel OOM-killer journal record, do not attribute the kill to memory
  pressure.
- **File modification times and `sudo`/group membership do not establish
  deployment history or actor identity.** They support at most weak correlation;
  do not infer who deployed what, or when, from them.

## 5. Required response

Complete and return the YAML template in
[`docs/operations/servers-infra-core-postgresql-request.md`](servers-infra-core-postgresql-request.md)
(`contract_version` 1.0). At minimum the response must cover:

- **Target identity:** PostgreSQL version, host/socket, port, database name,
  schema and default `search_path`.
- **Access roles:** runtime role, migration access mechanism, and the
  disposable test target, kept separate.
- **Secret references:** vault/secret-store paths only, never values.
- **Transport/TLS:** mode and CA reference for any remote TCP path.
- **Service ownership:** WSGI and OCR-worker supervision arrangements, and the
  outcome of the stray-process reconciliation in §3 item 3.
- **Verification results:** the commands run, their exit codes and the
  authenticated database identity actually observed (per the request's
  `verification:` block), plus `remaining_gaps` stated explicitly.
- **Backup/restore and monitoring references** per §3 item 5.

`provisioned` still does not mean application acceptance has passed (see §6).

## 6. Application blockers the infrastructure response does not close

The application team records these open items so it is clear that **credential
repair alone will not complete acceptance**:

- **JAN-01/JAN-02:** the OCR HTTP 500 and the protected-download mismatch are
  investigated as separate defects; authentication redirects must be
  distinguished from file corruption. Normal login and protected original
  download must be demonstrated.
- **JAN-03:** the core/optional-A1 profile separation is partially
  implemented; A1-specific requirements must not gate core acceptance.
- **JAN-04:** target forwarding to the configured `PRACE_DB_*` target, verified
  disposable cleanup, migration credential scope and the effective statement
  timeout must be repaired and validated; restart persistence must verify
  actual file bytes and exact records.
- **One committed-source core acceptance run** on the returned target, then
  Jan's observed use, complete the delivery. Existing-data migration,
  real-data activation and official A1 issuance remain separate.

Until the infrastructure response arrives, application-side synthetic work
continues against the default SQLite target; a missing or unreachable target
is reported as unverified, never downgraded to a false PASS.

---

**Application-team disposition:** this document is a review checkpoint only.
It repairs no application code, rotates no credentials, changes no services
and migrates no data. It is forwarded by the user, not sent automatically.
