# Plan J — Data Protection and Legal Decision Inputs

**Status:** active
**Milestone:** M1A–M5 gate
**Owner:** product owner with Czech/German counsel

## Objective

Implement and verify `docs/security/real-data-rules.md`. Legal validation remains
a parallel advisory track and must not block synthetic product implementation.

## Work

- Require purpose, uploader, intake time, and retention-review date for every real-data intake.
- Implement default-deny organization/record/action authorization and auditable sensitive access.
- Preserve OCR proposals separately from human-confirmed authoritative values and provenance.
- Implement the 90-day review workflow, justified extensions/legal holds, controlled deletion, and minimal audit tombstones.
- Block public file URLs, accidental Git tracking, sensitive logs, and full-document external-model processing.
- Implement retention/deletion, rights-request, security-incident, periodic access-review, and credential/session response workflows without automating legal conclusions.
- Maintain a counsel question register for controller/processor allocation, legal bases, document-copy necessity, statutory holds, DPIA/DPO screening, and German-partner arrangements.

## Deliverables

- Passing automated and manual real-data activation checklist.
- Purpose/retention metadata and access/audit enforcement in the portal.
- Tested procedures for rights requests, security incidents, retention/deletion, access review, credential compromise, and session invalidation.
- Counsel question register citing primary Czech, German, and EU sources.
- Product/schema constraints separated from unresolved legal conclusions.

## Exit gate

Synthetic implementation proceeds immediately. Existing operator-only A1 processing
continues under `AGENTS.md`. New real-data portal uploads are enabled only when the
activation checklist in `docs/security/real-data-rules.md` passes and the operator
explicitly approves activation.

## Exclusions

No universal multi-year retention, blanket Article 9 classification, default
partner legal role, automatic DPIA/DPO conclusion, or legal advice by an agent.
Backups are not part of this activation gate; ad-hoc PII copies remain prohibited.
