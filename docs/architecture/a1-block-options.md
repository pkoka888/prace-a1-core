# A1 block options: analysis, suggestions, dependencies, comparison

Status: research and options, 2026-10-20. Non-PII; synthetic examples only.
This document does not decide, implement, migrate or activate anything. It
answers the status-3.3 default question, then for each of the six data blocks
sets out the analysis, at least two suggestions from **different perspectives**,
the dependencies of each suggestion, and a comparison. It refines
[the field mapping](a1-field-source-mapping.md) and
[the gap analysis](a1-gap-analysis.md) and feeds the decision gates D1a, D1b and D2–D12.

Every suggestion is backed by a source listed in §11, and by the repository
history where the decision is this repository's own.

## 1. The status-3.3 default, answered

**Question.** When official status 3.3 (posted self-employed) is not
mentioned, what must the default be?

**Answer: 3.3 must have no default at all. The default is "undecided", and
it fails closed.**

The reasoning is not a preference; it follows from what the status *is*.

1. **The status is a legal determination, not a piece of data the applicant
   merely omits.** Section 3 of the official form asks the institution to
   declare which of the twelve situations in Title II of Regulation (EC)
   No 883/2004 applies. The ČSSZ application makes that determination
   explicit: the form's central choice is *"žádám o posouzení své situace
   dle příslušného článku platných koordinačních nařízení … jako vyslání /
   souběh činností / výjimka / jiná situace"*, and the employee variant
   carries a matching *"Žadatel má status: zaměstnanec / státní úředník /
   pracovník v mezinárodní přepravě / smluvní zaměstnanec ES / námořník /
   letový personál"*. The applicant **declares** the status; the institution
   determines the legislation on that basis.

2. **Silence is not a declaration of anything.** An omitted status cannot
   become 3.1, 3.4 or 3.3 by default, because each of those asserts a
   different set of legal consequences (different competent institution,
   different applicable legislation, different certificate validity). A
   default that picks one of them asserts a legal fact nobody stated.

3. **The regulation itself provides the correct treatment for an
   undetermined situation.** Article 16(2) of Regulation (EC) No 987/2009:
   where a person pursues activities in two or more Member States, the
   designated institution *"shall without delay determine the legislation
   applicable … **That initial determination shall be provisional**"*, and
   under Article 16(3) it becomes definitive within **two months** unless
   another institution disagrees. So the law's own answer to "not yet
   settled" is *provisional determination by the institution*, not a default
   status — and it is official form field **2.5**, which the form labels
   *"The determination is provisional"*.

4. **The repository's own principle agrees.** "Unknown values stay unknown.
   Do not invent them. Do not coerce missing facts into placeholder values
   to satisfy a check; the placeholder must be visibly distinguishable from a
   real reviewed value at every layer." An unstated status that silently
   becomes 3.4 is exactly a coerced placeholder.

**So the rule is:**

| Situation | Section 3 | What happens |
|---|---|---|
| The applicant stated the situation | exactly one box ticked | the certificate is rendered for that situation |
| The applicant stated a self-employed posting (Art. 12(2)) | **3.3** ticked, 4.1.2 ticked | the 19-site activation path runs — but see §1.1, it is not code sites alone |
| The applicant stated nothing | **no box ticked** | the case is rendered as an undecided worksheet with the status listed as a missing field, and **no A1 is issued** |
| The coarse worker profile is `employee` or `self_employed` | **no box ticked** | the profile selects the *application variant* and the worksheet's offered choices; it is never promoted to a status |

**This rule was not what the code did, and the discrepancy was found by
review rather than by reading.** The completion preview assigned a status when
none was supplied: for the self-employed variant it set
`status_profile = "self_employed_multi_state"`, which ticked official status
**3.4** and left the status out of `missing_fields`; for the employee variant
it raised `EMPLOYEE_STATUS_PROFILE_REQUIRED`; and a coarse `self_employed`
profile raised `UNSUPPORTED_STATUS_PROFILE`. In other words the repository did
precisely what point 4 above forbids — it silently turned an unstated status
into a legal status — and the rule above was written as if it did not.

That behaviour is now corrected, and the correction is enforced by tests
rather than by prose:

- `scripts/a1_completion_preview.py` no longer assigns a status when none was
  supplied, and accepts a coarse `self_employed` profile the same way it
  accepts a coarse `employee` one — as a **variant**, with the situation left
  undecided.
- `tests/test_a1_status_default.py` asserts that no Section 3 box is ticked
  for every unstated-status and coarse-profile case, that the status is
  reported as a missing field, and that the supported profile set is
  enumerated consistently in all six places that name it.

The undecided worksheet still asserts **nothing**: no Section 3 box and no
Section 4.1 box. That is deliberate and pre-existing — the worksheet is a
request for the reviewed choice, and it must not assert an employment kind
that the determination has not settled. The role is carried in
`meta.variant` and in `employment.kind`, not in a rendered checkbox.

The remaining defect is the one this document was written to describe:
`status_posted_self_employed` is hardcoded `False`, so the *stated* Art. 12(2)
situation cannot be expressed either.

### 1.1 The activation path is larger than 23 code sites

The activation path in [the field mapping §15](a1-field-source-mapping.md#15-status-33-switchable-design-default-no)
is a list of **code** sites. The legal reading adds **data** sites, and this
is the finding that should change D1's framing.

Article 12(2) of Regulation 883/2004 does not apply to every self-employed
person who goes abroad. Three conditions gate it, and the model has no home
for any of them:

| Condition | Authority | Consequence for the model | Model has a home? |
|---|---|---|---|
| The activity abroad is a **"similar activity"** to the one normally pursued | Art. 12(2) with Art. 14(4) Reg. 987/2009 — *"the criterion … shall be that of the actual nature of the activity, rather than of the designation of employed or self-employed activity"*, applied to the *sector* | a fact about the activity, not derivable from the status | **No** |
| The self-employed has *"already pursued his activity for some time"* before moving | Art. 14(3) Reg. 987/2009; the Commission's Practical Guide treats **two months** as normally sufficient | a start date, compared against the posting start | **No** |
| The activity abroad lasts **no more than 24 months** | Art. 12(2) Reg. 883/2004 | a bound on 2.2/2.3 | **No** — the provisional period is a policy default of one year, and the 24-month cap is not checked |

The same three conditions apply to **3.1** (posted employee), with two
differences and one addition: the 24-month cap and the prior-activity
condition are identical, but Art. 12(1) adds *"he is not sent to replace
another person"* — a condition the CJEU examined in *Alpenrind* (C-527/16)
and which the ČSSZ employee form makes mandatory in exactly those words
(*"Údaj o nahrazování jiného vyslaného pracovníka je povinný v situaci
vyslání"*), plus the employee form's own *"Na zaměstnance se vztahují
právní předpisy vysílajícího státu minimálně jeden měsíc před vysláním"*.

**Consequence.** D1 is not "does the agency issue posted-self-employed A1s?"
It is two questions:

- **D1a** — does the agency issue them at all? (business fact, Jan)
- **D1b** — if yes, is the agency willing to capture the situation facts
  (similar activity, prior-activity start, 24-month bound, replacement-worker
  flag) that Art. 12 requires? (business fact, Jan)

If D1a is no, the generator should refuse such a row and the fact is recorded
once. If D1a is yes but D1b is no, the agency cannot lawfully issue an A1
for those cases, and the right behaviour is again to refuse. Either way the
**default stays "undecided"**; what changes is whether a *stated* 3.3 can be
represented.

**Recommendation:** keep D1's default **NO** for the *checkbox* (3.3 unticked
unless stated), split it into D1a and D1b as above, and add a third
gate **D10 — the situation-fact record** — which asks whether the model
should carry a `Situation` record with `legal_basis`, `posting_start`,
`posting_end`, `prior_activity_start`, `replaces_worker`, `nace_code`. Those
six fields are the minimum that makes either 3.1 or 3.3 defensible, and
they are needed **regardless** of the D1 answer, because 3.1 is already
expressible today without them.

## 2. How to read the options

Each block carries two suggestions, and they are deliberately of different
kinds:

- a **legal/institutional** option — what the authority requires. This is a
  *constraint*: the system may not contradict it. It is not a choice.
- an **engineering/data** option — how to represent it. This *is* a choice,
  and it is compared on cost, risk and reversibility.

The two are orthogonal in every block, and in five of six the recommendation
is to take **both**, in the order given. Where they conflict, the legal
option wins on the value and the engineering option wins on the mechanism.

A third option appears in blocks **E, A, W and P**, where a third
perspective is genuinely different rather than a restatement: a *vocabulary*
perspective for A, an *adjudication* perspective for W, an *operational and
retention* perspective for P, and a *depth* alternative for E.

## 3. Block C — the certificate

**Analysis.** The certificate is the only artifact in the system that binds
another State's institution. Article 5(1) of Regulation 987/2009: the
documents are *"to be accepted by the institutions of the other Member States
for as long as they have not been withdrawn or declared to be invalid by the
Member State in which they were issued"*. The CJEU in *Alpenrind*
(C-527/16, 6 September 2018) confirmed that an A1 binds both the
institutions **and the courts** of the State where the work is carried out,
even with retroactive effect. The Court's later judgment in *ZUS* (C-422/22,
16 November 2023) adds the decisive characterisation: the A1 *"is not a
measure giving rise to rights but a declaratory act"*, and the issuing
institution may **withdraw it of its own motion** if it finds the evidence
incorrect — and must then inform the other institutions and the person
concerned. In *DRV Intertrans* (C-410/21, 2 March 2023) the Court accepted a
state in which an A1's binding effects are **provisionally suspended**
pending review.

The repository currently models the certificate as: a `run_id` in the
generation manifest, a `document_id` in `cohort.json`, an `A1Case` row, and
the rendered PDF with its hash. The header number's lifecycle was fixed in
`1fb8da1` (*"preserve A1 draft numbers across generation revisions"*) and the
visual confirmation was bound to exact generation evidence in `bbbbf4c`. So
the *rendering* side is disciplined; the *legal lifecycle* side is thin.

### C-L — legal: bound the certificate, and derive provisionality from the situation

The certificate's own fields are already constrained by law, and the
repository does not yet enforce the constraints:

| Field | Rule | Authority | Today |
|---|---|---|---|
| 2.2/2.3 | For a posting, the activity "does not exceed twenty-four months" | Art. 12(1) and 12(2) Reg. 883/2004 | unbounded; the provisional default is a policy one-year period |
| 2.3 | Beyond 24 months, the posting State requires an **Art. 16 agreement**; without one, the legislation of the State of work applies from the end of the 24 months | Practical Guide, point 12 | not modelled |
| 2.4 | "The certificate applies for the duration of the activity" — the alternative to a bounded period | official form 2.4 | rendered, derived from 2.2/2.3 presence |
| 2.5 | **Mandatory** where the initial determination is provisional, i.e. the Art. 13 situations | Art. 16(2) and 16(3) Reg. 987/2009 | not rendered; derived from `form["meta"]["provisional"]` |
| 2.6 | Transitional rules under Reg. 883/2004 | official form 2.6 | not rendered; derived from `form["transitional_rules"]`, no source |
| 6.10 | The date the determination was made | official form 6.10 | provisional policy date (Mon/Wed, 61–180 day window) |

**Dependencies.** C-L cannot be implemented before the E block's situation
record exists (§1.1): the 24-month bound applies to 3.1 and 3.3, and 2.5
depends on whether the situation is an Art. 12 or an Art. 13 one. It also
depends on D4 (whether 2.5 is rendered at all) and on the P block's
withdrawal capability (§8), because a certificate that can be withdrawn
needs a recorded basis for the withdrawal.

### C-E — engineering: model the certificate as an issued artifact with a lifecycle, not as a mutable row

The A1 is declaratory and withdrawable. A row that can be updated in place
cannot express "issued, then suspended, then withdrawn, then re-issued", and
cannot answer "what did the certificate say on the day it was relied on?".
The current `A1Case` carries `external_status`, `artifact_reference`,
`prepared_artifact_hash` and `visual_confirmed*` flags — enough to know the
artifact exists, not enough to know its legal state.

**Dependency.** Needs the P block's append-only decision ledger (§8): a
withdrawal is a recorded decision with an actor, a time and a reason, not a
status flip. It also needs an artifact ledger keyed by content hash, so that
a re-issued certificate does not overwrite the bytes a host State may already
have seen.

### Comparison

| | C-L (legal) | C-E (engineering) |
|---|---|---|
| Kind | constraint on values | choice on structure |
| Cost | low — validation rules and one derived field | medium — a new lifecycle state machine and an artifact ledger |
| Risk if skipped | a certificate that asserts a 36-month posting, or a 3.4 case without 2.5 ticked | cannot answer a challenge; cannot re-issue cleanly |
| Reversibility | high | low — a migration |
| Depends on | E-block situation record, D4 | P-block ledger, artifact storage |
| Recommendation | **take** | **take, after P** |

**Recommendation: take both.** C-L is cheap and prevents a wrong document.
C-E is the durable form, but it is a migration and belongs after the P block
exists, because the ledger is the thing that makes the lifecycle meaningful.

## 4. Block W — the person

**Analysis.** The ČSSZ application collects **three** addresses where the A1
has two: section A *"ADRESA BYDLIŠTĚ – NEMUSÍ SE SHODOVAT S ADRESOU TRVALÉHO
POBYYTU"* (the habitual residence — *"adresa obvyklého bydliště ve smyslu
centra životních zájmů (povinný údaj)"*), section B *"Kontaktní adresa (pokud
se liší od adresy bydliště)"*, and section C *"Adresa pobytu"*. The A1 asks
for 1.8 *"Address in the State of residence"* and 1.9 *"Address in the State
of stay"*. The permanent address is a fourth concept that the A1 does not
carry, and that the model also does not carry.

The legal definition is Regulation 883/2004 Article 1(j): residence is *"the
place where a person habitually resides"*, with the elements in Article 11 of
Regulation 987/2009. The employee identity form in this repository is
already a versioned chain: `IdentityEvaluation` → `WorkerIdentityClaim` →
`WorkerIdentityRevision.confirmed_fields`, with the MRZ cross-check that
caught a page swap in real scans, and `b8097e5` reconciling the legacy worker
keys.

### W-L — legal: separate the three addresses, and treat residence as a legal determination

The habitual residence is a *determination* (centre of vital interests), not
a postal lookup. The repository's `config/address_enrichment.json` already
holds the right principle — it enriches district and postal code from an
**exact address match only**, and its stated policy is that the OSSZ is *"a
review suggestion and never silently replaces the configured issuing
institution"*. That principle must be extended to the residence itself: an
enrichment rule may not decide where the person's centre of vital interests
is.

**Dependencies.** Needs D3 (the `stay_*` nullable fields for 1.9) and the O
block's competence rule, because the residence and the employer's registered
office are two of the three ways competence is determined. Needs the P block
for the determination's evidence: Article 3(2) of Regulation 987/2009 places
the duty on the person concerned to provide *"all the information, documents
or supporting evidence necessary to determine their situation"*, and
*C-422/22* paragraphs 35–36 require the issuing institution to carry out *"a
proper assessment of the facts on which the issue of such a certificate is
based"* and to verify the accuracy of the particulars *"throughout the
performance of the activity"*. A residence that was never determined cannot
be evidenced later.

### W-E — engineering: keep the person separate from the identity chain, and make the chain re-examinable

The model already separates `Worker` (the person) from
`WorkerIdentityRevision.confirmed_fields` (the accepted identity). What it
does not yet have is the property the law requires: that a challenged
identity fact can be *re-examined* and that the re-examination is visible.
The `FieldProposal`/`FieldDecision` pair and `A1Case.evidence_notes` (free
text today) are the right shape; the missing piece is typed entries.

The same requirement appears for the *employer* and for the *situation*: a
certificate can be challenged on any of the facts it rests on, and each must
be independently re-examinable. That argues for one mechanism across blocks,
not three.

**Dependencies.** Depends on the P block's typed evidence (§8) and on the
E block's employer identity, because the ARES-backed employer record is
itself an identity fact with the same re-examination property.

### Comparison

| | W-L (legal) | W-E (engineering) |
|---|---|---|
| Kind | constraint on which facts exist and who decides them | choice on mechanism |
| Cost | low–medium — three nullable address groups, one determination record | medium — typed evidence across three blocks |
| Risk if skipped | a residence silently taken from a postal lookup; 1.9 conflated with 1.8 | a challenged fact cannot be re-examined, so a certificate cannot be defended or withdrawn cleanly |
| Reversibility | high | medium |
| Depends on | D3, O-block competence, P-block evidence | P-block ledger, E-block employer identity |
| Recommendation | **take** | **take, after P** |

### W-A — adjudication: who re-decides a contested identity fact, and on what authority

A third perspective, distinct from W-L (which fields exist and who decides
them) and from W-E (which records the decision): a contested identity fact has
to be **re-decided** by somebody, and the form of that re-decision is a
different constraint again. A name is disputed because two records disagree;
the resolution needs a named authority, a defined evidentiary threshold, a
record of which side prevailed, and a rule for what happens to a certificate
already issued against the losing side. None of that is a field on the A1,
and none of it is a data-structure question.

This is the part of the P block's requirement that W-E does not answer: W-E
says the evidence is *typed*, but it does not say who may re-decide. Without
that, "re-examinable" means "re-readable", which is a weaker property than
the law asks for.

**Dependencies.** Needs W-E's typed evidence and the P block's decision
ledger. It also needs the O block, because an identity dispute and an issuing
institution's competence question can arrive together.

**Recommendation: take W-L, then W-A, then W-E.** W-L is the
official-contract change and is cheap. W-A states the adjudication rule, which
is cheap to state and expensive to leave implicit. W-E is the durable
mechanism and is best done once, for all three fact-bearing blocks, rather
than three times.

## 5. Block E — employer, role and situation

**Analysis.** This block carries the most legal structure and the most
missing data. Article 12(1) (posted employee) and 12(2) (posted
self-employed) are both capped at 24 months and are the derogations from
Article 11(1)'s single-legislation rule. Article 13 covers simultaneous
activity in two or more States, with a quantitative test: Article 14(8) says
a share *"of less than 25 % in respect of the criteria mentioned above shall
be an indicator that a substantial part of the activities is not being
pursued in the relevant Member State"*, measured on working time and/or
remuneration for employees, and on turnover, working time, number of services
and/or income for the self-employed. Article 13(2)(b) turns on the *"centre
of interest"* (Art. 14(9)). Article 11(3)(a) is the residual "A1 CZ" case.
Article 16 agreements can derogate from all of it, in the interest of the
worker.

That decision tree is what the official Section 3 encodes, and it is why the
model's `status_profile` — three values, one string — is a *narrowing* of the
law rather than a model of it. The narrowing is defensible for the cases the
agency issues, provided it is declared. The repository already treats the
coarse `Worker.activity_profile` correctly (§1).

On the employer side, ARES is the Czech business register and publishes a
free, key-free REST API: `GET /ekonomicke-subjekty/{ico}` returns the
business name, registered address, legal form, DIČ, CZ-NACE and the state in
each register; `GET /ekonomicke-subjekty-res/{ico}` returns the predominant
CZ-NACE activity and an employee-count category; `POST /ekonomicke-subjekty-notifikace/vyhledat`
returns **change-notification batches**, i.e. which IČOs changed and when;
and `POST /standardizovane-adresy/vyhledat` converts a free-text address into
a RÚIAN-standardised address with a municipality code. The documented
operating limit is 500 queries per minute with no daily cap, and the guidance
is to cache, because register data changes rarely.

**What the ARES claims rest on.** The repository records exactly one ARES
artefact — the employer record under `a1/` and the single point-lookup URL in
`a1/employees_normalized.json`. Everything else in this section — the
`/ekonomicke-subjekty-res/{ico}` view, the change-notification endpoint, the
RÚIAN address standardisation, the 500-queries-per-minute limit, and the
"free and key-free" characterisation — is **external research** from the ARES
Swagger UI and technical catalogue, cited in §11, and is not evidenced by the
repository. The E-E/E-X trade-off leans on the notification channel, so that
part of the argument is external; the offline-import path in D11a is not.

**What the ARES authorisation is actually for.** An earlier draft of this
document had a single gate, "permit an outbound ARES lookup from the
server?". That was over-scoped, and it conflated three unrelated things.
Separating them is the useful result:

| | What crosses a boundary | What is decided | Gate |
|---|---|---|---|
| **ARES is not a model provider** | nothing | — | AGENTS.md's provider rules are about LLM providers, key handling, billing and data egress to model endpoints. ARES is a **public register of the Ministry of Finance**: free, no key, no registration, no billing, no quota to buy. It is inside the "verified-free endpoints" envelope by inspection, and it is not a model call, so the OpenRouter `:free` rule and the paid-fallback rules do not apply | none |
| **D11a — offline import** | nothing at runtime; a human runs the lookup on their own machine and reviews the result before it becomes a record | whether the *agency* accepts the register data as a source of employer facts, and how a sole trader's record is handled as personal data | Jan; **default YES** |
| **D11b — runtime server egress** | the request itself (an IČO, which is already a business fact the agency holds); **no worker PII crosses the boundary** | whether the *service* may make outbound HTTPS calls to a third-party host. AGENTS.md puts "networking" and host services with the sysadmin, and this repository's rule is that the durable workspace is the only thing the application owns | sysadmin; **default NO** |

So the honest answer to "what is the ARES authorisation for?" is: **it is not
about ARES at all.** It is about whether the *server* is allowed to make
outbound network calls. The register data itself is free, public,
key-free and inside the verified-free envelope. What needs deciding is a
host question — and it only becomes relevant if the agency wants a *live*
lookup at data-entry time rather than a reviewed import.

Two consequences worth stating plainly:

1. **A reviewed offline import needs no new authorisation.** It is the same
   mechanism the institution profiles already use: a human retrieves the
   record, reviews it, and commits the result with its source and hash. The
   repository's ARES-derived employer record under `a1/` is exactly that, and
   the E-E master can be seeded the same way.
2. **D11b is not a blocker for the master data work.** If the answer is no,
   E-E still works with an operator import; only the *automatic refresh* is
   lost, and the change-notification channel — which is the part that
   actually needs the network — is the part that would be deferred. The
   master would then carry a "verified on" date that a human set, which is
   precisely what the institution profiles already do.

### E-L — legal: make the situation a first-class record with a closed decision tree

Do not model the status as one string. Model the **situation** — the legal
basis, the dates, the conditions — and *derive* the Section 3 box from it.
That makes the 24-month cap, the prior-activity condition, the
"similar activity" test and the replacement-worker flag enforceable, and it
makes 3.3 a consequence rather than a special case.

The decision tree to encode, in the order the law applies it:

1. Is the activity performed in only the State referred to in 2.1? → Art. 11(3)(a) → **3.12**
2. Is it a posting of an employee (Art. 12(1)), i.e. the employer normally
   carries out activities in the first State and the person is posted? → **3.1**,
   subject to ≤24 months, not replacing another person, and the prior
   one-month condition
3. Is it a posting of a self-employed person (Art. 12(2))? → **3.3**, subject
   to ≤24 months, a similar activity, and prior activity of at least two
   months
4. Is it simultaneous activity in two or more States as an employee? → Art.
   13(1) → **3.2**, decided by the 25 % substantial-part test
5. As a self-employed? → Art. 13(2) → **3.4**, decided by the 25 % test and
   the centre of interest
6. Employee in one State, self-employed in another? → Art. 13(3) → **3.8**
7. Civil servant plus other activity? → Art. 13(4) → **3.9**
8. Seafarer / flight and cabin crew / contract staff / exception → Art. 11(4),
   11(5), 15, 16(1) → **3.7 / 3.10 / 3.6 / 3.11**
9. None of the above and the situation is not stated → **no box**, undecided
   worksheet, no certificate

**Dependency.** Needs the C block's 2.2/2.3 bound (the 24-month cap is a
certificate field), the A block's territory and NACE facts, and the W
block's residence (Art. 13(1)(a) turns on the State of residence).

### E-E — engineering: employer as a legal entity in a master table, refreshed from ARES

The employer is a legal entity, not a set of strings. `LegalEntity` with
`registration_id`, `legal_name`, `legal_form`, `country_code`,
`registered_address`, `source`, `verified_on`, `content_sha256`, and the
`Employment` fact binding a worker to an entity with a role and a period. A
sole trader is the same entity with `legal_form = sole_trader` and the
person's own registration id — which turns the current renderer-internal
derivation (`a1_core.py:321-334`, the self-employed employer block derived
from the person's own name) into a recorded, reviewable row.

For the refresh path, ARES offers two distinct mechanisms and the difference
matters: the **point lookup** tells you what an entity *is* now, and the
**notification endpoint** tells you *when a registry record changed*. A master
built only on point lookups has no defensible "as of" date for a correction
that reaches an already-issued certificate. The notification batches give
exactly that.

**Dependencies.** Needs a `LegalEntity` table and an import path (the master
data landing sequence in the
[architecture solution](solutions/a1-topic-data-architecture-solution.md) §4).
Needs the W block's identity mechanism, because a legal entity is an identity
fact with the same re-examination property. Needs a rate-limit and cache
policy for ARES, and an operator decision on whether the agency may query a
public register from the server (it is free and key-free, but it is an
outbound call to a third party, and AGENTS.md requires an authorisation
decision for provider use).

### E-X — alternative: keep the employer in the assignment, add only a registry snapshot

The opposite structure: keep `Assignment.a1_facts_json` as the employer
store, and add only a *cached* ARES snapshot (name, address, legal form,
CZ-NACE, retrieved-at, response hash) attached to the employment fact. No
`LegalEntity` table, no cross-worker reuse.

**Dependencies.** Needs the same ARES authorisation and caching, plus a
per-assignment snapshot storage, plus the decision that cross-employer
questions ("which clients work for employer X") are answered by scanning
JSON rather than by a query.

### Comparison

| | E-L (legal) | E-E (engineering) | E-X (alternative) |
|---|---|---|---|
| Kind | constraint on the model | structure choice | structure choice |
| Cost | medium — a situation record with six fields, a decision function, three new gates | medium–high — a master table, an import path, a change-notification job | low–medium — a snapshot column and a cache |
| Risk if skipped | a 3.3 or 3.1 case that cannot be shown to satisfy Art. 12 | employer facts duplicated per worker and unqueryable; a correction cannot be traced to a registry event | same duplication risk, but smaller blast radius; no reusable identity |
| Reversibility | high — additive fields | low — a migration | high — a column |
| Blast radius of a bad correction | — | **every worker of that employer** | one worker |
| Depends on | C-block bound, A-block facts, W-block residence | O-block, P-block, ARES authorisation | ARES authorisation |
| Recommendation | **take** | **take** | fallback if the ARES authorisation is declined |

**Recommendation: take E-L and E-E; keep E-X as the documented fallback.**
E-L is not optional — without it the model cannot show that a 3.1 or 3.3
certificate satisfies Art. 12, which is the whole point of the certificate.
E-E and E-X differ mainly in blast radius, which is a real trade-off worth
stating: a shared legal entity is more useful and more dangerous, and the
existing per-case `A1Case.source_snapshot_json` pinning is what keeps the
danger bounded.

## 6. Block A — activity and territory

**Analysis.** The official form's Section 5 is frequently misread. It is
not an address block. 5.1 asks for *"Name(s) or business name(s) and code(s)
of the firm(s) or ship(s) or the home base(s) where you will be employed"* —
the **host-side** entity and its code. 5.2 asks for *"Address(es) or name(s)
of ship(s) or the home base(s) where you will be (self) employed in the
'host' State(s)"* — for the self-employed multi-state case this is a
**territory list**, not a street address, which is why the repository's
layout gives `activity.address` a wide two-line field. 5.3 is *"Or no fixed
address in State(s) of (self)employment"*, and it is the exclusive
alternative to 5.2.

The ČSSZ application supplies the missing third piece: section D asks
*"Žadatel po dobu uvedenou v žádosti vykonává výdělečnou činnost na území
těchto států (nutno uvést i ČR, pokud odpovídá skutečnosti)"* — the
**territory** the activity is performed in, and the form insists the Czech
Republic be included if it is true. Section R asks for the **CZ-NACE**
classification with exactly one main activity, and it is mandatory where
activity is performed in Member States.

### A-L — legal: three distinct fields, with the territory and the host entity separated

5.1 (host entity + code), 5.2 (territory list) and 5.3 (no fixed address) are
three different facts, and today the repository has 5.1 and 5.2 but no
source for 5.3.

**The territory is a list of States, in ISO 3166-1 alpha-2 codes, from a
closed domain.** The official form's own footnote fixes the domain: *"A
'State' or a 'Member State' is any European Union country, plus Iceland,
Liechtenstein, Norway and Switzerland."* The Czech application adds the
United Kingdom, because the Withdrawal Agreement keeps a bilateral form in
force for cases involving it. So the list is at most EU-27 + IS + LI + NO +
CH, plus GB for a bilateral case — roughly thirty-two values, not free
text. The form's other country fields (1.8.4, 1.9.4, 4.4.2, 6.5) are
labelled *"Country code"*, and the repository already uses that convention
(`"country_code": "CZ"` in the institution profiles, `kodStatu` in the ARES
records). The two-letter form is therefore the correct representation, and
the codes are unambiguous: **DE is Germany (Deutschland), CZ is Czechia
(whose previous ISO name was "Czech Republic"), and Denmark is DK.** The
repository contains no reference to Denmark or DK anywhere, and its own
posting scenario settles what the two codes mean: `cz_employee_to_de` sets
`certificate.member_state = "CZ"` (field 2.1), `employment.country_code =
"CZ"` (field 4.4.2) and `activity.address = "DE"` (field 5.2) — a Czech
worker posted to **Germany**, with the Czech State included in the
territory list. The scenario also adds `activity.workplace_address` to the
missing fields when the address is a bare `"DE"`, which is the correct
treatment: a territory code is not a workplace address.

**Correction.** An earlier draft of this document claimed that the `DE, CZ`
provisional default "omits the home State". That was wrong: `DE, CZ` is
Germany **and** Czechia, so the home State *is* in the list. The real
deficiencies are different, and smaller:

1. it is a **labelled policy proposal**, not a reviewed value, and it lives
   as a comma-joined **string** rather than a typed list, so nothing in the
   record distinguishes it from a reviewed territory;
2. whether Czechia belongs in the list at all depends on whether the person
   also performs activity there — which is the operator's fact, not a policy
   default. The `cz_employee_to_de` scenario correctly uses `"DE"` alone
   because it is an explicit operator selection, and that is the shape a
   reviewed value should have;
3. nothing validates the codes against the closed State domain, so a typo
   would render as an unknown territory.

**Dependencies.** Needs D7 (whether the `DE, CZ` default stays) and D9
(whether 5.3 is ever reachable). Needs the E block's situation record for
which territory list is correct. Needs the A1's 5.1 to be sourced from the
**host-side** employer, which is a different entity from the Section 4
employer — and which the model does not have.

### A-E — engineering: a country master and a typed territory list, with the default kept distinct

Represent the territory as a list of ISO 3166-1 alpha-2 codes against a
`Country` master, and keep the provisional default in a *separate* field
from a reviewed value, so that a reader of the record — and of the rendered
PDF — can tell which one it is. The repository already has the vocabulary
problem solved elsewhere: ARES returns CZ-NACE codes and RÚIAN municipality
codes, and the `config/institutions/*.json` profiles carry a `country_code`
per issuing State.

**Dependencies.** Needs a `Country` master, or an explicit ISO-3166-1
validation rule if no table is wanted. Needs the C block's 2.5 (a provisional
determination under Art. 16(2) is exactly the case where the territory is
provisional). Needs the P block, because a policy default that reaches a
binding document must be distinguishable in the record.

### Comparison

| | A-L (legal) | A-E (engineering) |
|---|---|---|
| Kind | constraint on what each field means | choice on representation |
| Cost | medium — separate host entity, territory and 5.3 sources | low–medium — a country master, a typed list |
| Risk if skipped | 5.1 prints the Section 4 employer; 5.3 is unreachable | a policy default and a reviewed value are indistinguishable in the record; a mistyped code renders as an unknown territory |
| Reversibility | high | high |
| Depends on | D7, D9, E-block situation | C-block 2.5, P-block |
| Recommendation | **take** | **take** |

### A-V — vocabulary: one country list for the whole form, not per-field text

A third perspective, genuinely different from both A-L (which separates three
facts) and A-E (which types the territory list): the form uses country
references in **six** places — 2.1 (Member State), 1.8.4 and 1.9.4
(Country code), 4.4.2 (Country code), 6.5 (Country code) and the 5.2
territory list — and today each is free text validated nowhere. A single
reference list, checked against ISO 3166-1 alpha-2 and against the A1's own
definition of a "State", would make all six consistent by construction and
would make a mistyped territory impossible rather than merely detectable.

**Dependencies.** Needs the country master of A-E, and the State-domain
definition from A-L. It is a *validation* concern rather than a *storage*
concern, which is why it is neither of the other two.

**Recommendation: take A-L, A-E and A-V.** A-L is a correctness fix with a
visible consequence — the `DE, CZ` default should list the home State first,
because the ČSSZ form requires the home State to be listed when it is true.
A-E makes the default distinguishable from a reviewed value, and A-V makes the
whole vocabulary consistent. The three are cheap and do not compete.

## 7. Block O — the institution

**Analysis.** Competence is a three-way rule. Article 19(2) of Regulation
987/2009 requires the competent institution to provide the attestation; the
competent institution is, under the implementing rules, the one where the
employer's registered office or place of business is, the one where the
person resides, or — where it cannot be determined — any institution of the
competent State. ČSSZ states the fallback in the same terms: *"V případě,
kdy nelze místní příslušnost určit, lze žádost podat na jakékoli správě
sociálního zabezpečení"*.

Two facts must not be conflated: the **office contact** (6.7 fax, 6.8 phone,
6.9 e-mail) and the **certificate signatory** (6.11). Every current
institution profile carries `CONTACT_NOT_CONFIRMED_SIGNATORY` for exactly
this reason, and the repository's own rule is that a signatory is never
copied from a template or an example.

### O-L — legal: encode competence as a selection rule with a fallback, and keep the signatory separate

Make the institution a *decision*, not a default. The three competence
grounds (employer's establishment, person's residence, or any institution)
should be computable from data the model already holds, and the fallback
should be explicit. The signatory and the office contact are two fields
with different owners and different lifecycles, and the model should never be
able to fill one from the other.

**Dependencies.** Needs the E block's employer country and the W block's
residence, since competence follows from both. Needs D6 (the 6.7–6.9
coordinates) and the P block, because a signatory is a person whose identity
and authority must be evidenced like any other identity fact.

### O-E — engineering: institution as versioned master data, projected from the reviewed profiles

The institution profiles are already the right artefact: `source_url`,
`verified_on` and a runtime sha256 on each. The gap is that they are files
selected by path convention rather than records, so there is no query for
"every case handled by OSSZ Teplice" and no version to pin a case to. A
master table **seeded from** the reviewed files, with the files retained as
the evidence of record, gives both. ARES provides the model for the refresh
mechanism: a point lookup for the current value, and a change-notification
channel for knowing when a record changed — for a public body that is
periodically re-verified rather than a registry, the equivalent is the
reviewer re-confirming the profile and the file's hash changing.

**Dependencies.** Needs the master-data landing sequence from the
[architecture solution](solutions/a1-topic-data-architecture-solution.md) §4,
and it must land *after* the reviewed files are confirmed, so that the
projection never becomes a second, divergent source.

### Comparison

| | O-L (legal) | O-E (engineering) |
|---|---|---|
| Kind | constraint on which institution may issue | choice on how the institution record is trusted |
| Cost | low — a selection rule over data already held | medium — a master table, a seeding step, a re-verification flow |
| Risk if skipped | a certificate issued by an institution without competence; a signatory taken from the contact | no "as of" date for a re-verified profile; a profile change cannot be traced to a case |
| Reversibility | high | medium |
| Depends on | E-block employer, W-block residence, D6, P-block | the master-data landing sequence |
| Recommendation | **take** | **take** |

**Recommendation: take both.** O-L is cheap and prevents a real
misapplication. O-E is the durable form and must follow the reviewed files,
not precede them.

## 8. Block P — provenance

**Analysis.** This block owns no form field and carries the whole weight of
the document. Three legal requirements converge on it:

1. **Re-examination.** *C-422/22* paragraphs 35–36: the issuing institution
   *"must carry out a proper assessment of the facts on which the issue of
   such a certificate is based"* and, because the binding force of an A1
   rests on sincere cooperation and mutual trust, *"must verify throughout the
   performance of the activity … the accuracy of the particulars contained
   therein and to withdraw it if … it finds that that certificate does not
   comply with the provisions of Title II"*.
2. **Informability.** *C-422/22* paragraphs 54–55: after a withdrawal the
   issuing institution must *"inform, as soon as possible, both those
   institutions and the person concerned of that withdrawal and to communicate
   to them all the information and data necessary for the establishment and
   determination of that person's rights"*. That is a communication duty, and
   a communication needs a retained record of what was communicated.
3. **Suspensibility.** *C-410/21*: an A1 whose binding effects are
   *provisionally suspended* pending review is a recognised state, and a
   court may disregard it in criminal proceedings where fraud is found and a
   reasonable period has elapsed.

The repository has the right primitives — `FieldProposal`, `FieldDecision`,
`A1Case.evidence_notes`, `source_snapshot_json`, `artifact_reference` — but
`evidence_notes` is a JSON list without a schema, and the review flags
(`identity_reviewed`, `certificate_reviewed`, `approved_for_pdf`,
`validated_by_user`) are flat strings with no actor, time or scope.

### P-L — legal: make the record re-examinable, informable and withdrawable

The evidence chain must answer, for any single field of a certificate: who
confirmed it, when, from which source, on which revision, and on what basis.
That is what allows a re-examination under *C-422/22* to conclude "the fact
was correct" or "the fact was wrong and the certificate is withdrawn", and
what allows the information to be communicated to the other institution.

**Dependencies.** Needs W-E, E-E and O-E to produce the typed facts it
records. Needs the C block's lifecycle to record the withdrawal.

### P-E — engineering: an append-only decision ledger, with the legacy flags demoted to projections

The flat flags are the weak point. They are read as authority but carry no
attribution, and the 44-column mapping already treats them as *"historical
claims"* rather than evidence. The fix is to make the ledger authoritative
and the flags **derived** from it — so a flag can only be YES if a decision
exists, and the decision says who, when and why.

**Dependencies.** Needs the P block's own consumers to move off the flat
flags — the two `validate_review` gates, the `A1Case` import path, the
`generate_provisional_a1` promotion path, and the two paths that set a flag
to YES **without any actor**: `finalize_a1.auto_approve_stale_identity_reviews()`
marks a row `identity_reviewed = YES` after 24 h with only an
`AUTO_APPROVED <timestamp>` comment, and the row-seeding path sets
`identity_reviewed`, `certificate_reviewed`, `approved_for_pdf` and
`validated_by_user` wholesale. Those two are the strongest instance of the
problem the ledger exists to close, so they belong in the migration list. Needs a migration of the existing
flags into typed decisions, or an explicit decision to grandfather them as
legacy claims.

### Comparison

| | P-L (legal) | P-E (engineering) |
|---|---|---|
| Kind | constraint on what the record must be able to do | choice on mechanism |
| Cost | low as a statement, high as an implementation | high — a ledger plus a migration of every gate |
| Risk if skipped | a certificate cannot be defended, withdrawn or re-issued | same, in practice |
| Reversibility | — | low |
| Depends on | W-E, E-E, O-E | P-L, and the gate migration |
| Recommendation | **take** | **take, last** |

### P-O — operational: what an auditor or the host institution must be able to retrieve, and for how long

A third perspective, and the one that exposes a dimension neither P-L nor P-E
touches. P-L asks whether the record can be re-examined; P-E asks what shape
it has. Neither asks the question an *external* party actually asks: given a
certificate that was relied upon in another Member State three years ago,
what can that institution obtain, in what form, and under what retention
obligation? That is a *retention and disclosure* constraint, and it can
demand things the structure does not: a preserved copy of the exact bytes
that were relied upon, a record of who was told what and when, and a rule for
the period after which the agency's own retention expires while the
obligation to answer a question does not.

It also explains why the withdrawal cases matter: *C-422/22* requires the
issuing institution to inform the other institutions and the person, and
*C-410/21* contemplates an A1 whose binding effects are suspended. Both
assume a record that outlives the transaction that produced it.

**Dependencies.** Needs P-E's ledger and the C block's artifact storage. It
also constrains the retention policy that the other blocks' snapshots assume.

**Recommendation: take P-L as the requirement, P-O alongside it, and P-E as
the last engineering step.** P-L states what the record must be able to do and
P-O states for whom; P-E is the mechanism. Doing P-E first would encode
today's flat flags as authority, which is the opposite of the requirement.

## 9. Cross-block comparison and the ordering

There is **no single total order**, and an earlier draft of this document
claimed one. The honest shape is two chains with explicit cross-chain edges.

**The legal chain** changes *what is true*. It needs no migration, is
reversible, and can start immediately.

| Order | Item | Depends on |
|---|---|---|
| L1 | **E-L** situation record and decision tree | — |
| L2 | **A-L** 5.1/5.2/5.3 separation, typed territory | E-L (which territory is correct) |
| L3 | **O-L** competence selection rule, signatory separation | E-L (the employer's country) and A-L (the territory) |
| L4 | **W-L** three addresses, residence as a determination | O-L (competence reads the residence) and A-L (the territory) |
| L5 | **C-L** 24-month bound, 2.5 derived from the situation | E-L (whether the situation is an Art. 12 or an Art. 13 one) |

L3 precedes L4 on purpose: the competence *rule* can be implemented while the
residence fact is still empty — it reads a field that may be blank. That is
what breaks the W↔O cycle an earlier draft had.

**The engineering chain** changes *where it is true*. It needs migrations and
follows the legal chain.

| Order | Item | Depends on |
|---|---|---|
| E1 | **P-L** the re-examination, information and suspension requirements | — (a requirement statement, so it comes first) |
| E2 | **O-E** institution master, projected from the reviewed profiles | the reviewed files being confirmed |
| E3 | **E-E** `LegalEntity` master, seeded from ARES | E2 (the master-data landing) and D11a |
| E4 | **A-E** country master and typed territory | L5 (for 2.5) and E1 (provenance) |
| E5 | **W-E** typed identity evidence | E1 |
| E6 | **P-E** append-only ledger, flags demoted to projections | E1, and the migration of every gate that reads the flags |

**Cross-chain edges:** A-E (E4) also needs L5, because 2.5 is what makes a
territory provisional; P-E (E6) needs E2, because an institution is itself an
identity fact with the same re-examination property.

**What this ordering buys.** The legal chain needs no migration and is
reversible, so it can start before any decision about the data model. The
engineering chain is one migration per step, and each step is independently
acceptable.

**The one thing that can be decided now and needs no data:** the default for
an unstated status stays **"undecided"**, and no status is ever inferred from
the coarse worker profile. That is now the behaviour, enforced by
`tests/test_a1_status_default.py`; it needed a code change to become so, and
the change is recorded in the delivery record.

## 10. What this changes in the decision gates

| Gate | Current | Proposed | Why |
|---|---|---|---|
| D1 | "Agency issues posted-self-employed A1s (3.3)? NO, Jan" | **Split into D1a and D1b**, default NO for the checkbox; add **D10** for the situation-fact record | §1.1 — Art. 12 requires facts the model has no home for; a bare enum value is not enough |
| D2 | Page-level provisional marker: NO | unchanged, still Jan | the marker is a client-communication choice, not a legal one |
| D3 | Add `stay_*` nullable fields: NO | **YES** | W-L requires 1.9 to be a distinct fact; the field is additive and safe |
| D4 | Render 2.5: NO | **YES, but derived** — ticked exactly when the situation is an Art. 13 one | Art. 16(2) makes the initial determination provisional for Art. 13; 2.5 is not a free choice |
| D5 | 2.6 stays FALSE | unchanged | no source exists; the gate correctly records that |
| D6 | Render 6.7–6.9: NO | **YES** | O-L: the contact block is institution data the profile already holds, and 6.11 is a different fact |
| D7 | `DE, CZ` default stays? | **YES, but as a typed list of ISO 3166-1 alpha-2 codes, validated against the State domain** | the default already includes the home State; what it lacks is typing, validation and separation from a reviewed value |
| D8 | Self-employed employer derivation: YES | **replaced by E-E** — a `sole_trader` `LegalEntity` row | the current derivation is renderer-internal and therefore not reproducible |
| D9 | 5.3 branch: NO | unchanged for now; A-L requires a source before it can ever be ticked | a fact, not a default |
| **D10** | — | **new** — carry the situation record (`legal_basis`, `posting_start`, `posting_end`, `prior_activity_start`, `replaces_worker`, `nace_code`)? | §1.1, E-L |
| **D11a** | — | **new** — permit an **operator-initiated offline** ARES import (a human runs the lookup and reviews the record)? **YES** | it needs no host egress and no provider decision; it needs the same data-protection care as any employer fact |
| **D11b** | — | **new** — permit **runtime server-side egress** to `ares.gov.cz`? **NO** | it is a host/network decision, which AGENTS.md places with the sysadmin |
| **D12** | — | **new** — model the certificate as a lifecycle with withdrawal and suspension states? | C-E and P-L; the states exist in the case law |

## 11. Sources

**Law and official authority**

- Regulation (EC) No 883/2004, Art. 1(j) (residence), Art. 11 (single
  legislation), Art. 12 (special rules, 24-month cap), Art. 13 (activities in
  two or more Member States, 25 % test, centre of interest), Art. 16
  (agreements) — EUR-Lex 32004R0883.
- Regulation (EC) No 987/2009, Art. 3(2) (duty to provide information),
  Art. 5 (legal value of documents, withdrawal), Art. 14 (Art. 12/13 details,
  25 % indicator, prior activity, similar activity), Art. 16 (Art. 13
  procedure, provisional determination, two months), Art. 19 (A1 attestation)
  — EUR-Lex 32009R0987.
- Commission Decision A2 of 12 June 2009 (interpretation of Art. 12).
- Commission, *Practical guide on the applicable legislation in the European
  Union, the European Economic Area and in Switzerland* — posting conditions,
  "similar activity", 24 months and Art. 16 agreements, the two-month gap
  between postings, the 25 % substantial-part test.
- DG EMPL, *A1 Certificate concerning the Social Security legislation which
  applies to the holder* — the official field structure and numbering, the
  holder information, and the note that 1.4 is given by the holder when the
  institution does not know it.
- ČSSZ, *Podání žádosti o určení příslušnosti* and the three application
  forms (zaměstnanec / zaměstnanec současně OSVČ / OSVČ) with their
  *Pokyny k vyplnění* — the mandatory facts, the situation choice, the three
  address blocks, section D (territory), section R (CZ-NACE), section F
  (status), and the posting conditions.
- CLEISS, the 2018-08-03 addition of status 3.12 and the E101/E103/E102
  supersession.

**Case law**

- *Alpenrind*, C-527/16, 6 September 2018 — the A1 binds the institutions and
  the courts of the State of work; "sent to replace another person" under
  Art. 12(1).
- *DRV Intertrans*, C-410/21, 2 March 2023 — provisional suspension of an
  A1's binding effects; criminal disregard for fraud.
- *ZUS*, C-422/22, 16 November 2023 — own-motion withdrawal without prior
  dialogue, the duty to inform, and the A1 as a declaratory act.
- *Bouman*, 62015CJ0356 — the presumption created by an A1.

**Pending EU reform (read as press coverage, not primary text)**

- The European Commission's package on fair worker mobility, presented
  **15 September 2026**: five legislative proposals, including a **European
  Social Security Passport (ESSPASS)** for digital social-security documents
  with the **A1 as the first document affected**, and an express aim of
  "limiting the use of falsified documents" and making A1s easier to verify.
  This was read through trade-press reporting, so the Commission's own
  communication and the proposal texts are the authority and should be
  consulted before the roadmap depends on any of it.
- The A1 reform provisionally agreed in **April 2026** — Council adoption
  and publication in the Official Journal still pending — which would exempt
  short business trips and add a three-day exemption for other short-term
  assignments abroad.

**Registry and data sources**

- ARES (Ministry of Finance, Czech business register) REST API —
  `https://ares.gov.cz/ekonomicke-subjekty-v-be/rest`, Swagger UI and the
  technical catalogue. Point lookup by IČO, search, per-register views, the
  **change-notification** endpoint, RÚIAN address standardisation, the
  500-queries-per-minute limit and the guidance to cache.
- The repository's own history for the decisions this document touches:
  `ebd6b88` (Section 5 policy and the two PDF frameworks), `09d28dd`
  (unverified draft publication through the shared core), `5469501` (variant
  system and default review flags), `a3a9a24` (placeholder framework),
  `1fb8da1` (draft numbers across generation revisions), `bbbbf4c` (visual
  confirmation bound to exact generation evidence), `b8097e5` (legacy worker
  key reconciliation).

**Repository artefacts**

- `docs/architecture/a1-field-source-mapping.md` — the per-field contract,
  the topic partition, the 23-site 3.3 activation path, gates D1a, D1b and D2–D12.
- `docs/architecture/a1-gap-analysis.md` — G1–G15 with severity and owner.
- `docs/architecture/solutions/a1-topic-data-architecture-solution.md` — the
  master-data landing sequence.
- `docs/architecture/a1-automation-scenarios.md` — the per-topic scenarios.
