# Release 1A Role and Data Catalog

**State:** frozen for synthetic proofs; operator validation required before pilot

| Role | Allowed Release 1A scope |
|---|---|
| Organization administrator | Manage scoped users, workers, documents, assignments, A1 cases, approvals, and audit views |
| Document reviewer | Upload documents and decide OCR proposals for assigned organization records |
| Assignment editor | Manage workplaces and effective-dated assignments within assigned organization scope |
| A1 approver | Run readiness, review prepared packages, and record external submission/response evidence |
| Auditor/operator | Read authorized history and investigate exceptions; no implicit write authority |

Every permission is organization-, record-, and action-scoped with default deny.
Delegation is explicit, effective-dated, attributable, and revocable.

| Data group | Purpose and authority | Provenance/sensitivity | Retention |
|---|---|---|---|
| Worker identity | Stable person matching; confirmed human revision | document/manual source; restricted | policy and legal-basis review |
| Activity profile | Profile-specific workflow and A1 inputs | effective-dated operator decision; restricted | history retained under policy |
| Document version | Review evidence; immutable bytes and metadata | uploader/hash/version; highly restricted | 90-day review default unless justified |
| OCR proposal | Assist human transcription only | engine/version/page/region; restricted | tied to document review lifecycle |
| Assignment | Placement and relevant period | editor/reason/effective dates; restricted | operational/legal review |
| A1 snapshot/artifact | Reproducible prepared package | hashes/source revisions/generator; highly restricted | case and legal review |
| Audit event | Accountability without sensitive payloads | server actor/time/action/object metadata | append-only policy review |

Required fields remain classified as `confirmed`, `synthetic-default`,
`operator-validation-required`, or `specialist/counsel-dependent`. No migration
mapping contains real values. This is the Plan N-1A catalog input, not final pilot
approval.
