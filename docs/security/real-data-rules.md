# Pravidla reálných dat

**Status:** Authoritative operational policy
**Approved direction:** 2026-08-12
**Applies to:** the existing A1 pipeline and the future Jan portal

This policy is the single operational gate for using identifiable people and
their documents. It enables implementation to continue with synthetic data; it
does not replace purpose-specific Czech/German legal advice.

## 1. What counts as real data

Real data includes any information that identifies, or can reasonably be linked
to, a real worker:

- worker identity and contact records;
- OP/ZP and other source documents;
- OCR text, crops, proposals, and corrections;
- workplaces and assignments linked to a person;
- A1 application data, prepared packages, previews, and official responses;
- exports and audit events linked to a person.

Synthetic data must be clearly fictional and must not be derived by lightly
altering a real person's record.

## 2. Permitted purposes

Real data may be processed only to:

1. create or maintain a worker record;
2. verify information needed for the worker or A1 workflow;
3. record a workplace or assignment;
4. prepare, review, or track an A1 application;
5. process a correction, access, export, restriction, or deletion request;
6. investigate security and maintain the required audit trail.

Every document intake must record the worker or intake reference, document type,
declared purpose, uploader, upload time, and retention-review date. A document
without a permitted purpose must not be accepted.

Real data must never be used in demonstrations, marketing, public screenshots,
test fixtures, issue trackers, ordinary logs, agent prompts, or model training.

## 3. Data minimization and identity documents

- Collect and expose only the fields needed for the declared purpose.
- Do not require or retain a complete OP/ZP copy when verification or selective
  extraction of the necessary fields is sufficient.
- A retained full scan requires a recorded operational need and an applicable
  legal basis or other documented authorization.
- Do not copy unused document fields into notes, logs, exports, or generic JSON.
- Do not treat employee consent as a universal legal basis. The controller must
  record the applicable basis for each processing purpose.

The Czech Data Protection Authority warns against blanket copying and retention
of identity documents and emphasizes purpose-specific minimization. See
[ÚOOÚ guidance on consent](https://uoou.gov.cz/verejnost/qa-otazky-a-odpovedi/k-vyzadovani-souhlasu)
and [identity verification and personal-data processing](https://uoou.gov.cz/media/clanky/dokumenty/prokazovani-totoznosti-a-zpracovani-osobnich-udaju-1.pdf).

## 4. Authorized access

- Access is denied by default.
- Jan, Pavel, and an administrator explicitly delegated by Jan may work with
  records within Jan's organization according to their assigned permissions.
- Access must be enforced server-side by organization, record, role, and action.
- A technical administrator may access content only when a necessary maintenance
  or incident task cannot be completed without it.
- Viewing, downloading, or exporting a sensitive document must create an audit
  event. Sensitive files must never have a public URL.
- Users must not share accounts. Confirmation and approval belong to the logged-in
  user who performed them.

## 5. Storage and Git boundary

All durable project data must remain under:

```text
/var/www/prace-v-nemecku.tvoje.info
```

Real data is permitted only in designated gitignored locations:

```text
a1/
scans/
ocr/
evidence/
output/                         # generated PII-bearing artifacts only
runtime/portal/quarantine/
runtime/portal/documents/
runtime/portal/generated/
runtime/portal/previews/
runtime/portal/temporary/
```

Rules:

- Never commit or force-add real data. A private GitHub repository does not make
  Git an appropriate document store.
- Never place real data in `/root`, `/home`, `/srv`, another repository, or
  `/tmp`. `/tmp` remains disposable and non-PII only.
- Single-owner protected directories use mode `0700` and files use `0600`.
- When a dedicated service group is required, directories may use `0750` and
  files `0640`. Modes `0644` and `0664` are not acceptable for real data.
- Stored filenames/keys and URLs must not contain names, birth numbers, national
  identifiers, or document numbers. Preserve an original filename only as
  protected display metadata when necessary.
- Nginx must not expose the project root or runtime directories. An authenticated
  application check must authorize every protected download.
- Secrets and `.env` files are gitignored and protected; their values must never
  enter logs, docs, screenshots, or agent output.

The native PostgreSQL data directory may remain system-managed outside the
checkout. That is host-managed application state, not a project artifact agents
may relocate or edit directly.

## 6. OCR, corrections, and authoritative values

- OCR output is always an untrusted proposal.
- OCR must not overwrite an authoritative worker field automatically.
- Jan, Pavel, or a delegated administrator may correct or confirm a proposal;
  no mandatory second-person approval is required.
- Confirmation records the actor, time, source document/version, original OCR
  proposal, accepted value, and manual change where applicable.
- A correction preserves the prior authoritative value, reason, actor, time, and
  provenance.
- Changing an authoritative source value marks affected prepared A1 artifacts
  stale. They must be regenerated rather than edited or silently reused.
- A prepared A1 package remains distinct from an official certificate issued by
  the competent institution.

## 7. External providers and AI

- Local deterministic processing and local OCR are the default.
- Full OP/ZP scans, full A1 artifacts, or employee datasets must not be sent to an
  external AI/model provider.
- A narrowly cropped or redacted payload may be used only when explicitly
  authorized under `AGENTS.md` and when local processing is insufficient.
- Record purpose, provider, model, and execution date. Never record credentials.
- External output remains a proposal and requires deterministic validation and
  human confirmation.

## 8. Audit requirements

Append an audit event for:

- successful login, material authentication events, and denied authorization;
- upload, view, download, export, supersession, and deletion;
- OCR completion, correction, and confirmation;
- permission changes and administrator delegation;
- material worker or assignment changes;
- A1 generation, approval, status changes, and official-response handling;
- suspected or confirmed security incidents.

An event contains actor, organization, action, opaque object reference, time,
result, request/correlation ID, and a reason where required. It must not contain
document content or full identity values.

## 9. Retention and deletion

Do not encode an arbitrary universal multi-year period. Each real-data item has:

```text
purpose
retention_review_at
retention_status = active | review_due | retained_with_reason | legal_hold | deleted
retention_reason
```

Pilot default: the first review is due 90 days after intake, then every 90 days
while the item remains retained without a separately confirmed rule.

At review, an authorized administrator must:

1. delete the item when its purpose has ended;
2. retain it with a recorded operational/legal reason and a new review date; or
3. apply a documented legal or authority hold.

Deletion removes the raw document and unnecessary OCR derivatives, crops,
previews, temporary files, and generated copies. Keep only a minimal non-content
audit tombstone showing what object was deleted, by whom, when, and under which
decision. Do not automatically delete material subject to an active A1 case,
legal obligation, authority process, or documented hold.

This implements GDPR purpose limitation, minimization, accuracy, storage
limitation, and accountability without inventing a statutory retention period.
See [GDPR Article 5](https://eur-lex.europa.eu/eli/reg/2016/679/art_5/oj/eng).

## 10. Data-subject requests

- Log requests for access, correction, restriction, objection, export, or
  deletion and route them to the responsible administrator.
- Exports must be purpose-limited, access-controlled, and audited.
- Legal exceptions and authority records require review before deletion; the
  application must not make that legal decision automatically.
- Record completion, refusal/partial fulfillment, reason, actor, and time without
  duplicating sensitive content in the audit message.

## 11. Incident response

Suspected unauthorized access, accidental publication, a wrong recipient, leaked
credentials, or loss of a device/session must be reported to Pavel immediately
and recorded as an incident.

The response must:

1. restrict or revoke affected access;
2. preserve only the evidence needed for investigation;
3. identify affected data, people, recipients, and systems;
4. record containment and remediation;
5. determine with the responsible controller whether notification is required.

GDPR Article 33 requires controller notification to the supervisory authority
without undue delay and, where feasible, within 72 hours when the breach is likely
to result in risk; a processor informs the controller without undue delay. See
[GDPR Article 33](https://eur-lex.europa.eu/eli/reg/2016/679/art_33/oj/eng).

## 12. Mandatory recovery before real-data activation

Backups are not a condition for synthetic implementation. They are mandatory
before new real-data portal uploads or migration. The activation evidence must
include an encrypted application-consistent PostgreSQL dump, the protected-file
set and manifest, a fresh off-host archive, an integrity check, and an isolated
actual restore with schema/query and representative file validation. The recorded
elapsed time must be compared with the approved RTO; RPO, retention, key custody,
and stale/failed-backup alert ownership must be explicit.

Git protects tracked source history only. It does not back up gitignored scans,
runtime files, PostgreSQL data, or secrets. Do not compensate by creating ad-hoc
`.backup`, archive, ZIP, or copied PII trees. Approved backups must be encrypted
and governed by the same access, retention, incident, and deletion rules.

## 13. Responsibility boundary

The application enforces purpose recording, access scope, provenance, audit,
retention reviews, deletion workflow, and external-processing restrictions. It
must not silently decide:

- the final legal entity acting as controller or processor;
- the legal basis for every identity-document use;
- statutory retention periods;
- whether a DPIA or DPO is legally mandatory;
- controller/processor contracts or German-partner arrangements;
- legal eligibility for A1 or validity of an official certificate.

Before onboarding another organization, the operator must record its legal name,
controller/processor allocation, contact, permitted purposes, and applicable
processing bases. These declarations do not block application scaffolding or
synthetic development.

ČSSZ describes the workflow as an application for determination of applicable
social-security legislation and issuance of an A1 confirmation by the competent
institution. See [ČSSZ A1 service](https://eportal.cssz.cz/web/portal/-/sluzby/zadost-o-urceni-pouzitelnych-pravnich-predpisu-pro-zamestnance-pojistenec).

## 14. Real-data activation gate

Existing operator-only A1 work may continue under the canonical `AGENTS.md`
pipeline. New real-data uploads through the portal remain disabled until all of
the following pass:

- [ ] approved users and delegated roles exist;
- [ ] organization and record scoping is enforced server-side;
- [ ] every intake requires a permitted purpose and retention-review date;
- [ ] storage is gitignored, protected, opaque-keyed, and not publicly served;
- [ ] OCR cannot overwrite authoritative data without human confirmation;
- [ ] sensitive actions create non-content audit events;
- [ ] retention review and controlled deletion work;
- [ ] ordinary logs and error output exclude document and identity content;
- [ ] full documents cannot be sent to external model providers;
- [ ] Pavel is configured as the immediate incident contact;
- [ ] the gate passes with synthetic acceptance fixtures.
- [ ] PLAN-INFRA's capacity threshold is satisfied and forecast margin recorded;
- [ ] a fresh encrypted backup passes integrity checks and an isolated restore;
- [ ] backup key custody, RPO/RTO, retention, and failure alert owner are recorded.

Capacity and recovery proof do not block synthetic implementation, but they do
block activation with real data. Visual refinements and later hardening remain
operational work unless another accepted decision promotes them to a gate.
