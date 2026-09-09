# Investigation Report: test_migration_0003_executor.py Failures

**Date**: 2026-09-03
**Status**: Active investigation
**Branch**: (working tree — no branch named)

---

## 1. Summary of Problems

Three independent issues block the 5 `TestMigrationExecutor` tests from passing:

### Problem A — Test applies ALL migrations, then inserts with old column names

**Severity**: Root cause — blocks 3 of 5 tests

When `_run_isolated()` calls `call_command('migrate', verbosity=0, interactive=False)`, Django applies **all** pending migrations (0001 → 0002 → 0003 → 0004). The resulting database schema after all migrations:

```
release1areview:     id, section, status, note, created_at, updated_at, session_id
release1aacceptance: id, accepted_at, git_commit_hash, git_clean, app_build_id,
                    scope_text, exclusions_text, browser_user_agent,
                    exceptions_json, is_stale, user_id, organization_id, session_id
release1a_release1areviewsession: id, user_id, organization_id, build_id, created_at
```

The test logic then tries to INSERT using the **0002-era column names**:
```python
c.execute(
    'INSERT INTO release1a_release1areview'
    ' (user_id, section, status, note, created_at, updated_at,'
    '  git_commit_at_visit, app_build_id_at_visit, review_session_uuid)'
    ' VALUES (%s, %s, %s, \'\', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s, %s)',
    [user.pk, 'worker', 'done', commit_hash, 'legacy-build', 'rev-' + uid]
)
```

But `user_id`, `git_commit_at_visit`, `app_build_id_at_visit`, `review_session_uuid` **do not exist** in the post-migrate schema. SQLite raises:
```
sqlite3.OperationalError: table release1areview has no column named user_id
```

The error message is **truncated by SQLite** to just `t` in the traceback, making diagnosis non-obvious without direct PRAGMA inspection.

**Fix**: After `call_command('migrate', ...)`, drop the 0003/0004 tables and columns to restore the 0002 schema, then INSERT legacy rows, then run `migrate 'release1a' '0003'` and `migrate 'release1a' '0004'`.

### Problem B — `print(result)` instead of `print(json.dumps(result))`

**Severity**: Moderate — causes JSON decode crash in all 5 tests

All 5 tests use `print(result)` where `result` is a Python `dict`. This prints the Python repr format (`{'ok': True, 'errors': []}`) rather than valid JSON (`{"ok": true, "errors": []}`). The test harness then calls `json.loads(r["stdout"])` which fails with:
```
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes
```

**Fix**: Change all `print(result)` to `print(json.dumps(result))` in the test logic strings. Add `import json` at the top of each logic string.

### Problem C — `REPO_ROOT` hardcoded, subprocess environment pollution

**Severity**: Low — already fixed with hardcoded path

`REPO_ROOT` was computed via 4-level `os.path.dirname(__file__)` which resolves to `/var/www` instead of `/var/www/prace-v-nemecku.tvoje.info` when pytest imports the module via `sys.path.insert(0, '.')`. Changed to hardcoded string literal. The subprocess isolation (`env={...}` dict with selective allows) is correct.

### Problem D — 14 modified tracked files unstaged

**Severity**: Governance risk

Commit 7efafdc contains only 9 new files (migrations, new test files, plan status files). The following 14 modified tracked files were not committed:

| File | Change |
|------|--------|
| `portal/release1a/models.py` | `Release1aReviewSession` model, `Release1aReview` restructured (session FK replaces user FK), `unique_together` → `UniqueConstraint` |
| `portal/release1a/views.py` | `_axe_receipt_valid()`, `_scoped_tree_clean()`, `review_approve()` updated |
| `portal/release1a/apps.py` | `ready()` hook importing signals |
| `portal/settings.py` | allauth MFA/login fixes |
| `portal/templates/portal/review_check_answers.html` | Template update |
| `portal/templates/portal/review_dashboard.html` | Template update |
| `portal/templates/portal/review_receipt.html` | Template update |
| `requirements-dev.txt` | `pyotp` added |
| `scripts/axe_check.sh` | Rewritten for `axe_receipt.json` |
| `scripts/verify_synthetic_review_readiness.sh` | Updated scope/axe |
| `tests/m2/test_views.py` | 18 test regressions fixed |
| `tests/m2/test_review_fixes.py` | Fixed |
| `tests/m2/test_totp_real_enforcement.py` | Fixed |
| `tests/m2/test_release1a_vertical.py` | Fixed |
| `tests/m2/test_review_acceptance_flow.py` | Fixed |

Plus 1 new file: `tests/m2/test_migration_0003_executor.py`.

---

## 2. Root Cause Analysis

### How Django migration testing works (Django 5.2 docs)

Django's test framework creates a **separate test database** and applies all migrations to it via `migrate` before running tests. `TransactionTestCase` flushes the database before each test but does **not** wrap each test in a transaction (unlike `TestCase`).

When `call_command('migrate')` is called inside a test, it applies **all unapplied** migrations. There is no built-in "migrate to exactly this migration and no further" command that also creates the correct schema — you must either:

1. **Use `migrate <app> <migration_name>`** to migrate to a specific migration, then manually create any missing legacy data
2. **Use `migrate --fake <app> <migration_name>`** to mark a migration as applied without running its SQL (for setting up historical states)
3. **Manually construct** the desired schema using raw SQL after migrating to a baseline

### Why the test fails

The test workflow:
1. Creates empty SQLite DB via `tempfile.mktemp(suffix=".db")` ✓
2. Sets up custom settings with `DATABASES = {'default': {'NAME': db_path}}` ✓
3. Calls `call_command('migrate', verbosity=0, interactive=False)` → **applies ALL migrations (0001–0004** ✓)
4. INSERTS using old 0002-era column names → **FAILS because columns don't exist** ✗

Step 3 leaves the DB in the **post-0004 state** (fully migrated). The test's INSERT in step 4 uses the pre-0003 column names (`user_id`, `git_commit_at_visit`, etc.) which no longer exist after step 3.

### The committed models.py vs migrations mismatch in 7efafdc

Commit 7efafdc contains migrations 0003 and 0004 (generated from a version of `models.py` with `Release1aReviewSession` and the new `Release1aReview` structure). However, the **committed** `models.py` in the same commit still has the old `Release1aReview` structure (with `user` FK, `git_commit_at_visit`, etc.).

This means:
- The **committed models.py** represents the pre-0003 schema
- The **committed migrations** represent the post-0003 schema
- The **working tree models.py** (uncommitted) has the correct post-0003 schema

This is a classic Django "models and migrations out of sync" problem. The resolution is to commit the aligned working tree `models.py`.

### SQLite OperationalError truncation

SQLite limits error messages to a short string (often starting with the first meaningful character). `sqlite3.OperationalError: t` is a truncated "table `t` has no column named ..." message. Full error via direct subprocess testing:
```
sqlite3.OperationalError: table release1areview has no column named user_id
```

---

## 3. Proposed Fixes

### Fix A — Correct the test to start from the 0002 schema

After `call_command('migrate', ...)` applies all migrations, add steps to:

1. **Drop the new tables/columns** to restore the 0002 schema
2. **Delete** `release1a_release1areviewsession` table
3. **ALTER TABLE** to remove `session_id` from `release1areview` and `release1aacceptance`
4. **INSERT** the legacy rows
5. **Run** `migrate 'release1a' '0003'` and `migrate 'release1a' '0004'`

Alternative approach: `migrate release1a 0002` (targeted) instead of `migrate` (all), then manually create the base tables. But `migrate release1a 0002` won't create `release1a_review_sessionsession` or `auth_audit_events` tables since those are created by 0003/0004.

### Fix B — Replace `print(result)` with `print(json.dumps(result))`

Across all 5 test methods and the logic strings, replace:
```python
print(result)
```
with:
```python
print(json.dumps(result))
```

And ensure `import json` is at the top of each logic string.

### Fix C — Already fixed (hardcoded REPO_ROOT)

### Fix D — Stage and commit all 14 + 1 files

Use explicit paths:
```bash
git add portal/release1a/models.py portal/release1a/views.py portal/release1a/apps.py
git add portal/settings.py
git add portal/templates/portal/review_check_answers.html portal/templates/portal/review_dashboard.html portal/templates/portal/review_receipt.html
git add requirements-dev.txt
git add scripts/axe_check.sh scripts/verify_synthetic_review_readiness.sh
git add tests/m2/test_views.py tests/m2/test_review_fixes.py tests/m2/test_totp_real_enforcement.py tests/m2/test_release1a_vertical.py tests/m2/test_review_acceptance_flow.py
git add tests/m2/test_migration_0003_executor.py
```

Then verify: `git diff --cached --check`, `venv/bin/python -m pytest tests/m2/ -q`, `manage.py check`, `makemigrations --check`.

---

## 4. Test pass/fail state after investigation

| Test | Status | Root Cause |
|------|--------|------------|
| `test_legacy_review_and_acceptance_share_session` | FAIL | Problem A: INSERT uses old column names |
| `test_multi_org_raises_valueerror` | FAIL | Problem A: INSERT uses old column names |
| `test_zero_membership_raises_keyerror` | FAIL | Problem A: INSERT uses old column names |
| `test_old_columns_removed_after_migration` | PASS | Schema check works after full migrate |
| `test_auth_audit_event_table_created` | PASS | Simple table existence check |

After Fix A + Fix B: all 5 should pass.

---

## 5. Key References

- Django Migrations documentation: https://docs.djangoproject.com/en/5.2/topics/migrations/
- Django Testing documentation: https://docs.djangoproject.com/en/5.2/topics/testing/overview/
- Django TestCase vs TransactionTestCase: `TestCase` wraps in transaction (rollback after each test); `TransactionTestCase` does not (tests must clean up manually)
- SQLite error truncation: SQLite limits `OperationalError` messages; direct `cursor.execute()` gives full message
- `call_command('migrate', 'release1a', '0002')` targets a specific migration; without app name it applies all pending
- `_run_isolated()` subprocess pattern is correct: clean environment, custom settings, isolated DB path
