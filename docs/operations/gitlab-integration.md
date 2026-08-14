# GitLab integration — prace-v-nemecku

This is a **proposed, inactive runbook**. GitHub is currently the only configured
remote and remains authoritative as `origin`. Plan AE proposes GitLab as a private
secondary/backup and CI host, but DEC-016 is not accepted and no activation is
authorized. The commands below are reference material for a separately approved
operator session, not instructions to execute now.

## The GitLab repo

| Item | Value |
|---|---|
| Path | `tvoje-info/prace-v-nemecku` |
| Web UI | https://git.expc.cz:8445/tvoje-info/prace-v-nemecku |
| HTTPS clone/push (LAN) | `https://192.168.1.60:8445/tvoje-info/prace-v-nemecku.git` |
| HTTPS clone/push (Tailscale) | `https://100.87.66.75:8445/tvoje-info/prace-v-nemecku.git` |
| SSH (LAN, needs GitLab-registered key) | `ssh://git@192.168.1.60:2222/tvoje-info/prace-v-nemecku.git` |

**Reachability from s62 (verified 2026-08-14):** the public name
`git.expc.cz:8445` does NOT resolve to a route from the LAN (the Cisco NAT does
not map 8445), so **always use the LAN URL `https://192.168.1.60:8445` from
s62** (or the Tailscale URL as fallback). The GitLab TLS certificate is
self-signed but IS trusted on s62, so plain `git clone`/`push` works with no
`sslVerify` override.

## Proposed setup (requires exact approval)

```bash
cd /var/www/prace-v-nemecku.tvoje.info
# 1. Keep origin = GitHub (unchanged). Add GitLab as a second remote.
git remote add gitlab https://192.168.1.60:8445/tvoje-info/prace-v-nemecku.git
git remote -v   # expect: origin=github, gitlab=git.expc.cz(LAN)

# 2. Authentication — HTTPS uses a GitLab PAT (user odeen, api scope).
#    The canonical PAT lives in the servers-infra SOPS vault:
#      /workspace/servers-infra/.sops/secrets/hermes-gitlab.enc.yaml -> gitlab.pat
#    Write it to this host's git credential store (URL-encoded, like the
#    existing github.com + 192.168.1.60:8445 entries) so pushes are non-interactive:
#      https://oauth2:<PAT>@192.168.1.60:8445
#    NEVER commit the PAT, put it in a repo file, or paste it into a chat/log.
#    NOTE: the previously stored 192.168.1.60:8445 credential is REVOKED;
#    refresh it before the first push.
```

## Proposed day-to-day workflow after activation

GitHub stays `origin` and remains the source the agent treats as primary.
GitLab is a second target for the same branches:

```bash
# Push a branch to BOTH remotes (after local review + staging discipline per AGENTS.md):
git push origin <branch> && git push gitlab <branch>

# Never use --all or bulk tag publication. Publish only the explicitly reviewed
# branch named in the approval and verify its SHA on each remote.
```

**PII rules are unchanged and apply to BOTH remotes.** GitLab is a private
group, but the same safety rules hold: never stage/force-add/commit the
gitignored PII paths (`a1/`, `scans/`, `evidence/`, `ocr/`, `data/`,
`employees/scans/`, `output/`, `runtime/portal/`, `secrets/`, `.env`,
`.history-remediation/`); never push unless explicitly asked; never
force-push/rewrite history/delete branches without separate approval. The
`.gitignore` already protects these paths on both remotes — verify with
`git status`/`git diff --cached` before every push.

**Branch naming / default branch:** GitHub default is `master`; GitLab's new
project currently reports `main` as its placeholder default. When the first
branch is pushed to GitLab, prefer pushing `master` and set the project default
to `master` (Settings → Repository → Default branch) so both remotes agree.

## Rules for this repo

1. Do not move GitLab to be the primary remote without operator approval.
2. Do not add the GitLab remote, credentials, CI/CD, runners, mirrors, or
   webhooks without operator approval; the integration is not active.
3. If a push to GitLab fails, GitHub is unaffected; fix/retry locally and
   re-push. Never "fix" a GitLab failure by rewriting GitHub history.
4. Treat GitLab access like GitHub access: same operator key policy, same
   rotate-on-suspect discipline.
