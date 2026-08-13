# Findings — proposal diff vs live s62 state

**Date:** 2026-08-12 (probed 23:35–23:45 CEST)
**Method:** Live probes via SSH on s62 + s61, DNS queries to authoritative GoDaddy
NS, GitHub API via `gh`, apt-cache policy checks. Subagent-assisted verification.
**Labels:** [Fact] live command output | [Inference] derived | [Unverified]

## 1. Verified claims (match)

| Claim | Result | Evidence |
|---|---|---|
| Disk / 93%, ~6.8 GiB free | [Fact] 93% / 6.7 GiB avail | `df -h /` |
| RAM 15 GiB, ~7.3 avail | [Fact] 15Gi, 7.4Gi avail + 8Gi swap | `free -h` |
| sshd active; sudo: pavel/backups/deploy/ansible/sugent/agent | [Fact] | systemctl + getent group sudo |
| ufw active, INPUT deny, allows 100.64/14, 5555, 4000, 3000 | [Fact] rules present | `ufw status verbose` |
| fail2ban active | [Fact] | systemctl |
| Docker engine + compose v5.1.1 | [Fact] docker 26.1.5, compose v5.1.1 | versions |
| logrotate: tvoje-app/nginx/docker-containers/prometheus | [Fact] | /etc/logrotate.d |
| borg installed | [Fact] | /usr/bin/borg |
| A1 venv: pymupdf/reportlab/pillow/pypdf/numpy, no poppler/gs needed | [Fact] pymupdf 1.28.2, reportlab 5.0.0, pillow 12.3.0 | pip freeze |
| No /etc/letsencrypt/live on s62 | [Fact] | ls |
| No postfix/msmtp on s62 | [Fact] | systemctl/which |
| No clamav | [Fact] | which clamscan |
| No dedicated project service identities | [Fact] | getent/systemd |
| s62 multi-tenant (litellm, stehovani supabase, grafana/loki, adi, lukaspitrik, marketing vhosts) | [Fact] | docker ps + ls /var/www |
| git/gh/gs/openssl/rsync present | [Fact] git 2.47.3, gh 2.46.0 | versions |
| git-filter-repo 2.47.0-2 + gitleaks 8.16.0-1+b12 in Debian 13 repos, not installed | [Fact] | apt-cache policy |
| qpdf 12.2.0-1 in repos; trufflehog/pdftk NOT in repos | [Fact] | apt-cache policy |
| Repo private, default master, sole collab pkoka888 (admin) | [Fact] | gh repo view/api |
| Branch protection/rulesets API 403 (free plan) | [Fact] | gh api |
| gh token scopes incl. the 6 listed | [Fact] all 6 present (+ more) | gh auth status |
| .env contains the 13 listed keys | [Fact] all 13 + TELEGRAM_ALLOW_ALL_USERS | key names only |
| A1_PRIVATE_DIR unset by default; a1_private.py fails closed | [Fact] | grep + a1_private.py:14,17,21 |
| refs/rollback/ local refs exist (2) | [Fact] | git for-each-ref |

## 2. Mismatches — report says X, live says Y

1. **DNS: MISMATCH.** Report: "no DNS records for prace-v-nemecku.tvoje.info;
   server's public IP is unknown." Live:
   - [Fact] `prace-v-nemecku.tvoje.info A = 89.203.173.196` EXISTS — confirmed at
     GoDaddy authoritative ns55/ns56.domaincontrol.com AND via 9.9.9.9/8.8.8.8/1.1.1.1.
     SOA serial 2026081200 = today's date (zone touched recently).
   - [Fact] s62 egress IP = 89.203.173.196 (the shared Cisco NAT public IP).
     So the A record already exists and points at the correct fleet public IP.
   - [Fact] `portal.prace-v-nemecku.tvoje.info` has NO record (still to add).
   - Implication: the premise "public IP unknown" is false; the IP is the known
     fleet NAT IP. Caveat: per fleet topology, public HTTP(S) on 89.203.173.196
     NATs to s61 (Traefik), not directly to s62 — portal routing must go
     s61-Traefik → s62 backend, not a public A record to s62 itself.

2. **Alertmanager: MISMATCH (partial).** Report: "alertmanager inactive (no
   alerting)". Live:
   - [Fact] alertmanager.service is **active** (running since 2026-08-10,
     enabled, pid 1248, listening 0.0.0.0:1062).
   - [Fact] But prometheus.yml alertmanager targets = `[]` (empty), and
     /etc/prometheus/rules/ does not exist → **no alerts flow**. alertmanager.yml
     smtp_smarthost = localhost:25 with no postfix on s62 → email delivery would
     fail anyway.
   - Verdict: daemon runs; the "no alerting" conclusion is correct but the stated
     reason ("inactive") is wrong.

3. **Native PostgreSQL: MISMATCH.** Report: "Native PostgreSQL not installed
   (only another project's Supabase container)". Live:
   - [Fact] postgresql-18 (18.3-1.pgdg13+1) + postgresql-common IS installed
     (pgdg.list added 2026-07-03; data dir 2026-07-29). The `postgresql`
     meta-package is absent but the server/cluster tooling is present.
   - [Fact] Cluster 18/main (port 5432) exists but is **down**.
   - Verdict: packages installed but never configured/started → Plan K item is
     partially done already.

4. **nginx / s62:8097 pattern: MISMATCH.** Report cites the s62-nginx-8097 +
   s61-Traefik chain as an existing working pattern to copy. Live:
   - [Fact] nginx IS installed (1.26.3) but **service is FAILED** since
     2026-08-10 13:53:57; nothing listens on 8097; /run/nginx missing.
   - [Fact] tvoje.info.conf vhost exists (listen 192.168.1.62:8097 → proxy to
     127.0.0.1:3010) but the Next.js app is NOT running — pm2 has ZERO apps,
     nothing on 3010/8097.
   - [Fact] Traefik router `tvoje.tvoje.info.yml` on s61 routes
     Host(tvoje.info) → http://192.168.1.62:8097; `curl https://tvoje.info`
     from s61 = **HTTP 000 timeout**.
   - Verdict: the cited pattern is currently **down end-to-end** (pre-existing
     prod issue, not caused by this project). Do not assume the s62:8097 pattern
     is operational before replicating it for the portal.

5. **GitHub SHAs / Plan Q push state: STALE / MISMATCH.** Report: "live SHAs
   match local (master=3302934, codex/unified-a1-core=2250845)" and "no rewrite
   or push is approved yet". Live (probed after report mtime 23:05):
   - [Fact] origin/master and origin/codex/unified-a1-core BOTH point at
     **c01aa2b "Sanitized source checkpoint"** (pushed 2026-08-12 23:26:20,
     author "Repository Remediation") — 21 min AFTER the report.
   - [Fact] c01aa2b is NOT an ancestor of local HEAD. Local master=3302934
     (ahead 4, behind 1), local codex=a8763eb (ahead 23, behind 1).
   - [Fact] The report's codex SHA 2250845 matches neither live (c01aa2b) nor
     local (a8763eb). Local master SHA 3302934 equals the report's value but is
     the LOCAL sha, not the live one.
   - Verdict: a sanitized history checkpoint has ALREADY been pushed to origin on
     both branches — contradicting the report's "no push approved yet". Plan Q
     gates must be re-run against current origin state.

6. **poppler-utils version: minor mismatch.** Report: 25.03.0-1; live candidate
   is 25.03.0-5+deb13u4. Not blocking.

7. **Monitoring "partial" framing:** prometheus+node-exporter are systemd;
   grafana/loki/alloy run as healthy Docker containers (not systemd). Minor
   framing difference; alerting is genuinely absent.

## 3. Additional observations

- [Fact] ufw allows 5555 (borg) and 8097 (tvoje.info) but NOTHING is currently
  listening on either port; 4000 (litellm) is loopback-only despite the
  "Anywhere" ufw rule; grafana is 0.0.0.0:3000 (operator chose LAN-only bind
  per AGENTS.md §13.3; live container still 0.0.0.0 — known drift).
- [Fact] The proposal project itself is NOT in the fleet SSOT inventory
  (no prace-v-nemecku site/service/ports entries in inventory/).
- [Fact] Report file is currently untracked in the project repo (git status dirty).
- [Inference] The Aug 10 13:53 timestamps (nginx failure + alertmanager start
  same minute) suggest a provisioning/reboot event on s62 that broke the
  tvoje.info chain.

## 4. Actions implied by the diff

1. Re-check DNS premise: A record already exists (89.203.173.196). Only
   `portal.` subdomain needs adding. Public routing = s61 Traefik, not s62.
2. Start/fix the tvoje.info chain (nginx + Next.js) OR document the outage —
   the portal will reuse the same broken path.
3. Re-run Plan Q gates: origin already contains a sanitized checkpoint (c01aa2b);
   local is diverged (4/23 ahead, 1 behind). Decide push policy before more work.
4. Postgres: packages present, cluster down — Plan K "install" step is
   half-complete, not a greenfield install.
5. Alerting: alertmanager runs but is unwired (empty targets, no rules, dead
   SMTP) — "inactive" is wrong; plan should say "running but not wired".
6. Disk (93%) confirmed most urgent — unchanged.
