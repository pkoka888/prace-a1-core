# A1 open decisions: the investigation and the recommended answer

Status: decision brief, 2026-10-20. Non-PII. This brief gathers the evidence
behind each decision that is waiting on Jan, states the question in a form
that can be answered, and gives a recommended answer with its reasoning. It
decides nothing and changes nothing.

Companions: [the field mapping](a1-field-source-mapping.md) (the contract),
[the block options](a1-block-options.md) (the research behind it), and the
[gap analysis](a1-gap-analysis.md) (G1–G17).

## 0. The answers in one table

| Gate | Question in one line | Recommendation | Cost if you say no |
|---|---|---|---|
| **D1a** | Do you ever issue an A1 for a self-employed person **posted** to another State (official status 3.3)? | **No — not yet.** Keep the checkbox off; establish the arrangement per case instead | None now. If a case needs it, the 23-site activation is ready to run |
| **D1b** | Will you capture, per case, the facts Article 12 requires (prior activity, replaces another worker)? | **Yes** — capture them now, nullable, even with 3.3 off | 3.1 and 3.3 cannot be shown to satisfy Art. 12, so the generator should refuse them |
| **D2** | Should the client-confirmation copy carry a visible "not an issued A1" mark on every page? | **Yes** — the machinery exists; the digitisation direction makes it the safer default | A copy that looks official can be forwarded and mistaken for a certificate |
| **D10** | Should the model carry a situation record? | **Yes, but four fields, not six** — `posting_start`, `posting_end`, `prior_activity_start`, `replaces_worker` | Facts that make an A1 defensible have to be collected later, about past dates |
| **D11a** | May the agency retrieve an employer's registry record manually, review it and store it? | **Yes** | Employer facts stay un-sourced; the ARES enrichment has nowhere to attach |

Only **D1a** is genuinely a business-model question. The other four are
engineering decisions with a business consequence, and three of them are
cheaper to do now than later.

## 1. D1a — posted self-employed (official status 3.3)

### What the investigation found

The agency's own portfolio answers most of the question. `a1/review.csv` holds
five rows, and their official situations are:

| Rows | `status_profile` | Official status | Article |
|---|---|---|---|
| 1 | `posted_employee` | 3.1 posted employee | Art. 12(1) |
| 2 | `self_employed_multi_state` | 3.4 self-employed in two or more States | Art. 13(2) |
| 2 | `employee` (a coarse profile) | *situation undecided* | — |
| **0** | — | **3.3 posted self-employed** | Art. 12(2) |

Three things follow.

1. **The agency already does both halves.** It issues a posted-employee A1
   (3.1) and it handles self-employment (3.4). The missing cell is only the
   *intersection* — a self-employed person posted abroad.
2. **The two OSVČ rows carry the signature of 3.4, not 3.3.** Both have
   `activity_address = "DE, CZ"` — a *two-country* territory — and both are
   `activity_source_status = UNVERIFIED`. Working in two States is 3.4. A
   self-employed person *posted to Germany alone* for a defined period is 3.3.
   The distinction is not a product choice; it is a fact about each person's
   arrangement.
3. **The agency holds no situation facts at all.** No posting period, no
   prior-activity date, no replacement-worker flag. The only per-row data is
   the status profile, the institution profile, the activity address, the
   employment block, and the UNVERIFIED flags.

### The question, in a form that can be answered

> For the two self-employed cases (Švéda, Nistor): is the arrangement
> **"posted to Germany for a defined period"** (→ 3.3) or **"working in
> Germany and the Czech Republic"** (→ 3.4)?
>
> And going forward: will the agency take on an OSVČ posting at all?

### Recommended answer

**Keep the 3.3 checkbox off, and treat the question as a per-case fact
rather than a product decision.**

The reasoning is about cost, not about the law. Activating 3.3 is a
**23-site change** of which **16 fail silently** — they produce a wrong
certificate rather than an error. There is currently **no case that needs
it**. Switching the capability on before a case needs it means taking that
risk for nothing.

The better move is to make the *arrangement* recordable, so that the day a
case does need 3.3 the status follows from the fact rather than from a
product switch. That is D10.

**If the answer is "yes, we will have OSVČ postings"** then the
recommendation flips to "yes, activate" — but the D10 facts must be captured
**first**, because an A1 asserting Art. 12(2) without them is not defensible
if the host State checks, and the condition is checked by the
hosting State's labour inspectorate, not by the issuing institution.

## 2. D1b — the Article 12 situation facts

### What the investigation found

The Article 12 conditions are not a single question, and the cost is much
lower than D10's original framing suggested. Of the six fields originally
proposed, only **two are genuinely new facts**:

| Proposed field | Reality |
|---|---|
| `legal_basis` | **Derivable** from the status profile. Storing it would create two sources for one fact — exactly the class of defect the P block exists to close |
| `posting_start` / `posting_end` | The certificate's own 2.2/2.3. Real, and the model has **no home for them today** — `A1Case` has no validity-period field at all; the dates live only in the CSV/export row |
| `prior_activity_start` | **New fact** — Art. 14(3) Reg. 987/2009. The Practical Guide treats two months as normally sufficient |
| `replaces_worker` | **New fact** — Art. 12(1). Already mandatory for a posting on the Czech employee form, and *Alpenrind* (C-527/16) turned on it |
| `nace_code` | Belongs to the A block and the assignment fact, not to the case |

### The question

> Will you capture, per case: (a) the date the person began pursuing the
> activity in the host State, and (b) whether they replace another posted
> worker?

### Recommended answer

**Yes — capture both, now, as nullable, even with 3.3 off.**

1. **The replacement-worker question already applies today.** There is one
   3.1 case in the portfolio, and the Czech employee form makes that question
   mandatory "in the posting situation". That certificate cannot currently be
   shown to satisfy Art. 12(1), because nothing records the answer. This is
   not a future-3.3 problem; it is a present-3.1 problem.
2. **The prior-activity date is expensive to collect late.** It is a fact
   about a past date. If it is needed in two years, it has to be
   reconstructed from memory or from documents that may no longer exist.
3. **Both are cheap.** One nullable date and one nullable boolean, on a
   fact that is *about a case*, not about a person — so they can differ per
   case. Neither blocks saving a worker; a missing fact only blocks the one
   A1 operation that needs it.
4. **A missing fact should be visible, not defaulted.** The same principle as
   the status: an unknown stays unknown, and the absence of the answer
   blocks the certificate rather than the record.

**If the answer is "no"**, then the honest consequence is that the generator
should **refuse** 3.1 and 3.3 rather than issue them without the facts —
because an A1 that asserts the posting conditions without them is
indefensible in exactly the review where it matters.

## 3. D2 — the page-level mark on the client-confirmation copy

### What the investigation found

**What the switch is.** `mark_provisional(form, reason, visible_notice=True)`
draws `PROVISIONAL_NOTICE` on every page — *"NÁVRH – ČEKÁ NA POTVRZENÍ
OSSZ"* ("draft — awaiting OSSZ confirmation"). The current default is
`visible_notice=False`, so the client copy is unmarked and the marking lives
in the **package**: the manifest status `PROVISIONAL_NOT_FOR_OFFICIAL_USE`,
the manifest `notice` field, and `CLIENT_CONFIRMATION_CHECKLIST.md`.

**Three distinctions that matter.**

1. **A page mark is not official field 2.5.** Field 2.5 — *"The determination
   is provisional"* — is a statement about the **legal determination** under
   Art. 16(2) Reg. 987/2009. The notice is a statement about **this
   document**. Conflating them would put a legal claim on a draft.
2. **The repository already has a page-level mark, for the application
   draft.** `APPLICATION_DRAFT_NOTICE` — *"UNVERIFIED DRAFT – NEOVĚŘENÝ
   NÁVRH, NENÍ VYDANÉ A1"* — is stamped on every page of the application
   draft. The client copy is the *other* document, and it is the one that
   leaves the agency's hands.
3. **A page mark is a deterrent, not a control.** Watermarks are croppable
   and, since 2025, AI-removable. The reliable protection is structural, and
   the client copy already has it: the preview path sets `certificate = {}`
   and the document number to empty, so the copy has **no number, no
   signature and no institution** — an institution receiving it would reject
   it on sight.

**The new fact.** On 15 September 2026 the European Commission presented a
package of five proposals on fair worker mobility, including a **European
Social Security Passport (ESSPASS)** — a digital wallet for social security
documents, with **the A1 as the first document affected**. The stated aims
include making A1s easier to verify and **limiting the use of falsified
documents**. Separately, the A1 reform provisionally agreed in April 2026
(Council adoption and OJ publication still pending) would exempt short
business trips and add a three-day exemption. The direction of travel is a
digitised, verifiable A1 — which makes the *provenance* of a document
decisive, and makes a copy that looks like a certificate a liability rather
than a nicety.

### The question

> Should the client-confirmation copy carry a visible "this is not an issued
> A1" mark on every page?

### Recommended answer

**Yes — turn the existing switch on for the client copy.**

The argument is the *worker's* protection, not the agency's tidiness. The
client is being asked to check facts on a document that will become their
A1; the copy is the one artefact that leaves the agency before the real
certificate exists; and the Commission is explicitly moving to make
look-alike documents detectable. The machinery is written, tested and
one-flag away.

Two conditions:

1. **It must be the document-status notice, not 2.5.** `PROVISIONAL_NOTICE`
   ("draft — awaiting OSSZ confirmation") is correct; ticking the
   provisional-determination checkbox on a draft would be wrong.
2. **The package keeps its own marking.** The page notice and the package
   status are two different things and both should say what they are. The
   page says *this document*; the package says *this is not an issued A1 and
   carries no number, signature or institution*.

**If the answer is "no"**, then the protection must rest entirely on the
package, and the portal should make that visible to the operator at the
moment the copy is handed over — otherwise the worker receives an unmarked
copy and a package they never see.

## 4. D10 — the situation record

### What the investigation found

The agency holds **no** situation facts today, and the model has no home for
the certificate's own validity period: `A1Case` carries `source_hash`,
`source_snapshot_json`, `bound_identity_sha256`, `readiness`, the artifact
references, `external_status`, the visual-confirmation fields and the
evidence fields — but **no validity dates**. Fields 2.2 and 2.3 live only in
the CSV row and the export dict. `Assignment` does have `start` and `end`
date fields for the employment relationship.

### The question

> Should the model carry a situation record, and with which fields?

### Recommended answer

**Yes — but four fields, not the six originally proposed.**

| Field | Type | Why |
|---|---|---|
| `posting_start` | date, nullable | field 2.2. No model home today |
| `posting_end` | date, nullable | field 3.2/2.3. Also the 24-month bound (Art. 12) and the Art. 16(3) two-month definitiveness clock |
| `prior_activity_start` | date, nullable | Art. 14(3). Two months is normally sufficient |
| `replaces_worker` | boolean, nullable | Art. 12(1). Mandatory for a posting on the Czech form |

**Drop `legal_basis`** — it is derivable from the status profile, and storing
it would create two sources for one fact, which is the defect class the P
block's ledger exists to close. **Move `nace_code`** to the A block, where it
belongs: it is a property of the activity, not of the case.

The cost is four nullable fields on a per-case fact, all additive, none
blocking the saving of a worker. `posting_start`/`posting_end` additionally
let the certificate's own period become a *sourced* fact instead of a policy
one-year default.

**If the answer is "no"**, then D1b is "no" as well, and the generator
should refuse 3.1 and 3.3 rather than issue them without the facts.

## 5. D11a — the offline ARES import

### What the investigation found

- The repository records exactly **one** ARES artefact: the employer record
  under `a1/`, and a single point-lookup URL in
  `a1/employees_normalized.json`. The other endpoints, the rate limit and the
  "free and key-free" characterisation are **external** research, now marked
  as such in the block options.
- An offline import crosses **no** boundary at runtime: a human runs the
  lookup, reviews the result, and the reviewed record is stored with its
  source. It is the same mechanism the institution profiles already use, and
  the same one the `LegalEntity` master would be seeded from.
- The personal-data angle is real: for a sole trader the IČO is a natural
  person's registration number, publicly searchable, and it resolves to a
  name. A `LegalEntity` row for a sole trader is personal data.

### The question

> May the agency retrieve an employer's registry record manually, review it,
> and store it as the employer's fact?

### Recommended answer

**Yes.** It is free, public and key-free; it needs no host or network
change; it is the only way the employer facts acquire a source; and it
unblocks E-E without waiting on D11b.

Two conditions:

1. **The imported record carries its provenance** — source URL, retrieval
   time and content hash — so that a later correction is traceable to a
   registry event rather than appearing as an unexplained change. The ARES
   change-notification channel exists for exactly this, and it is the part
   that would need D11b; the offline import does not.
2. **A sole trader's record is handled as personal data**, with the same care
   as the worker's identity — and its registration identifier is not published
   in committed documents. That last point is now enforced:
   `scripts/check_git_content.py` detects a business-registration identifier
   in a tracked document, and the test that guards it is part of the
   `infrastructure_git_workflow` package check.

**D11b** — runtime server-side egress — is a *different* question and is not
needed for the import. It is a host and network decision, which this
repository's own rules place with the sysadmin.

## 6. One cross-cutting fact that should shape the sequencing

The Commission's September 2026 package proposes an **EU Social Security
Passport**, with the A1 as the first document digitised, aimed partly at
"limiting the use of falsified documents" and making certificates easier to
verify. The A1 reform agreed in April 2026 is still awaiting Council adoption
and OJ publication.

Three consequences for this repository:

1. **The data model outlives the PDF.** A digitised A1 is a signed, verifiable
   record with a provenance chain. The durable asset is the *facts and their
   evidence*, not the rendered form. That argues for doing the P block's
   ledger before polishing the rendering.
2. **Verification becomes a product surface.** A host institution, an
   inspectorate or the European Labour Authority will check an A1's
   authenticity. The repository already holds the ingredients — source hash,
   snapshot, artifact hash, receipt build id and commit — and the P block's
   typed decisions would make them checkable by someone other than us.
3. **The rules are moving, so the *facts* should be captured loosely.** The
   April 2026 reform would exempt short business trips and add a three-day
   exemption, and further changes are likely. A model that stores the
   *situation* as facts — rather than encoding the rules in code — survives a
   reform better than one that does not. That is the strongest argument for
   D10 and for E-L's decision tree.

None of this changes what the five decisions above should be. It changes the
order: the situation record and the ledger first, the rendering second.

## 7. The answers, if you want to give them

A single reply in this form is enough:

- **D1a**: no / yes, and for which cases
- **D1b**: yes / no
- **D2**: yes / no
- **D10**: yes with four fields / no
- **D11a**: yes / no

Each answer has a documented consequence in this brief, and the engineering
work it unblocks is already specified: the 23-site activation path for D1a and
D1b, the visibility flag for D2, the additive migration for D10, and the
`LegalEntity` seed path for D11a.
