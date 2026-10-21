# The working database: where it lives, how it is backed up, and why it is not in Git

**Status:** accepted decision, 2026-10-21
**Owner:** primary agent
**Applies to:** the workspace database `db.sqlite3` and any other database file
in this repository

## 1. The decision

**The working database stays out of Git. `.gitignore` keeps excluding it, and
the exclusion is now enforced rather than merely stated.**

The question was whether to un-ignore the database, protect it with a
password, and put the password in `.env`. The answer is no, and the reasoning
is below rather than a preference.

## 2. What the database actually holds

The workspace database holds **five real client workers**: their names, their
dates of birth, their sex and their insurance numbers. It is not a template,
not synthetic and not a fixture. The identity revisions table is empty, and
there are no cases, documents or assignments in it, so the exposure today is
five identities — which is exactly the class of record the repository's own
rules place outside version control.

`AGENTS.md` lists `a1/`, `scans/`, `runtime/`, `secrets/`, `evidence/` and
`output/` as never committed, and says *"Tests, fixtures, docs, screenshots and
model prompts use synthetic data. Never disguise an actual employee record by
lightly changing names or identifiers."* A database holding five real client
identities is an employee record in the most direct sense.

## 3. Why a password does not change the answer

Encryption at rest and Git are two different problems, and a password on the
file only addresses the first.

**Encryption at rest protects against unauthorised access to storage media.**
It does not protect against a repository leak, a leaked key, or a compromised
application — the key is in the process's environment while the database is
open, and an attacker with the repository *and* the host's `.env` has both.
The industry guidance is explicit that a committed encrypted file is still a
committed file, and that a key stored alongside the thing it protects is not
a control.

**Git history is permanent.** The published history of this repository was
once rewritten to remove PII-bearing ancestry — that is recorded in
`docs/operations/repository-history-remediation.md`, which states that the
accepted remote baseline *"excludes the PII-bearing ancestry"* and that a
normal all-ref bundle or publication of the recovery refs *"would duplicate or
re-expose PII"*. Committing the working database would put five client
identities into the published history, and `git rm` afterwards would not take
them out of the clones. Undoing it would need another destructive rewrite,
which that record explicitly gates behind a separate approval.

**A binary database has no useful diff.** The schema is already versioned by
the migrations, which is what version control is for. Tracking the binary adds
merge conflicts and review noise without adding a reviewable change.

## 4. What to do instead

The proposal's actual goal — the data is preserved, recoverable, and the
repository holds no secrets — is delivered three ways, and all three already
exist or are recorded here.

### 4.1 The working database is backed up outside Git, to the private runtime

The runtime manifest already defines the place: `PRACE_RUNTIME_ROOT` is a
required approved absolute private runtime root, and the manifest proposes
the retention (RPO 24 h, RTO 4 h, seven daily and four weekly backups). A
database backup belongs there, next to the other private runtime children, and
not in the repository.

| Step | Command | Where it lands |
|---|---|---|
| Back up | copy `db.sqlite3` to `$PRACE_RUNTIME_ROOT/backups/portal/`, mode 0600, owned by the runtime user | the private runtime root |
| Restore | copy the chosen backup back over `db.sqlite3` and run `manage.py migrate` | the workspace |
| Verify | `sqlite3 db.sqlite3 "PRAGMA integrity_check"` returns `ok`, and the worker count matches the backup | the workspace |

The backup is encrypted or held on an encrypted volume **as a host
decision** — see §4.4.

### 4.2 A reproducible, synthetic database is committed instead

The repository already has the mechanism: `scripts/seed_verification_db.py`
recreates an isolated verification database from the migrations and seeds
synthetic organizations, users, workers, documents and assignments. That is the
"template database plus a dump" pattern the practice recommends, and it is
the thing a committed database would have been for. It is extended here to
cover the employer records added in 2026-10-21.

### 4.3 The rule is enforced, not just stated

`scripts/check_git_content.py` now refuses a database file in the committed
tree **and** in the index, so removing the `.gitignore` rule cannot quietly
expose the working data. The same script is a CI step, so the check runs on
every push as well as on every commit.

### 4.4 If encryption at rest is wanted for the local file, it is a host change

SQLite has no built-in encryption. The options are SQLCipher, which is a
dependency change and a *migration* rather than a toggle — converting a
database rewrites every byte of it — or an encrypted volume, which is a
host decision. Either way it carries the risk the guidance names: if the file
is encrypted and the key is not available at the next start, the application
cannot open its own database, and that is a total, unrecoverable loss of the
records. So encryption, if adopted, must arrive with a verified backup taken
first, a documented key location, and a restore that has been rehearsed.

The key belongs in the host's secret store, injected at runtime — not in
`.env` in the repository, and not beside the file it protects.

## 5. What is explicitly not being done

* The working database is **not** un-ignored.
* No database password is added to `.env`; `.env` holds provider keys and
  the GitHub token, and the database belongs to the host's secret handling.
* No history rewrite is performed. The existing sanitisation stands.
* The local database is not migrated in a way that changes its content.

## 6. Review triggers

| Trigger | Action |
|---|---|
| The database is ever staged | the guard refuses the commit; the backup path in §4.1 is used instead |
| A client asks for the data to be versioned | it goes to the agency's own encrypted storage, not to Git |
| The private runtime root changes | the backup path in §4.1 is updated to point at the new root |
| A decision is taken to encrypt the local file | it is done as a host change, with a verified backup and a rehearsed restore, and it is recorded here |

## 7. Sources for the decision

* This repository's own `docs/operations/repository-history-remediation.md`:
  the accepted remote baseline excludes the PII-bearing ancestry.
* This repository's `AGENTS.md`: the protected paths, the synthetic-data rule,
  and the private-runtime model.
* This repository's `docs/operations/runtime-manifest.md`: the private runtime
  root and the backup retention proposal.
* "Best Practices for Using Git with Your Database": Git is not a backup
  system; schema definitions, migrations, procedures and views belong in Git,
  production-grade backups and PII do not.
* "What's the correct way to deal with databases in Git?": track the schema
  and a template, not the binary; recreate from migrations.
* "SQLite Encryption in Production": encryption at rest covers storage media
  and backups, and does not cover a compromised application, a leaked key, or
  access control; `.env` is for local development and is never committed.
* "Database at-rest encryption: enable/migrate (guarded) + decrypt": the
  lockout risk if the key does not reach the next start, and the requirement
  for a verified backup before the migration.
