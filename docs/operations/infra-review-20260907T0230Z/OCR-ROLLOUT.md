# Prace OCR fallback installation and validation

2026-09-07. Status: **Tesseract installed and both engines exercised offline on s62**. This is infrastructure capability acceptance, not automatic application fallback or production document-quality acceptance. Operator requested installation/testing; reviewed legacy IaC was staged through `scripts/ssh62` and applied with local Ansible. Core records evidence and does not claim fleet authority closure.

## Applied changes

- Installed `tesseract-ocr` 5.5.0-1+b1 and `ces`, `deu`, `eng`, `osd` language-data packages 1:4.1.0-2, plus required native dependencies. No application venv changes, broad upgrades, new daemon or public OCR endpoint.
- Corrected an actual installation blocker: the existing GitLab Runner public APT key had expired in February 2026. Ansible fetched the official public key over verified HTTPS, checked its complete fingerprint and expiry, then atomically replaced only the existing source-specific keyring. No credential/deploy key or GitLab server change.
- The unchanged fingerprint is `F6403F6544A38863DAA0B6E03F01618A51312F3F`; the updated expiry is February 6, 2028. This matches [GitLab's extension notice](https://about.gitlab.com/blog/gpg-key-used-to-sign-gitlab-package-repositories-metadata-has-been-extended/).
- Strict `apt-get update -o APT::Update::Error-Mode=any` then succeeded, including the Runner repository. The initial failure and diagnostic output are retained; plain apt-get update initially returned zero despite signature warnings, so it was insufficient proof.
- Both package and key plays passed a second actual apply with changed=0, failed=0. Public-key verification performs temporary download/inspection each run, removes that scratch directory, and measures convergence on the managed keyring.

Implementation branch: `fix/prace-ocr-fallback`, worktree `/workspace/servers-infra-prace-ocr-20260907`. The OCR play includes only the existing site's OCR task entry point. The key play includes only the existing Runner role's public-key task entry point. Neither invokes the broad role main tasks. The benchmark script is registered and accepts only a fixed engine choice, never document paths.

## Executed OCR smoke comparison

Both engines ran as the operator's underlying unprivileged identity in isolated user/network namespaces, through the existing project Python environment. No external network was available to inference. The test generated four synthetic PNGs internally and deleted them on completion. Three existing RapidOCR model files and four installed Tesseract language files have recorded SHA256 hashes. One thread was requested for inference/OpenMP; runs were sequential with a 180-second outer deadline.

| Synthetic case | RapidOCR seconds / character error rate | Tesseract seconds / character error rate |
|---|---|---|
| Czech | 5.82 / 1.39% | 0.49 / 1.39% |
| German | 5.14 / 0% | 0.55 / 0% |
| Mixed Czech/German | 5.12 / 1.25% | 0.47 / 2.50% |
| Skewed 3 degrees | 4.63 / 0% | 0.66 / 0% |

RapidOCR initialization was 1.71 seconds and process peak RSS about546MiB. Tesseract benchmark initialization was0.11 seconds; individual engine processes started per image, with peak child RSS about66MiB (benchmark parent about35MiB). These are single-run smoke measurements under different engine architectures, not throughput or statistically representative accuracy rankings. CER normalizes whitespace and Unicode composition, retaining diacritics and case.

Both engines returned nonempty results for all four images and exactly matched two complete pages. RapidOCR lost a Czech accent; Tesseract made a different Czech error and altered German diacritics on mixed text. Keep RapidOCR as baseline and Tesseract available for explicit fallback/comparison. Human review remains necessary. No automatic application failover was implemented or claimed; the application must define triggers, adapter output/provenance and review behavior.

## Post-install health and remaining gaps

Postflight: nginx active, no failed s62 system units, `.env` remains0600 pavel:www-data, project pip check passes. Through the s61 HTTPS edge, public `/` and `/ready` return200; tested private routes return404 with certificate validation successful. Configuration-only restore verification passes. The public site remains a holding page; it does not advertise private operational details.

The [host readiness audit](HOST-READINESS.md) records s62 resources, healthy observability containers, backup timer status, and wider fleet findings. It does not prove restore success or application log delivery. s61 root86% and failed native services/Borgmatic check remain open: ownership is contradictory and failure causes are not established. No speculative restart, deletion or broad package upgrade was performed.

Follow-up priorities:

1. App agent supplies the clean release/settings/database/runtime manifest and executes a representative synthetic field benchmark, including the baseline and fallback.
2. Infrastructure prepares immutable model delivery and actual service-user access tests. Existing RapidOCR assets inside the app venv are group-writable; these tests do not establish a hardened future model directory. Do not recursively change a live application environment without its release contract.
3. Implement private worker supervision with explicit limits and metadata-only logs once its queue/identity contract is supplied. Current ORM broker does not require Redis. No app listener or PostgreSQL activation was inferred from OCR installation.
4. Follow the [SOPS/database runbook](SECRETS-DATABASE.md): controller-side decryption, scoped delivery, environment-specific identities, isolated migration rehearsal and actual DB-plus-file recovery. No vault files or private keys were copied to core or other hosts.
5. Resolve s61 service ownership, inspect authorized causal logs and repair service task ordering on separate topics; measure app impact before changing shared infrastructure.

## Evidence and validation

Ignored local artifacts: `evidence/raw/2026-09-07-ocr-install/`. Each live receipt records command, exit code, timestamp and operational authority. Key artifacts: `check.json`, initial `apply.json`, `apt-diagnosis.json`, `key-check.json`, `key-apply.json`, `ocr-apply-retry.json`, both `*-idempotence.json`, `apt-verified.json`, `rapidocr.json`, `tesseract.json`, `postflight.json`, `final-manifest.json`. All seven staged implementation file hashes match reviewed local sources; initial benchmark staging was superseded by the final manifest after review refinements.

Ansible syntax and production-profile lint passed. Tests exercise missing languages, failed engines, invalid key fingerprints, expired/revoked/extra keys and benchmark input rejection. Core research registration initially failed, was corrected with an indexed frontmatter-backed research artifact, and the full core test rerun passed104 tests. Final validator receipts and commits are recorded with the branch handoff; no raw evidence is committed.

Final validation: legacy static22/22, focused tests11passed plus4subtests, core validators14/14, core pytest104passed. Operational commit `38140b36` on `fix/prace-ocr-fallback`; core documentation on `docs/prace-devops-readiness`. Branches are local, not pushed or merged. The seven-file remote staging directory was removed after hash verification; managed packages and the corrected public keyring remain.
