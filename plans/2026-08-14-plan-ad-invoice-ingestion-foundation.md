# Plan AD — Invoice Ingestion and Reviewed Export Foundation

**Status:** active
**Prerequisite:** Coordinated with Plans M3, N, O, J, H, P, and AC. Research,
domain-contract design, and an in-memory synthetic proof may proceed, but
persistence/adapters, production implementation, and Plan AD acceptance require
DEC-015 accounting-specialist acceptance.
**Milestone:** M1B proof; later certified implementation
**Owner:** product engineering + Czech/German accounting specialists
**Lane:** Parallel non-blocking M1B proof

## Objective

Define and prove a reusable, privacy-conscious invoice ingestion boundary:
protected scan/PDF → preprocessing → OCR/layout extraction → field proposals →
deterministic validation → human review → immutable confirmed invoice version →
database-ready record → versioned Slauf CSV export. Plan AC supplies market and
technical evidence; it does **not** authorize accounting behavior.

DEC-015 in `docs/decisions/decision-register.md` is the explicit specialist gate.
Until it is accepted, Plan AD remains a public/synthetic design and in-memory
contract proof: no fiscal ground truth, Slauf mapping, persistence/adapter
implementation, Plan AD acceptance, or production behavior may be inferred from
AC research or benchmark results.

## Product boundary (Version 1)

```text
Protected scan/PDF
→ preprocessing
→ OCR/layout extraction
→ field proposals
→ deterministic validation
→ human review
→ immutable confirmed invoice version
→ database-ready record
→ versioned Slauf CSV export
```

Version 1 explicitly excludes:

- authoritative bookkeeping;
- VAT or tax advice/calculation;
- ledger posting;
- payments;
- direct writes to accounting systems;
- real customer invoices;
- customer-facing production activation.

Later accounting adapters and lightweight customer workflows require separate
decisions (ADR). Slauf CSV structure is **not** guessed: obtain an official
import specification or a sanitized synthetic column example before freezing
columns, encoding, delimiter, date/decimal formats, enumerations, and row
semantics.

## Domain interfaces

Define (framework-independent Python contracts):

- `Document`
- `DocumentVersion`
- `ExtractionRun`
- `FieldProposal`
- `ValidationFinding`
- `ReviewDecision`
- `InvoiceRecordVersion`
- `ExportProfile`
- `ExportRun`
- `AuditEvent`

### Field states

`missing`, `proposed`, `confirmed`, `conflict`, `rejected`, `superseded`.

Every record preserves: source hash, page/bounding-box provenance, engine/model/
config version, confidence, validation results, organization scope, reviewer,
timestamp, reason, immutable revisions, and idempotency key.

### Minimum invoice fields

supplier/customer identity, IČO/DIČ, invoice and variable symbols, issue/DUZP/
due dates, currency, net/VAT/gross totals, VAT breakdown, payment identifiers,
and optional line items.

## Adapter boundaries

Two framework-independent interfaces:

- `extract(document_version) -> proposal_set`
- `export(confirmed_invoice_version, export_profile_version) -> artifact + reconciliation_report`

No extractor may overwrite confirmed data. Every export binds to an immutable
confirmed invoice version and an export-profile version.

## Evidence basis

- Plan AC OSS/LLM benchmark informs component-by-layer selection.
- Synthetic Czech invoice corpus (VAT 21%/12%, valid IČO/DIČ) under
  `research/synthetic/`; its ground truth is pending accounting-specialist review.
- Local baseline OCR benchmark pending actual engine execution (currently
  `unproven`).

## Current checkpoint — adversarial in-memory contract proof

The framework-independent contracts are implemented in
`src/invoice_ingestion/contracts.py` with synthetic adversarial tests in
`tests/test_invoice_ingestion_contract.py`. The proof rejects direct construction
of confirmed extraction proposals, empty or unreviewed confirmed records,
cross-scope adapter output, stale/tampered reviews, idempotency replay collisions,
unsafe public storage references, unrestricted audit text, and fabricated export
reconciliation. Authorized service functions bind scope, revision, proposal
fingerprint, review decision, adapter output, and paired audit outcomes.

This checkpoint proves only the behavior of an in-memory contract. It does not
prove persistence constraints, transaction isolation, authorization storage,
denial-audit persistence, OCR quality, fiscal correctness, concrete Slauf CSV
columns, or production readiness. Those remain gated by Plan O implementation,
synthetic fixtures reviewed by the accounting-specialist role, an approved Slauf
specification, and DEC-015.

## Exit

- Domain interfaces and adapters specified and unit-tested with synthetic data.
- Persistence/transaction adapters prove the same scope, immutability,
  idempotency, concurrency, authorization, and audit invariants.
- Synthetic review + CSV prototype demonstrated against specialist-reviewed
  ground truth after DEC-015 is accepted.
- DEC-015 accepted by the recorded accounting-specialist role before
  persistence/adapters, production implementation, or Plan AD acceptance.
- No production activation, no real invoices, no tax implementation.

## Exclusions

- No real invoices, employee records, or PII.
- No tax calculation implementation.
- No authoritative bookkeeping or payment systems.
- No production deployment.
