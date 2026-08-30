# `.archive/` — local archive directory

**Purpose.** Files that are no longer part of the active tree but should
be preserved on disk (for rollback, audit, or future re-inclusion) live
under `.archive/`. This directory is the **only** place the operator
archives things; "delete" suggestions from the operator action plan
should always be replaced with an archive move here.

**Convention.** Every file or directory moved under `.archive/` keeps
its original path **relative to the project root**. The tree mirrors
the live tree, with `.archive/` as a sibling of the moved item.

```text
output/provisional.backup-20260811-114746/   →   .archive/output/provisional.backup-20260811-114746/
scripts/a1_core.py.backup                   →   .archive/scripts/a1_core.py.backup
docs/old-feature/                           →   .archive/docs/old-feature/
```

**Why a mirror and not a flat dump.** The relative path is preserved so
that:

1. The next operator reading `.archive/output/provisional.backup-20260811-114746/`
   knows it came from `output/provisional.backup-20260811-114746/`
   without reading a separate manifest.
2. A future migration or restoration can move items back to their
   original path with a single `mv -r .archive/<path> <path>` — no
   lookup table needed.
3. Grep across `.archive/` and the live tree is unambiguous because
   the same filename under different parents means different things.

**Why `.archive/` is gitignored.** Archived items are by definition
out of the active tree; committing them would defeat the purpose.
The README in this directory IS tracked (so the convention is visible
to any agent opening the repo). To track a specific archived item,
either:

- Move it back to its live path and commit normally, or
- Add an explicit `git add -f` with the item's full path and a commit
  message that explains why it stays archived and tracked (rare).

**Operational notes.**

- `.archive/` lives at the repo root so it stays in scope of any
  `tar` or backup operation that targets the project root.
- `.archive/` is excluded from the validator (`scripts/validate_change_packages.py`)
  by the `change-packages.yml` rule: paths matching `.archive/` are
  not staged even if they appear dirty.
- `.archive/README.md` (this file) is the only tracked item in the
  directory. Anything else under `.archive/` is local-only.

**Audit trail.** Each move into `.archive/` should be documented as
a separate commit on its parent path with a message like
"chore: archive output/provisional.backup-* per Plan R §8"
so the git history shows when and why the item left the live tree.