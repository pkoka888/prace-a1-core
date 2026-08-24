# Shell environment audit — 2026-08-14

This note supersedes the audit that attributed the shell input
`35;59;12M` to virtualenv path resolution or quoting.

## Verified findings

- `/var/www/prace-v-nemecku.tvoje.info` is the canonical repository path.
- `/var/www/prace-v-nemecku.troje.info` does not exist. It was a stale sibling
  workspace and was deleted on 2026-08-13 under explicit operator instruction.
- `source /var/www/prace-v-nemecku.tvoje.info/venv/bin/activate` and, from the
  repository root, `source ./venv/bin/activate` both succeed in a clean Bash
  environment.
- `venv/bin/activate` passes `bash -n`. Its generated expression
  `PATH="$VIRTUAL_ENV/"bin":$PATH"` is valid adjacent shell quoting and is not a
  syntax error.
- The virtualenv metadata records the canonical `tvoje.info` path.

## Correct diagnosis

`35;59;12M` is consistent with the payload of a terminal SGR mouse report whose
control-sequence prefix was lost or consumed. Bash then interprets the semicolons
as command separators. This is a terminal/input integration problem; it is not
evidence of inconsistent filesystem resolution.

If it recurs, capture the complete raw terminal input and inspect the originating
terminal client, shell integration, and any multiplexer for mouse-reporting mode
left enabled after a program exits.

## Operating convention

Repository commands should invoke the interpreter directly when activation is
unnecessary, for example:

```bash
venv/bin/python -m pytest -q
```

For an interactive shell, change to the repository root and run:

```bash
source venv/bin/activate
```

Do not hand-edit the generated activation script. Recreate the virtualenv if it
is ever genuinely damaged.

Project-specific roots and credentials must not be exported from the user's
global `.bashrc`. Tool credentials should be loaded only by that tool, and
project credentials should remain in a gitignored file owned by the project and
be loaded explicitly for the relevant session.
