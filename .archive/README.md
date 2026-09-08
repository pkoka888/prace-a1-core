# `.archive/` — non-sensitive history

Use this directory for reviewed non-sensitive historical documentation or source
material. Preserve the original repository-relative path where useful. Existing
tracked history remains tracked; other local archive entries remain ignored.
Archiving is a deliberate classification decision, not automatic permission to move
unknown files or a substitute for retention/deletion policy.

Never move scans, employee datasets, generated A1 PDFs, credentials or other PII
here. Keep working provisional packages where they are. Individually classified
private obsolete artifacts may be retained under
`runtime/portal/temporary/retained/<uuid>/` with an original-location/hash manifest,
reason, owner and retention-review date. That location remains protected and
ignored; it is not an ad-hoc backup. Do not relocate `.history-remediation/`.

Non-sensitive examples:

```text
docs/old-feature/ → .archive/docs/old-feature/
plans/old-plan.md → .archive/plans/old-plan.md
```

Inspect destination collisions and dependencies before a move, and record the
reversible mapping in the existing delivery record. Never force-add private or
unknown archived material. Restore a reviewed source file to its normal tracked
location before ordinary source delivery when it becomes active again.

Authority: [AGENTS.md](../AGENTS.md),
[real-data rules §5](../docs/security/real-data-rules.md#5-storage-and-git-boundary)
and the [consolidation plan](../plans/2026-09-08-local-a1-automation.md).
This policy update does not move or delete existing archive entries.
