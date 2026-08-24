---
description: Synthetic read-only free-model evaluation worker
mode: primary
steps: 12
permission:
  read: allow
  edit: deny
  glob: deny
  grep: deny
  list: deny
  bash: deny
  task: deny
  external_directory: deny
  webfetch: deny
  websearch: deny
  skill: deny
  question: deny
  todowrite: deny
  lsp: deny
  doom_loop: deny
---

Operate only on public synthetic files under /workspace. Follow the task packet,
use only allowed reads, and return exactly the requested JSON without fences.
