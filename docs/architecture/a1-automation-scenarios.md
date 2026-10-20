# A1 automation scenarios: what-if per topic

Status: brainstorm and design options, 2026-10-20. Companion to the
[field → source mapping](a1-field-source-mapping.md) and the
[gap analysis](a1-gap-analysis.md). Nothing here is implemented, scheduled or
approved. Scenarios describe *options and their failure modes*, not decisions.

Every scenario has the same shape:

- **Trigger** — what starts it.
- **Automation** — what a machine may do, and what it must not.
- **Human gate** — where a person decides, and what evidence they decide on.
- **Failure mode** — what goes wrong if this is automated wrongly, and what
  the failure looks like from the outside.
- **Feasibility** — S1/S2/S3 from the gap analysis, or a note that the
  scenario is blocked by a missing business fact.

The rule that holds across all of them, from the official form and from this
repository's existing gates: **a machine may propose, a human must confirm,
and a generated document never establishes a fact.** An A1 certificate is
binding on the institution of the State of stay (*Alpenrind*, C-527/16), so
the cost of a wrong field is not a cosmetic defect.

## 1. Topic W — person identity

### W1 — scan arrives, identity is proposed

- **Trigger** — a new scan lands in `scans/incoming/`.
- **Automation** — OCR extracts candidate fields; the identity service
  creates `IdentityEvaluation` and `WorkerIdentityClaim` records. The claim's
  organization/type/issuer/identifier hash is a *deduplication key*, not a
  confirmed identifier.
- **Human gate** — the BO field reviewer confirms each field individually
  through `field_review.confirm_field_review`, which binds the proposal's
  source, version, region and worker revision.
- **Failure mode** — a machine confidence score is read as a confirmation.
  The visible symptom: a worker record with a plausible but unverified name,
  and a certificate that was never reviewed.
- **Feasibility** — implemented. The multi-page MRZ cross-check that caught
  a page swap between two workers' second scan pages is exactly this
  scenario working. The scan filenames are deliberately not quoted here:
  they carry the worker's own name, and a committed document is not a
  place for a real identity.

### W2 — the same person appears under two spellings

- **Trigger** — a new claim's organisation/type/issuer/identifier hash
  matches an existing claim, or a reviewer proposes an existing worker.
- **Automation** — `IdentityResolution` binds an explicit human association
  to evaluated evidence, with an expected worker version and revision. It
  does **not** confirm individual identity fields.
- **Human gate** — the association is signed by the reviewer.
- **Failure mode** — two workers merge, so one person's history splits and
  the other is lost. The visible symptom: a certificate for a person whose
  employment history belongs to someone else.
- **Feasibility** — implemented. This is the highest-value automation in the
  whole chain, because it is the one that prevents a wrong person being
  certified rather than a wrong value being printed.

### W3 — address enrichment proposes an OSSZ

- **Trigger** — a confirmed residence address matches an
  `address_enrichment.json` rule exactly.
- **Automation** — propose district, postal code and a *suggested* OSSZ.
- **Human gate** — a reviewer accepts the suggestion. It stays a suggestion.
- **Failure mode** — the suggested OSSZ silently replaces the configured
  issuing institution. The existing policy forbids this — "OSSZ is a review
  suggestion and never silently replaces the configured issuing institution" —
  and the visible symptom would be a certificate issued by the wrong office.
- **Feasibility** — implemented. The rule is exact-match only, so a near
  match proposes nothing.

### W4 — habitually-residence vs permanent address

- **Trigger** — the worker states an address that differs from the registered
  permanent address.
- **Automation** — none. This is a legal determination (centre of vital
  interests) under Reg. 883/2004 Art. 1(j) and ČSSZ's own definition.
- **Human gate** — the worker confirms which address is the habitual
  residence; 1.8 carries it.
- **Failure mode** — 1.8 and 1.9 (or the permanent address) get confused, so
  the certificate names the wrong residence and the competence rule picks the
  wrong OSSZ.
- **Feasibility** — partially implemented; 1.9 has no model field yet (G12).

## 2. Topic E — employer, role and situation

### E1 — employer identified from an ARES lookup

- **Trigger** — the IČO is known and the employer is not yet a record.
- **Automation** — look the registration up, capture the legal name and
  registered address, record the registry, the retrieval time and the
  response hash.
- **Human gate** — the reviewer accepts the registry address as the Section
  4 address, or supplies a different one.
- **Failure mode** — the registry's registered address differs from the place
  of work, and 4.4 prints the registered address as if it were the workplace.
  The official form asks for the *registered* address, so this is often
  correct — but the point where it is wrong is "the employer moved and the
  registry has not caught up".
- **Feasibility** — partially implemented. ARES enrichment exists
  (the ARES-enriched employer record under `a1/`); there is no `LegalEntity` master to
  attach it to (G3).

### E2 — the same employer across a whole cohort

- **Trigger** — 30 workers reference the same employer.
- **Automation** — one `LegalEntity` record, referenced by 30 employment
  facts.
- **Human gate** — one review of the entity; the employment facts reference
  it.
- **Failure mode** — a correction to the employer propagates to all 30
  certificates, including ones already issued. The visible symptom: a
  retrospectively wrong certificate batch.
- **Feasibility** — blocked by G3. Today each worker's employer facts are
  independent, so the blast radius of a correction is one worker. This is
  the one place where a *shared* entity is a genuine risk, and it argues for
  a per-case snapshot that pins the entity version used — which the existing
  `A1Case.source_snapshot_json` already does for every other value.

### E3 — the situation is declared, the status is derived

- **Trigger** — a worker states they are posted, or work in two States.
- **Automation** — derive 3.1/3.2/3.3/3.4 and 4.1.1/4.1.2 from the
  employment role and situation. Exactly one status; the two sections can
  never disagree.
- **Human gate** — the worker confirms the situation; the official form's
  Section 3 is a *declaration* by the applicant.
- **Failure mode** — the wrong status is printed, so the certificate states
  the wrong applicable legislation. The visible symptom: the State of stay
  treats the person as uninsured, because the certificate says the wrong
  thing. This is the most expensive failure in the whole form.
- **Feasibility** — implemented for 3.1/3.2/3.4; **3.3 cannot be expressed**
  (G1).

### E4 — multiple employers

- **Trigger** — the ČSSZ application has one employer block per employer
  ("Máte-li více zaměstnavatelů v ČR, vyplňte oddíl E. vícekrát").
- **Automation** — record each employment fact; the case selects one.
- **Human gate** — the reviewer selects which employment the certificate
  describes, and that selection is recorded.
- **Failure mode** — the wrong employment is selected, so 4.3 names an
  employer the person has already left.
- **Feasibility** — not implemented. The selection is not modelled, so today
  the choice is implicit in whichever row the CSV carries.

### E5 — self-employed: the employer is the person

- **Trigger** — the status profile is `self_employed_multi_state`.
- **Automation** — the employer name is the person's own surname and
  forename in Czech display case with no OSVČ suffix, and the employer
  address is copied from the residence (`a1_core.py:321-334`).
- **Human gate** — the derived block is visible and reviewable like any
  other.
- **Failure mode** — the derivation is a *rule* hidden inside the renderer.
  If a rule changes, previously issued certificates are no longer
  reproducible, and nothing in the record says which rule produced them.
- **Feasibility** — implemented, but as renderer behaviour rather than a
  stored fact. Under the employer-as-organization decision it becomes a
  `LegalEntity` of type `sole_trader` whose identity is the person's own
  registration id — reproducible, reviewable, and a legal entity like any
  other.

## 3. Topic A — activity and territory

### A1 — the territory default

- **Trigger** — a self-employed multi-state row with no reviewed territory.
- **Automation** — the policy default `DE, CZ` is proposed for 5.2.
- **Human gate** — a reviewer confirms or replaces it. An explicitly
  reviewed row-specific territory override always wins.
- **Failure mode** — the default is read as a fact. The visible symptom: a
  certificate claiming activity in two States that the person never
  declared.
- **Feasibility** — implemented. The open part is classification, not
  behaviour: `DE, CZ` is a *content* default living in a file that describes
  itself as holding *display* defaults (G14).

### A2 — no fixed address

- **Trigger** — the activity has no stable address (the ČSSZ example is an
  international truck driver).
- **Automation** — none. 5.3 is a fact about the activity.
- **Human gate** — the reviewer ticks 5.3, and 5.2 is left blank because
  R5 makes them alternatives.
- **Failure mode** — 5.2 and 5.3 are both filled, or both are blank, and the
  reader of the certificate cannot tell what was meant.
- **Feasibility** — not implemented; the checkbox is hardcoded false (G11).

### A3 — the activity block for a posted employee

- **Trigger** — an employee is posted; Section 5 becomes applicable because
  an activity is pursued in the host State.
- **Automation** — 5.1 asks for the *name and code of the firm* where the
  person will be employed. This is not the employer's Section 4.3 name and
  not a street address.
- **Human gate** — the reviewer supplies the host-side entity and its code.
- **Failure mode** — the Section 4 employer is copied into 5.1, which
  misstates where the activity will be pursued. The visible symptom: 5.1
  names a Czech company for a certificate covering German work.
- **Feasibility** — not implemented. Today `activity.name` is blank for
  employees and the "CZ employee posting to Germany" preview scenario
  (`--posting-scenario cz_employee_to_de`) shows the shape: section 5 needs a
  *host workplace*, and a country alone does not complete it.

## 4. Topic O — issuing institution

### O1 — the institution profile is verified

- **Trigger** — a profile is added or its source page changes.
- **Automation** — fetch the page, extract the contact and signatory data,
  diff against the current profile, and propose an update.
- **Human gate** — a reviewer accepts the diff.
- **Failure mode** — the *office contact* is promoted to the *certificate
  signatory*. Every current profile carries
  `CONTACT_NOT_CONFIRMED_SIGNATORY` precisely to stop this, and the visible
  symptom would be a certificate that appears to have been signed by
  someone who did not sign it.
- **Feasibility** — the mechanism exists in
  `scripts/research_ossz.py` and is the canonical use case for the
  LangGraph research workflow in
  [langgraph-integration.md](langgraph-integration.md).

### O2 — competence: which OSSZ issued this?

- **Trigger** — a case needs an issuing institution.
- **Automation** — propose the competent OSSZ by the ČSSZ rules (registered
  office of the employer, place of residence, or any OSSZ where competence
  cannot be determined) and by the exact-address enrichment.
- **Human gate** — a reviewer confirms. The configured issuing institution is
  never replaced silently.
- **Failure mode** — a certificate issued by an institution that lacks
  competence, which the State of stay may reject.
- **Feasibility** — partially implemented; the enrichment exists as rules
  with sources, but there is no `Institution` master to select from (G4).

### O3 — the contact block (6.7–6.9)

- **Trigger** — the profile is rendered.
- **Automation** — render the contact from the profile.
- **Human gate** — none needed; it is institution data.
- **Failure mode** — the coordinates do not exist, so the block silently
  renders empty on an official form that expects it.
- **Feasibility** — the data is there; only the layout coordinates are
  missing (G2). This is the cheapest gap in the whole list to close.

## 5. Topic C — the certificate

### C1 — provisional draft for client confirmation

- **Trigger** — a reviewed row is ready for the client to see.
- **Automation** — reserve a stable provisional number, generate the issue
  date under the Mon/Wed 61–180 day policy, derive a one-year validity
  period, render, and stamp the package `INCOMPLETE_UNVERIFIED_PREVIEW`
  with the visible provisional notice on every page.
- **Human gate** — the client confirms the facts; the reviewer then decides
  on issuance.
- **Failure mode** — the draft is treated as a certificate. The visible
  symptom: a client sends a document that is not valid. The existing
  `assert`ion that the draft notice only appears when
  `form["meta"]["application_draft"]` is true, and the separation of
  `validated_by_user` from `visual_confirmed`, exist to prevent this.
- **Feasibility** — implemented.

### C2 — the official promotion

- **Trigger** — authoritative certificate evidence arrives: the certificate
  facts, the signatory, and the issue date.
- **Automation** — validate the input bundle, pin the profile bytes, publish
  atomically into a protected package, and record the receipt and audit
  event.
- **Human gate** — the approval is the `Release1aAcceptance` record, bound to
  a git commit, a clean tree and a build id.
- **Failure mode** — a generated identifier, a readiness report or a visual
  PASS is read as issuance. The visible symptom: the system says a
  certificate was issued when no institution ever issued one.
- **Feasibility** — implemented.

### C3 — resume a long run after an interruption

- **Trigger** — a batch generation is interrupted.
- **Automation** — resume from a checkpoint, reconcile what was already
  published, and continue.
- **Human gate** — none for the mechanics; the operator needs the run to
  stop rather than guess.
- **Failure mode** — the run "resumes" and does nothing, returning success.
  That is the current behaviour: `--resume` prints "Full checkpoint resume
  requires database implementation" and exits 0 (G10).
- **Feasibility** — the capability is proven by the agent-ops workflow
  (37 tests, including `test_checkpoint_resumes_in_fresh_interpreter` and
  `test_reopen_after_fault_reconciles_durable_effect`). Only the A1
  workflow's wiring is missing.

## 6. Topic P — provenance, review and authority

### P1 — the machine proposes, the human confirms

- **Trigger** — any value that a machine could fill.
- **Automation** — create a proposal with its source, version, region and
  hash.
- **Human gate** — a signed decision with actor, time, scope and reason.
- **Failure mode** — a proposal is treated as a value. The visible symptom:
  a "confirmed" field nobody confirmed.
- **Feasibility** — implemented.

### P2 — a value changes after a certificate was prepared

- **Trigger** — a reviewer corrects a confirmed field.
- **Automation** — create a successor snapshot, mark the dependent artifact
  stale, and fail the stale confirmation on an optimistic revision check.
- **Human gate** — a replacement of a confirmed value requires a reason.
- **Failure mode** — the old certificate is issued against superseded facts.
  The visible symptom: a certificate whose PDF does not match the current
  record.
- **Feasibility** — implemented.

### P3 — who decided what

- **Trigger** — an auditor asks why a value is on a certificate.
- **Automation** — walk the provenance chain: field → proposal → decision →
  actor → time → source hash → snapshot → package → artifact hash.
- **Human gate** — none; it is a read.
- **Failure mode** — the answer is "the CSV said so". The visible symptom:
  no accountable actor for a binding document.
- **Feasibility** — partially implemented. The chain exists for identity and
  assignment facts; the flat review flags (G15) cannot carry actor, time or
  scope.

## 7. Cross-cutting: where LangGraph fits

The scenarios above are mostly *not* graph problems. They are field-level
validations over a deterministic core, which the existing
[LangGraph guide](langgraph-integration.md) already places outside LangGraph
on purpose.

What genuinely benefits from a graph is the **multi-source, multi-step,
partly-failable** part:

- **O1** — institution verification: try URL A, fall back to URL B, then to a
  manual proposal, with a checkpointer so a long verification resumes.
- **Research workflows** — gather → analyse → summarise, where the branch
  depends on what the fetch returned.
- **Provider fallback** — OCR provider A, then B, then queue for review.

What must **not** move into a graph: `build_form_data`, `row_to_form`,
`generate_a1_pdf`, the 44-column contract, the validation gates, the
provisional notice, or the issuance workflow. A graph that calls the core is
fine; a graph that replaces the core is not.

The measured state of that layer, including three defects found by running
it, is in the [gap analysis](a1-gap-analysis.md#7-automation-gaps-langgraph)
and the [LangGraph guide](langgraph-integration.md).
