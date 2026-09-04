# UX Review Notes — 2026-09-04 (Informal)

**Status:** Jan informal UX feedback; not formal REV-002 approval
**Source:** Jan's review statement (2026-09-04)
**Scope:** Synthetic data only; no real PII used

## Disposition

Jan conducted an informal UX review using synthetic data. Formally, `REV-002`
remains in `implementation_gate: blocked` state. These notes record Jan's
operational feedback for implementation planning.

No formal acceptance or real-data authorization is granted by this document.

---

## Section-by-section notes

### J1 — Pracovník (Worker)

- Czech terminology understood
- Worker detail layout matches daily work
- Required fields for worker creation/review are appropriate
- **Open:** Who creates, edits, confirms worker identity? Roles and delegation to be confirmed

### J2 — Dokument a kontrola OCR

> ⚠️ J2 engineering prerequisites not yet implemented (protected storage, OCR bytes-from-storage, failure/retry)
> Do not mark J2 DONE until those are complete

- Understanding of required document fields
- Scope of original-file download (download button) needs explicit operator decision — is it operationally necessary?
- Selective verification / redaction preferred over mandatory full OP/ZP scan retention
- **Pending technical:** Real quarantine, OCR failure/retry, protected download

### J3 — Přiřazení (Assignment)

> ⚠️ J3 concurrent-edit technical verification pending

- Assignment terminology confirmed as appropriate
- Exceptional correction cases require further definition
- **Pending technical:** Concurrent edit handling (optimistic locking implementation)

### J4 — Příprava a kontrola A1

> ⚠️ J4 engineering prerequisites not yet implemented (immutable snapshots, generated previews, staleness)
> Do not mark J4 DONE until those are complete

- ČSSZ submission and response handoff steps require operator confirmation
- Actual competent institution (ČSSZ for Czech employer) to be confirmed at implementation time
- A1 field requirements confirmed appropriate
- **Pending technical:** Immutable input snapshots, deterministic A1 generation, staleness handling

---

## Open operational questions

| Question | Owner | Status |
|---|---|---|
| Roles and delegated users for create/edit/archive/confirm/approve/download | Jan + product design | Open |
| Original-file download necessity | Jan + product design | Open |
| ČSSZ submission/response handoff steps | Jan | Open |
| Exceptional assignment correction procedures | Jan + product design | Open |
| Supported browser/device | Jan | Open |
| Selective redaction workflow | Jan + product design | Open |

---

## Next steps

1. Sprint 1 implements J2/J4 engineering prerequisites
2. Jan's open questions resolved before formal REV-002 review session
3. Formal REV-002 review after Sprint 1 completion
4. Sprint 2–4 → REV-003 activation

---

*No PII in this document. Meeting notes from informal review session.*
