# A1 field → source mapping: one hood per topic

Status: proposed design, 2026-10-20. This document does not implement a
schema, migrate records, accept evidence or activate real data. It refines
[DB-MIG-1 through DB-MIG-7](../../plans/PLAN-WORKERS-MIGRATE-TO-DB.md) under
[ADR-002](../decisions/ADR-002-release-1a-data-and-transactions.md) and
complements (it does not replace) the
[44-column CSV mapping](release-1a-field-mapping.md).

**Reading model.** Every data point that reaches an A1 form belongs to exactly
one *topic*. This document has one section per topic. Within a topic, every
official A1 field position, its owning source, its rule, its default and its
write action are stated together, and nothing belonging to another topic
appears. The form is then a projection: read a topic's owner, project the
fields.

- [§1 Official authority basis](#1-official-authority-basis)
- [§2 The six topics](#2-the-six-topics)
- [§3 Topic C — The certificate](#3-topic-c--the-certificate)
- [§4 Topic W — Person identity](#4-topic-w--person-identity)
- [§5 Topic E — Employer / legal entity](#5-topic-e--employer--legal-entity)
- [§6 Topic A — Activity and territory](#6-topic-a--activity-and-territory)
- [§7 Topic O — Issuing institution](#7-topic-o--issuing-institution)
- [§8 Topic P — Provenance, review and authority](#8-topic-p--provenance-review-and-authority)
- [§9 The employer-as-organization decision](#9-the-employer-as-organization-decision)
- [§10 Local override for provisional forms](#10-local-override-for-provisional-forms)
- [§11 Gaps](#11-gaps)
- [§12 Verification](#12-verification)

## 1. Official authority basis

### 1.1 What the A1 certificate is

The A1 form ("PD A1", portable document A1) succeeded E101/E103. It is issued
under Regulation (EC) No 883/2004, Articles 11–16, and Regulation (EC) No
987/2009, Article 19. The structure is the DG EMPL interactive form ("A1
Certificate concerning the Social Security legislation which applies to the
holder"), the harmonised document every Member State's institution
completes.

The consequence that governs everything below: **the A1 certificate is issued
by the institution, not filled in by the applicant.** The applicant submits a
*national application* (in the Czech Republic the ČSSZ "Žádost o určení
použitelných právních předpisů", in three variants: employee, self-employed,
employee who is simultaneously self-employed). The institution then issues the
A1. Mandatory-ness therefore belongs to the *application* and to the
*situation*, not to the A1 certificate as a fixed form.

### 1.2 Situations and the legal basis they select

| Situation | Legal basis | Official status |
|---|---|---|
| Posting of an employee | Art. 12(1) Reg. 883/2004 | 3.1 posted employed |
| Posting of a self-employed person | Art. 12(2) | 3.3 posted self-employed |
| Simultaneous pursuit of activities in 2+ Member States, employed | Art. 13(1) | 3.2 employed in 2+ States |
| Simultaneous pursuit of activities in 2+ Member States, self-employed | Art. 13(2) | 3.4 self-employed in 2+ States |
| Usually employee in one State, self-employed in others | Art. 13(3) | 3.8 |
| Civil servant in one State, employed/self-employed in others | Art. 13(4) | 3.9 |
| Contract staff of the European Communities | Art. 15 | 3.6 |
| Mariner | Art. 11(4) | 3.7 |
| Flight or cabin crew member | Art. 11(4) | 3.10 |
| Exception under Art. 16(1) | Art. 16(1) | 3.11 |
| Employed/self-employed **only** in the State referred to under 2.1 (the "A1 CZ" case) | Art. 11(1) and 11(3)(a) | 3.12 |

Art. 11(1) is the general rule: one and only one Member State's legislation
applies at any time. Art. 12–16 are derogations and are construed strictly.
An A1 certificate binds the institution of the State of stay for as long as it
is not withdrawn or declared invalid (*Alpenrind*, C-527/16; *Bouman*,
62015CJ0356), so the data on it must be defensible.

### 1.3 Mandatory fields as stated by the Czech authority

From the ČSSZ "Pokyny k vyplnění" for the employee application:

> "Příjmení, Jméno, Státní příslušnost a Datum narození jsou povinné údaje.
> Nemáte-li rodné číslo, uveďte evidenční číslo pojištěnce přidělené ČSSZ.
> Adresa bydliště je adresa obvyklého bydliště ve smysle centra životních
> zájmů (povinný údaj), nemusí být shodná s adresou trvalého bydliště."

**Surname, forename, nationality and date of birth are mandatory** (or, without
a birth number, the ČSSZ evidence insurance number); the residence address is
mandatory and means the habitual residence (centre of vital interests), not
necessarily the permanent address. In the activity sections "Status žadatele je
povinný údaj" — the applicant's status is mandatory. Sections H and M (ratios
of activity) are "povinný pouze v situaci souběžného výkonu činnosti … a dále
v žádosti typu výjimka" — mandatory only for simultaneous pursuit and
exception requests. Section I/J are "vyplňte pouze v případě…" — fill only when
applicable. The employee/self-employed joint application adds: "Údaj o
nahrazování jiného vyslaného pracovníka je povinný v situaci vyslání" and
"Klasifikace ekonomických činností dle CZ-NACE — … povinně označte jeden
(hlavní) obor činnosti".

### 1.4 Field-level rules read off the official form

| Rule | Statement |
|---|---|
| **R1** | Section 3 is a **mutually exclusive set of exactly one** status out of 3.1–3.12. |
| **R2** | Section 4.1.1 (Employee) and 4.1.2 (Self-employed activity) are **exactly one of**. |
| **R3** | 2.2/2.3 give a bounded period; 2.4 is the alternative "applies for the duration of the activity". |
| **R4** | Section 5 applies **only when an activity is pursued in the host State(s)**. |
| **R5** | 5.2 (host-state address) and 5.3 (no fixed address) are **alternatives**. |
| **R6** | 1.8 is the address in the State of residence; 1.9 is the address in the State of stay. |
| **R7** | 2.6 is ticked only when transitional rules under Reg. 883/2004 apply. |
| **R8** | 1.4 (surname at birth) carries "(***) Information given to the institution by the holder when this is not known by the institution." |
| **R9** | 2.5 (the determination is provisional) is ticked when the determination is not final. |
| **R10** | Section 6 is completed by the institution and includes fax, phone and e-mail. |

### 1.5 Sources consulted

DG EMPL "A1 Certificate concerning the Social Security legislation which
applies to the holder" (field structure and numbering); ČSSZ "A1 form" and
"Miscellaneous situations" (issuing competence, situations, legal bases);
ČSSZ "Pokyny k vyplnění" for the employee and OSVČ applications (mandatory and
conditional statements); CLEISS (the 2018-08-03 addition of 3.12 and the
E101/E103/E102 supersession); EUR-Lex 62015CJ0356 and C-527/16 (binding force
of the certificate; strict construction of the Art. 12–13 derogations).

## 2. The six topics

| Topic | Hood | Owns | Official fields |
|---|---|---|---|
| **C** | Certificate | the issued document: run identity, header number, validity period, issue date | header number, 2.2, 2.3, 2.4, 2.5, 6.10 |
| **W** | Person | the natural person: identity and habitual residence | 1.1–1.9.4 |
| **E** | Employer / legal entity | the counterparty: who employs or engages the person, in what role, in what situation | 3.1–3.4, 4.1.1, 4.1.2, 4.2, 4.3, 4.4.1–4.4.4 |
| **A** | Activity | what is done, and where, in the host State | 5.1, 5.2, 5.3 |
| **O** | Institution | the issuing body | 6.1–6.9, 6.11, and 2.1, 2.6 |
| **P** | Provenance | whether a value is real, who confirmed it, from which source | every field's "is this real" answer |

Two rules hold across all six:

1. **One owner per fact.** A value is stored once, in its topic's owner, and
   projected into the form. No value is stored twice, so no value can disagree
   with itself.
2. **Derived fields are never stored.** Ten of the 38 rendered positions are
   computed: the two gender boxes at 1.1, the four Section 3 status boxes, the
   two Section 4.1 kind boxes, 2.4 and 5.3. Storing them would create a
   contradiction class the official form does not have.

### 2.1 Where each topic lives today

| Topic | Today | Target |
|---|---|---|
| W | `Worker` + `WorkerIdentityRevision.confirmed_fields` | keep |
| E | `Assignment.a1_facts_json` (migration 0015) — structured JSON in a versioned assignment | `LegalEntity` master + `Employment` fact — see [§9](#9-the-employer-as-organization-decision) |
| A | `Assignment.a1_facts_json["activity"]` | same assignment, extracted into its own versioned block |
| O | `config/institutions/*.json` (11 profiles) + `config/institution.json` — files with `source_url`, `verified_on`, runtime sha256 | `Institution` master table, **seeded from** the reviewed files, files retained as the provenance record |
| C | `a1/cohort.json` + `A1Case` | `A1Case` as the single authority; cohort becomes a compatibility export |
| P | `A1Case.evidence_notes`, `source_snapshot_json`, `FieldProposal`/`FieldDecision` | keep, extend with typed entries |

## 3. Topic C — The certificate

The certificate is the *document*, not the data. It owns the facts that only
the issuing decision can supply.

| Official | Label | Our layout key | Source | Rule | Default | Write action |
|---|---|---|---|---|---|---|
| header | certificate number | *(page header, not a numbered position)* | `A1Case` / `cohort.json` `document_ids` | must be unique and bound to the issue year | none | reservation service, `N{office}S{seq}/{year}/{MS}` |
| 2.1 | Member State | `certificate.member_state` | **O** (institution) | M | `CZ` | institution profile |
| 2.2 | Starting date | `certificate.start_date` | C (decision) | M | none | certificate evidence, or policy-derived provisional period |
| 2.3 | Ending date | `certificate.end_date` | C (decision) | M, or 2.4 ticked (R3) | none | as above |
| 2.4 | Certificate applies for the duration of the activity | `valid_duration` (checkbox) | **derived** from 2.2/2.3 presence | R3 | unticked | derive |
| 2.5 | The determination is provisional | **not rendered** | **derived** from `form["meta"]["provisional"]` | R9 | unticked | derive — see [§11.1](#111-official-fields-the-project-does-not-render) |
| 2.6 | Transitional rules apply (Reg. 883/2004) | **not rendered** (`form["transitional_rules"] = False`) | **derived**, no reviewed source | R7 | unticked | derive; keep false until a source exists |
| 6.10 | Date | `institution.issue_date` | C (decision) | M | none | provisional: policy-generated Mon/Wed, 61–180 day window |

**The certificate number is not a numbered field.** `config/a1_layout.json`
states it plainly: "`page_header` identifies the repeated certificate number
above the numbered sections." It therefore belongs to topic C, not to a
numbered position, and it is bound to the issue year.

**Certifications are separate from facts.** A generated number, a readiness
report or a visual PASS never establishes issuance. `external_status`
requires its own evidenced external event.

## 4. Topic W — Person identity

Everything in Section 1 is the natural person. Nothing in Section 1 is
institution-owned.

| Official | Label | Our layout key | Source | Rule | Default | Write action |
|---|---|---|---|---|---|---|
| 1.1 | Personal Identification Number | `person.insurance_number` | `WorkerIdentityRevision.confirmed_fields["insurance_number"]` | M | none — unknown stays unknown | confirm identity field |
| 1.1 | Female / Male | `gender_female`, `gender_male` | **derived** from `confirmed_fields["sex"]` | M, exactly one | none | derive; never stored |
| 1.2 | Surname | `person.surname` | `confirmed_fields["family_name"]` | M | none | confirm identity field |
| 1.3 | Forename(s) | `person.given_name` | `confirmed_fields["given_name"]` | M | none | confirm identity field |
| 1.4 | Surname at birth (***) | `person.maiden_name` | `confirmed_fields["maiden_name"]` | R8 — optional | none | confirm if known; else blank |
| 1.5 | Date of birth | `person.dob` | `Worker.birth_date` | M | none | `Worker` update, atomic with the revision |
| 1.6 | Nationality | `person.nationality` | `confirmed_fields["nationality"]` | M | none | confirm identity field |
| 1.7 | Place of birth | `person.birth_place` | `confirmed_fields["birth_place"]` | M | none | confirm identity field |
| 1.8.1 | Street, N° | `residence.address` | `confirmed_fields["street"]` + `["house_number"]` | M | none | confirm residence field |
| 1.8.2 | Town | `residence.city` | `confirmed_fields["city"]` | M | none | confirm residence field |
| 1.8.3 | Post code | `residence.postal_code` | `confirmed_fields["postal_code"]` | M | none | confirm residence field |
| 1.8.4 | Country code | `residence.country_code` | `confirmed_fields["country_code"]` | M | none | confirm residence field |
| 1.9.1 | Street, N° (State of stay) | **not rendered** | — | R6 | — | nullable model field; render only when staying abroad |
| 1.9.2 | Town (State of stay) | **not rendered** | — | R6 | — | as above |
| 1.9.3 | Post code (State of stay) | **not rendered** | — | R6 | — | as above |
| 1.9.4 | Country code (State of stay) | **not rendered** | — | R6 | — | as above |

The address in 1.8 is the *habitual residence* (centre of vital interests),
per §1.3 — mandatory, and not necessarily the permanent address.
`config/address_enrichment.json` derives district/postal code/OSSZ from an
**exact address match only**, and its stated policy holds that the OSSZ is
"a review suggestion and never silently replaces the configured issuing
institution". That must survive into the DB design: enrichment proposes, a
human decides, the decision is recorded in topic P.

## 5. Topic E — Employer / legal entity

The counterparty to the activity. Section 4 is entirely topic E, except that
4.1.1/4.1.2 are derived from the status.

| Official | Label | Our layout key | Source | Rule | Default | Write action |
|---|---|---|---|---|---|---|
| 3.1 | Posted employed person | `status_posted_employee` | **derived** from the employment role + posting situation (R1) | exactly one of 3.1–3.12 | unticked | derive; never stored |
| 3.2 | Employed, working in two or more States | `status_employee_multistate` | **derived**, same source (R1) | exactly one of 3.1–3.12 | unticked | derive; never stored |
| 3.3 | Posted self-employed person | `status_posted_self_employed` | **no value available** (hardcoded `False`) | exactly one of 3.1–3.12 | unticked | **gap** — [§11.2](#112-status-33--posted-self-employed-has-no-representation) |
| 3.4 | Self-employed, working in two or more States | `status_osv_c_multistate` | **derived**, same source (R1) | exactly one of 3.1–3.12 | unticked | derive; never stored |
| 4.1.1 | Employee | `employer_type_employee` | **derived** from the same source (R2) | exactly one of 4.1.1/4.1.2 | unticked | derive; never stored separately |
| 4.1.2 | Self-employed activity | `employer_type_self_employed` | **derived** from the same source (R2) | exactly one of 4.1.1/4.1.2 | unticked | derive; never stored separately |
| 4.2 | Employer/self-employed activity code | `employment.employer_id` | `LegalEntity.registration_id` | M | none — never the tenant `Organization.key` | employment fact binds a worker to a legal entity |
| 4.3 | Name or business name | `employment.employer_name` | `LegalEntity.legal_name` | M | none | employment fact |
| 4.4.1 | Street, N° | `employment.address` | `LegalEntity.registered_address` (or the employment's own address) | M | none | employment fact |
| 4.4.2 | Country code | `employment.country_code` | `LegalEntity.country_code` | M | none | employment fact |
| 4.4.3 | Town | `employment.city` | `LegalEntity.city` | M | none | employment fact |
| 4.4.4 | Post code | `employment.postal_code` | `LegalEntity.postal_code` | M | none | employment fact |

**Section 3 and Section 4.1 are the same fact, projected twice.** Both derive
from the employment's role and situation: the role decides 4.1.1 versus
4.1.2, and the role plus the posting situation decides the Section 3 status.
That is why they can never disagree, and it is why neither is stored. Today
the shared source is `Assignment.a1_facts_json["status_profile"]`, whose
accepted values are `posted_employee`, `employee_multi_state` and
`self_employed_multi_state`; `scripts/a1_core.py:299` rejects anything else
with an explicit "undecided completion worksheet" error.

**The "4.1 OR 4.2" question resolves to 4.1.1 XOR 4.1.2.** The employer/
self-employed *kind* is exactly one of; 4.2 is the employer *code* value
belonging to that kind.

**Self-employed multi-state derives the employer from the person.**
`scripts/a1_core.py:321-334`: the employer name is the person's own surname
and forename in Czech display case with no OSVČ suffix, and the employer
address is copied from the residence when absent. That is a *policy*, not a
fact, and stays labelled as one. Under the new model it is expressed as a
`LegalEntity` of type `sole_trader` whose identity is the person's own
registration id — the derivation becomes a recorded, reviewable row instead
of a hidden rule inside the renderer.

**Multiple employers.** The application form has one employer block per
employer (ČSSZ section E/G: "Máte-li více zaměstnavatelů v ČR, vyplňte oddíl
E. vícekrát"). Section 4 of the certificate therefore binds to *one* selected
employment fact, chosen from the worker's employment facts. The choice must be
recorded, not inferred.

## 6. Topic A — Activity and territory

What is done, and where, in the host State. Conditional (R4).

| Official | Label | Our layout key | Source | Rule | Default | Write action |
|---|---|---|---|---|---|---|
| 5.1 | Name(s)/code(s) of firm(s) or ship(s) or home base(s) | `activity.name` | `Assignment.a1_facts_json["activity"]["name"]` | R4 — conditional | blank for `self_employed_multi_state` in provisional mode | activity fact |
| 5.2 | Address(es) or name(s) of ship(s) or home base(s) in host State(s) | `activity.address` | `["activity"]["address"]` — a **territory list**, not a street address | R4/R5 — conditional, alternative to 5.3 | `DE, CZ` as a **labelled policy proposal** | activity fact + local policy default |
| 5.3 | No fixed address in State(s) of (self)employment | `no_fixed_address` (checkbox) | **derived** (hardcoded `False` today, `a1_core.py:404`) | R5 — alternative to 5.2 | unticked | derive; needs a source before it can ever be ticked |

Two points the CSV mapping already states, confirmed as official behaviour
rather than local preference:

- **5.1 is not a street address.** It is the *name and code* of the firm, ship
  or home base where the person will be employed. 5.2 is the host-State
  *territory* list for the self-employed multi-state case. Our layout gives
  `activity.address` a 430-point, two-line field — consistent with a territory
  list, not an address block.
- **5.2 vs 5.3 is an exclusive pair.** Ticking 5.3 means 5.2 is left blank.
  Today 5.3 is hardcoded `False`, so the pair is never exercised: 5.2 always
  carries the value and 5.3 is never ticked.

## 7. Topic O — Issuing institution

The body that completes the form. Section 6 plus 2.1 and 2.6.

| Official | Label | Our layout key | Source | Rule | Default | Write action |
|---|---|---|---|---|---|---|
| 6.1 | Name | `institution.name` | profile `name` | M | none | institution master record |
| 6.2 | Street, N° | `institution.address` | profile `street` + `house_number` | M | none | institution master record |
| 6.3 | Town | `institution.city` | profile `city` | M | none | institution master record |
| 6.4 | Post code | `institution.postal_code` | profile `postal_code` | M | none | institution master record |
| 6.5 | Country code | `institution.country_code` | profile `country_code` | M | none | institution master record |
| 6.6 | Institution ID | `institution.code` | profile `code` | M | none | institution master record |
| 6.7 | Office fax N° | **not rendered** | profile contact | M (official) | none | **gap** — [§11.1](#111-official-fields-the-project-does-not-render) |
| 6.8 | Office phone N° | **not rendered** | profile contact | M (official) | none | **gap** |
| 6.9 | E-mail | **not rendered** | profile contact | M (official) | none | **gap** |
| 6.11 | Signature | `institution.signed_by` | profile `signed_by` | M (official signature) | none | human signatory; **never** copied from a template or example |
| — | STAMP | not rendered | institution | M (official stamp) | none | out of scope (physical stamp) |

`config/institution.json` holds the canonically issued certificate baseline
for OSSZ Teplice: name, address, code 558, member state CZ, validity
26.09.2025–25.09.2026, issued 20.10.2025, signed by Milena Vitíková. That file
is the **O** source for the authoritative path and carries the release-state
control (`"draft": false` = no DRAFT watermark).

**The office contact is not the certificate signatory.** Every current profile
carries `CONTACT_NOT_CONFIRMED_SIGNATORY`. The institution's public contact
person and the person who signs the certificate are different facts and must
stay in different fields.

## 8. Topic P — Provenance, review and authority

Topic P answers one question for every value in every other topic: *is this
real, who confirmed it, and from which source?* It owns no form field.

| Concept | Today | Rule |
|---|---|---|
| Machine proposal | `FieldProposal` | a proposal never becomes a confirmed value because machine checks passed |
| Human decision | `FieldDecision` | binds actor, time, scope and reason |
| Accepted identity | `WorkerIdentityRevision.confirmed_fields` | the export authority; missing key means *unknown*, not empty evidence |
| Case snapshot | `A1Case.source_snapshot_json` | pins the values used for one export |
| Typed evidence | `A1Case.evidence_notes` (free text today) | planned typed entries: kind, subject, actor, time, revision/hash, result |
| Review flags | `identity_reviewed`, `certificate_reviewed`, `approved_for_pdf`, `validated_by_user` | both current validators require YES/YES/YES/1; provisional mode does not waive them |
| Artifact state | `A1Case.artifact_reference`, `prepared_artifact_hash`, `visual_confirmed*` | artifact presence is separate from freshness, submission and issuance |
| Authority status | `activity_source_status`, `certificate_source_status`, `signatory_source_status` | `AUTHORITATIVE` only with an evidenced assessment; a policy default or OCR success never promotes authority |

**Review flags are claims, not facts.** Import preserves their literal values
as historical claims. Only evidenced decisions project YES/1 in an accepted
export. `pdf_created` is not an input-approval gate, and `external_status =
submitted/issued` requires its own evidenced external event.

## 9. The employer-as-organization decision

**Question: can the employer be an "organization"?**

**Answer: yes as a concept, no as the same table.**

`portal/release1a/models.py` defines `Organization` as `key` + `label`, and
every tenant-scoped model inherits `TenantModel`, which puts an
`organization` FK on it. `Organization` is therefore the **tenant** — the
isolation boundary for one agency. The employer is a **counterparty** that
happens to be a legal person. Three facts force them apart:

1. **Isolation.** If the employer were an `Organization` row, "all workers in
   organization X" would mix the agency with the agency's customers, and the
   tenant FK would point at a customer. Every query would need to
   disambiguate.
2. **Shape.** `Organization` carries only `key` and `label`. Section 4 needs
   a legal name, a registration id, a registered address, a country code and
   (for foreign employers) a foreign registration number. `key`/`label` cannot
   hold that.
3. **An existing rule forbids it.** The
   [44-column CSV mapping](release-1a-field-mapping.md) states for
   `employment_id`: "never use tenant `Organization.key` as employer evidence".

So the model gets its own master entity, and the *concept* the question
intuits is preserved:

```
Master data (not tenant-scoped; carries provenance)
├── LegalEntity          the employer / self-employed business / foreign employer
│     registration_id, legal_name, legal_form, country_code,
│     registered_address, source, verified_on, content_sha256
└── Institution          the issuing body (OSSZ / ČSSZ)
      code, name, address, country_code, contact, signatory,
      source, verified_on, content_sha256

Tenant-scoped facts
├── Worker               the person (topic W)
├── Employment           worker ↔ LegalEntity, with role, period, address  (topic E)
├── Activity             what/where in the host State, per employment       (topic A)
├── A1Case               the certificate: institution selection, dates, snapshot (topic C)
└── Evidence / decisions the provenance chain                                 (topic P)
```

`LegalEntity` and `Institution` are **master data**: reference records shared
across tenants, each carrying where it came from and when it was verified.
That is exactly the shape the current `config/institutions/*.json` profiles
already have (`source_url`, `verified_on`, runtime sha256) and exactly what
`config/address_enrichment.json` produces for employers via ARES
(`a1/employer-17511267-ares.json`).

The consequence for the current code: the JSON files stop being the database.
They become **immutable seed/import inputs with provenance**, projected into
the master tables; the tables are what the generator reads; the files stay as
the evidence of where each record came from. That satisfies "one hood per
topic" without discarding provenance — which a plain migration into a mutable
table would.

`LegalEntity.legal_form` also collapses a distinction the current model
carries awkwardly. Today "employee" versus "self-employed" is baked into
`status_profile` and drives 4.1.1/4.1.2. Under the new model the *entity* has
a legal form (`company`, `sole_trader`, `foreign_company`, …) and the
*employment* has a role (`employee`, `self_employed`). The certificate's
4.1.1/4.1.2 is projected from the role; the status in Section 3 is projected
from the role plus the posting situation. One fact, two projections, no
possibility of disagreement.

## 10. Local override for provisional forms

A local policy may override the official default for **provisional** A1 forms
without contaminating the authoritative path.

### 10.1 Existing override points

| Override | Where | Current value | Status label |
|---|---|---|---|
| 5.2 territory default | `config/a1_provisional.json` `activity_address` | `DE, CZ` | policy proposal, unverified |
| 5.1 blanking | `finalize_a1._required_review_fields` + `a1_core.mark_provisional` | blank for `self_employed_multi_state` | intentional blank |
| 6.10 issue date | `a1_core.generate_provisional_issue_date` | Mon/Wed, 61–180 day window from `issue_date_reference` | provisional |
| 2.2/2.3 period | `a1_core.provisional_one_year_period` | one-year inclusive | provisional |
| header certificate number | `a1_core.generate_provisional_document_id` | `N{office}S{seq}/{year}/{MS}` | provisional reservation |
| Visible notice | `a1_core.PROVISIONAL_NOTICE` | "NÁVRH – ČEKÁ NA POTVRZENÍ OSSZ" | visible on the artifact |

### 10.2 The boundary

An override may **supply a value the official form would otherwise leave
blank**, and may supply a **policy default for a field the institution
derives** (2.2/2.3, 6.10). An override may **not**:

1. Supply a topic W identity value. Name, birth date, nationality, sex,
   insurance number and the residence address come from the worker or from
   confirmed evidence. A policy default there is a fabricated fact.
2. Supply a topic E employer value. Employer code, name and address come from
   the employment relationship.
3. Suppress a required topic O institution value. Section 6 is the
   institution's own data; the issuing institution cannot be "overridden" by a
   local policy, only corrected by a reviewed profile.
4. Turn an unknown into a plausible value at any layer. The unknown must
   remain visible as unknown.

### 10.3 The one tension worth resolving

`config/a1_provisional.json` carries `"policy_application":
"REVIEWED_VALUES_ONLY"` and its own `warning` ("These policy display defaults
do not overwrite review.csv"). Two of those statements pull against
`activity_address: "DE, CZ"`, which is not a display default: it lands in a
numbered official field (5.2) as the *content* of the certificate.

It stays — the Section 5 policy in this repository requires it — but it must be
labelled a **provisional content default with unverified provenance**,
distinct from the display defaults, and it must never be promoted into the
authoritative path by the same code path that applies a display default. The
distinguishing property is provenance, not the value: a 5.2 default is
acceptable for a provisional form because the artifact carries the provisional
notice, the unverified provenance and a client-confirmation label. The same
value without those markers is a fabricated fact.

## 11. Gaps

### 11.1 Official fields the project does not render (17 of 55)

The layout covers 30 text fields and 10 checkboxes — **38 numbered
positions** (the two gender boxes share position 1.1 with the insurance
number). The official form has **55**: 1.1–1.7 (7) + 1.8.1–1.8.4 (4) +
1.9.1–1.9.4 (4) + 2.1–2.6 (6) + 3.1–3.12 (12) + 4.1.1/4.1.2/4.2/4.3 (4) +
4.4.1–4.4.4 (4) + 5.1–5.3 (3) + 6.1–6.11 (11).

| Missing | Why it matters | Recommendation |
|---|---|---|
| 1.9.1–1.9.4 | R6: differs from residence when posted away; cannot be merged into 1.8 | model as nullable now; render only when staying abroad |
| 2.5 | R9: the certificate states its own provisionality; we only show an overlay notice | add a layout coordinate; tick from `form["meta"]["provisional"]` |
| 2.6 | R7: a real legal condition; hardcoded false with no source | add the coordinate; keep the value false until a reviewed source exists |
| 3.5–3.12 (8) | R1: the official set is 12, we model 3 | keep out of scope; **the generator must refuse** a case needing 3.3–3.12 |
| 6.7 / 6.8 / 6.9 | R10: official institution fields; the profile already holds the contact data | add layout coordinates; render from the profile. Closes the open question in the requirements matrix |

### 11.2 Status 3.3 — posted self-employed has no representation

The most common A1 case for a self-employed client (Art. 12(2)) maps to
official status **3.3**, and the repository cannot express it:
`status_profile` accepts only three values and
`status_posted_self_employed` is hardcoded `False`
(`scripts/a1_core.py:450`, comment "Not derivable from current profiles.").

This is a **business fact gap**, not only a code gap: it needs Jan's answer
before the enum can grow, because `posted_self_employed` also requires the
4.1.2 employer block, the 5.1/5.2 activity block and a coherent 2.2/2.3
period. Until it is answered, the generator should **refuse** a
posted-self-employed row rather than emit a certificate that claims 3.4 or
3.1.

The legal reading sharpens this further, and it is why D1 was split into
D1a and D1b. Article 12(2) of Regulation 883/2004 does not apply to every
self-employed person who goes abroad: the activity abroad must be a
*"similar activity"* (Art. 14(4) Reg. 987/2009), the person must have
*"already pursued his activity for some time"* before moving (Art. 14(3);
two months is normally sufficient, per the Commission's Practical Guide), and
the activity must not exceed **24 months**. The same three conditions apply
to 3.1, with the addition of the "does not replace another person" test that
*C-527/16* (*Alpenrind*) examined and that the ČSSZ employee form makes
mandatory. Activating either 3.1 or 3.3 therefore needs **twelve code sites
and six data fields** — `legal_basis`, `posting_start`, `posting_end`,
`prior_activity_start`, `replaces_worker` and `nace_code` — which is gate
D10. The full analysis, with the decision tree and the alternatives per
block, is in [the block options](a1-block-options.md#1-the-status-33-default-answered).

### 11.3 Mandatory-ness is situation-dependent, not field-dependent

A fixed per-field "required" column is only true for Section 1 and Section 6.
For Sections 2, 4 and 5 the rule is conditional on the situation, and the
situation is what the A1 is *about*. The repository already encodes this shape
(`status_profile` gates 4.1, 5.1, 5.2 and 2.x differently), so the DB contract
should express applicability as a function of `status_profile` + situation,
not as a flat boolean per column.

### 11.4 A municipality-to-OSSZ map is not a residency rule

`config/address_enrichment.json` maps exact addresses to an OSSZ. That answers
the *competent institution* question (§1.2) but it is not a source for 1.8 —
the residence address comes from the worker. The enrichment's own policy
already says the OSSZ is "a review suggestion and never silently replaces the
configured issuing institution"; that must be preserved verbatim in the DB
design.

The consolidated gap list, including the automation and LangGraph gaps, is in
the [gap analysis](a1-gap-analysis.md). The what-if and automation brainstorm
is in [automation scenarios](a1-automation-scenarios.md).

## 12. Verification

Documentation acceptance must not load Django or any private data:

```bash
PYTHON_BIN="$PWD/venv/bin/python"
"$PYTHON_BIN" - <<'PY'
import json
import re
from pathlib import Path

layout = json.loads(Path("config/a1_layout.json").read_text())
document = Path("docs/architecture/a1-field-source-mapping.md").read_text()

# Every field and checkbox key the layout renders must appear in the mapping.
keys = set(layout["fields"]) | set(layout["checkboxes"])
missing = sorted(key for key in keys if f"`{key}`" not in document)
assert not missing, f"layout keys missing from mapping: {missing}"

# Every official section number the layout declares must appear.
sections = {entry["section"] for entry in layout["fields"].values()}
sections |= {entry["section"] for entry in layout["checkboxes"].values()}
missing_sections = sorted(s for s in sections if s not in document)
assert not missing_sections, f"layout sections missing: {missing_sections}"

# The official form has 55 numbered positions; 38 are rendered; 17 are not.
official = (
    [f"1.{i}" for i in range(1, 8)] + [f"1.8.{i}" for i in range(1, 5)]
    + [f"1.9.{i}" for i in range(1, 5)] + [f"2.{i}" for i in range(1, 7)]
    + [f"3.{i}" for i in range(1, 13)] + ["4.1.1", "4.1.2", "4.2", "4.3"]
    + [f"4.4.{i}" for i in range(1, 5)] + ["5.1", "5.2", "5.3"]
    + [f"6.{i}" for i in range(1, 12)]
)
assert len(official) == 55, len(official)
assert len(sections) == 38, f"rendered positions: {len(sections)}"
assert len(official) - len(sections) == 17, "gap count changed"

# The six topics each own a disjoint set of layout keys.
topic_of = {
    "C": ("certificate.", "institution.issue_date", "valid_duration"),
    "W": ("person.", "residence.", "gender_"),
    "E": ("employment.", "employer_type_", "status_"),
    "A": ("activity.", "no_fixed_address"),
    "O": ("institution.name", "institution.address", "institution.city",
          "institution.postal_code", "institution.country_code",
          "institution.code", "institution.signed_by"),
}
assigned = set()
for prefixes in topic_of.values():
    for key in keys:
        if key.startswith(prefixes):
            assert key not in assigned, f"{key} claimed by two topics"
            assigned.add(key)
assert assigned == keys, f"unassigned layout keys: {sorted(keys - assigned)}"

# The CSV mapping contract must stay intact: 44 columns, one row each.
rows = re.findall(r"^\| `([a-z_]+)` \|",
                  Path("docs/architecture/release-1a-field-mapping.md").read_text(),
                  re.MULTILINE)
assert len(rows) == 44, f"expected 44 CSV rows, found {len(rows)}"

print("PASS: 40 layout keys / 38 positions mapped into six disjoint topics; "
      "17 official positions declared missing; 44-column CSV contract intact")
PY
```

This proves the document is complete **with respect to what the generator
renders today**, and that the topic assignment is a partition. It does not
prove coverage of the 17 official fields in §11.1, and it proves nothing about
runtime behaviour, issuance authority or operator acceptance. Those require
the DB-MIG acceptance run.

## 13. Logic functions — complete specification per topic

Every rendered position has exactly one source, one rule, one default and one
write action. Derived positions are never stored.

### 13.1 Topic C — Certificate

File: `scripts/a1_core.py`

| Function | Line | Purpose |
|---|---|---|
| `generate_provisional_document_id()` | 138 | Header number `N{office}S{seq}/{year}/{MS}`, year bound to issue_date |
| `provisional_one_year_period()` | 177 | One-year inclusive validity (29 Feb → 28 Feb) |
| `generate_provisional_issue_date()` | 105 | Mon/Wed, 61–180 day window from reference |
| `validate_form_data()` | 494 | Fail-closed validation; rejects unsupported `status_profile` (lines 541–549) |
| `mark_provisional()` | 471 | Sets `meta.provisional`, `meta.provisional_reason`, `meta.provisional_notice_visible`; blanks 5.1 for self-employed multi-state non-draft copies (line 487) |

| Position | Source | Default | Override | Logic |
|---|---|---|---|---|
| Header number | `certificate.document_id` | None | `generate_provisional_document_id()` | `document_id_for_issue_year()` binds /YYYY/ to issue year |
| 2.1 Member State | `certificate.member_state` | "CZ" | Institution profile | Direct passthrough |
| 2.2 Start date | `certificate.start_date` | "" | Provisional one-year from start | Validate start <= end |
| 2.3 End date | `certificate.end_date` | "" | One year from start | Validate start <= end |
| 2.4 Valid duration | Derived from 2.2/2.3 | FALSE | — | `bool(start and end)` |
| 2.5 Provisional | `meta.provisional` | FALSE | — | Derived, overlay notice only |
| 2.6 Transitional rules | No source | FALSE | — | Hardcoded FALSE until reviewed source |
| 6.10 Issue date | `institution.issue_date` | Mon/Wed 61–180 days back | Row `issue_date` | Normalized to DD.MM.YYYY |

### 13.2 Topic W — Person identity

File: `scripts/a1_core.py` `build_form_data()` (line 310)

| Position | Source | Default | Override | Logic |
|---|---|---|---|---|
| 1.1 Insurance number | `confirmed_fields["insurance_number"]` | None (unknown) | Never fabricated | No display casing (code) |
| 1.1 Gender | `confirmed_fields["sex"]` | None | — | `sex == "M"` → male, `sex == "F"` → female |
| 1.2 Surname | `confirmed_fields["family_name"]` | None | — | Czech display case at render |
| 1.3 Forename | `confirmed_fields["given_name"]` | None | — | Czech display case at render |
| 1.4 Maiden name | `confirmed_fields["maiden_name"]` | "" | — | Optional, R8 |
| 1.5 DOB | `Worker.birth_date` | None | — | Normalize DD.MM.YYYY |
| 1.6 Nationality | `confirmed_fields["nationality"]` | None | Never inferred from residence | CZ → "CZ" |
| 1.7 Birth place | `confirmed_fields["birth_place"]` | None | — | Czech display case |
| 1.8.1–1.8.4 Residence | `confirmed_fields["*"]` | None | Enrichment proposes only | Exact match only, never silent OSSZ replacement |
| 1.9.1–1.9.4 Stay address | `confirmed_fields["stay_*"]` | None (nullable) | — | Render only when stay country != residence country |

### 13.3 Topic E — Employer / legal entity (Section 3 + Section 4.1)

File: `scripts/a1_core.py` `build_form_data()` (lines 340–466)

**Status profile → Section 3 + Section 4.1 mapping:**

| status_profile | Role | Situation | 3.1 | 3.2 | 3.3 | 3.4 | 4.1.1 | 4.1.2 |
|---|---|---|---|---|---|---|---|---|
| `posted_employee` | employee | posted | TRUE | FALSE | FALSE | FALSE | TRUE | FALSE |
| `employee_multi_state` | employee | multi_state | FALSE | TRUE | FALSE | FALSE | TRUE | FALSE |
| `self_employed_multi_state` | self_employed | multi_state | FALSE | FALSE | FALSE | TRUE | FALSE | TRUE |
| `posted_self_employed` | self_employed | posted | FALSE | FALSE | **FALSE** | FALSE | FALSE | FALSE |

**Default: `posted_self_employed` is NOT in the accepted `status_profile` enum.** The generator refuses such rows until Jan confirms.

| Position | Source | Default | Override | Logic |
|---|---|---|---|---|
| 3.1 Posted employee | Derived from role+situation | FALSE | — | `role == "employee" and situation == "posted"` |
| 3.2 Employee multi-state | Derived | FALSE | — | `role == "employee" and situation == "multi_state"` |
| 3.3 Posted self-employed | Derived | **FALSE** (hardcoded line 450) | Switchable via enum | `role == "self_employed" and situation == "posted"` |
| 3.4 Self-employed multi-state | Derived | FALSE | — | `role == "self_employed" and situation == "multi_state"` |
| 4.1.1 Employee | Derived from role | FALSE | — | `role == "employee"` |
| 4.1.2 Self-employed | Derived from role | FALSE | — | `role == "self_employed"` |
| 4.2 Employer code | `LegalEntity.registration_id` | None | Never `Organization.key` | Direct passthrough |
| 4.3 Employer name | `LegalEntity.legal_name` | None | — | Direct passthrough |
| 4.4.1–4.4.4 Employer address | `LegalEntity.*` | None | — | Direct passthrough |

**Self-employed special case** (lines 368–381): when no external LegalEntity exists, employer = person:
- `employer_id` = person's insurance number
- `employer_name` = person's surname + given_name (Czech display case, no OSVČ suffix)
- `employer_address` = residence address (copied when absent)

### 13.4 Topic A — Activity and territory (Section 5)

File: `scripts/a1_core.py` `build_form_data()` (line 440), `scripts/finalize_a1.py` `row_to_form()` (line 884)

| Position | Source | Default | Override | Logic |
|---|---|---|---|---|
| 5.1 Firm name/code | `activity.name` | "" for self_employed_multi_state provisional | Reviewed value | Blank permitted in provisional for self-employed multi-state |
| 5.2 Territory list | `activity.address` | "DE, CZ" policy proposal | Row-specific override wins | Territory list, NOT street address |
| 5.3 No fixed address | No source | FALSE | — | Alternative to 5.2 (R5); unreachable until source exists |

Applicability (line 441–446): Section 5 active when `status_profile in {self_employed_multi_state, employee_multi_state, posted_employee}` or `completion_preview`.

### 13.5 Topic O — Institution (Section 6)

File: `scripts/a1_core.py` `build_form_data()` (lines 422–439)

| Position | Source | Default | Override | Logic |
|---|---|---|---|---|
| 6.1 Name | Profile `name` | None | — | Direct passthrough |
| 6.2 Street | Profile `street` + `house_number` | None | — | Direct passthrough |
| 6.3 Town | Profile `city` | None | — | Direct passthrough |
| 6.4 Post code | Profile `postal_code` | None | — | Direct passthrough |
| 6.5 Country code | Profile `country_code` | None | — | Direct passthrough |
| 6.6 Institution ID | Profile `code` | None | — | Direct passthrough |
| 6.7–6.9 Contact | Profile contact | Not rendered | — | No layout coordinates (gap G2) |
| 6.10 Issue date | Profile `issue_date` or row | Provisional policy | Row `issue_date` | Normalized DD.MM.YYYY |
| 6.11 Signature | Profile `signed_by` or row | None | Never from template | Human signatory only |

**Rule:** office contact ≠ certificate signatory. Profiles carry `CONTACT_NOT_CONFIRMED_SIGNATORY`.

### 13.6 Topic P — Provenance (no form fields)

Tracked per field: proposal → decision → actor → time → source hash → snapshot → package → artifact hash. Review flags (`identity_reviewed`, `certificate_reviewed`, `approved_for_pdf`, `validated_by_user`) require evidenced decisions; provisional mode does not waive them.

---

## 14. Decision gates register

The gates below are the questions that block an A1. Each has a default that
holds when the question is unanswered, and the defaults are all
**fail-closed**: an unanswered business fact blocks the one operation that
needs it and never blocks the rest of the application.

| # | Question | Default | Owner | Switchable | Location |
|---|---|---|---|---|---|
| D1a | Agency issues posted-self-employed A1s (official status 3.3)? | NO | Jan | Yes | `status_profile` enum |
| D1b | If D1a is yes: is the agency willing to capture the situation facts Art. 12 requires? | NO | Jan | Yes | Situation record (D10) |
| D2 | Client-confirmation copy: page-level provisional marker? | NO (`visible_notice=False`) | Jan | Yes | `mark_provisional(visible_notice=...)` |
| D3 | Add `stay_*` nullable fields for 1.9? | **YES** | Jan | Yes (additive migration) | Model + `build_form_data()` |
| D4 | Render 2.5 provisional checkbox? | **YES, but derived** — ticked exactly when the situation is an Art. 13 one | Engineering | Yes | Layout coordinate + situation record |
| D5 | Keep 2.6 transitional rules FALSE? | YES (until source) | Engineering | Yes | Hardcoded FALSE |
| D6 | Render 6.7–6.9 contact block? | **YES** | Engineering | Yes | Add layout coordinates |
| D7 | 5.2 default "DE, CZ" stays? | **YES, but the list must include the home State** | Engineering | Yes | `config/a1_provisional.json` |
| D8 | Self-employed employer = person derivation? | **Replaced by a `sole_trader` `LegalEntity` row** | Engineering | Yes | `LegalEntity` master (D11) |
| D9 | 5.3 no-fixed-address branch? | NO (hardcoded FALSE) | Engineering | Yes | Nullable source field + review |
| D10 | Carry a situation record (`legal_basis`, `posting_start`, `posting_end`, `prior_activity_start`, `replaces_worker`, `nace_code`)? | **YES** | Jan | Yes | Model + `build_form_data()` |
| D11 | Permit an outbound ARES lookup from the server? | NO | Jan | Yes | `LegalEntity` import path |
| D12 | Model the certificate as a lifecycle with withdrawal and suspension states? | NO | Engineering | Yes | `A1Case` + artifact ledger |

D1 was split into D1a and D1b, and D10 was added, after the legal reading
in [the block options §1](a1-block-options.md#1-the-status-33-default-answered):
activating official status 3.3 needs **twelve code sites and six data
fields**, because Article 12(2) of Regulation 883/2004 only applies when the
activity abroad is a *similar activity*, when the self-employed has already
pursued the activity for some time (two months is normally sufficient), and
when the activity does not exceed 24 months. The same conditions apply to
3.1, with the addition of the "does not replace another person" test, which
is why D10 is needed whichever way D1a goes.

**The default for an unstated status is "undecided", and it never changes.**
No Section 3 box is ticked, the status is listed as a missing field, and no
A1 is issued. The coarse `Worker.activity_profile`
(`employee` / `self_employed`) selects the *application variant* and the
worksheet's offered choices; it is never promoted to a legal status. That is
already the behaviour of the completion-preview path, and it is the only
correct answer: the status is a legal determination under Title II of
Regulation 883/2004, and Article 16(2) of Regulation 987/2009 provides for
an undetermined situation by making the institution's initial determination
*provisional* (official field 2.5) rather than by defaulting the applicant.

---

## 15. Status 3.3 switchable design (default NO)

**Current state:** `status_posted_self_employed` = `False` at `scripts/a1_core.py:450`. `status_profile` accepts only `{posted_employee, employee_multi_state, self_employed_multi_state}`. Generator fails closed on any other value at `scripts/a1_core.py:541-549` and `scripts/finalize_a1.py:476`.

**When Jan provides data (switch to YES) — 12 sites to change:**

| # | File | Line | Change | If missed |
|---|---|---|---|---|
| 1 | `scripts/a1_core.py` | 341 | Add `"posted_self_employed"` to accepted `status_profile` set | `build_form_data` raises "Missing or unsupported a1.status_profile" |
| 2 | `scripts/a1_core.py` | 368–381 | Extend self-employed employer derivation block to cover `posted_self_employed` | Section 4.3 employer name is the raw employee name, not the person's own |
| 3 | `scripts/a1_core.py` | 443 | Add `posted_self_employed` to activity applicability set | Section 5 renders empty for a posted self-employed |
| 4 | `scripts/a1_core.py` | 450 | Change `False` → `status_profile == "posted_self_employed"` | Section 3.3 is never ticked; the certificate claims 3.1 or 3.4 |
| 5 | `scripts/a1_core.py` | 454 | Change `employer_type_self_employed` to include `posted_self_employed` | 4.1.1 and 4.1.2 both unticked — Section 4 contradicts Section 3 |
| 6 | `scripts/a1_core.py` | 485–490 | `mark_provisional` Section 5.1 blanking: include `posted_self_employed` | A provisional copy prints Section 5.1, breaking the Section 5 policy that blanks it for self-employed multi-state |
| 7 | `scripts/a1_core.py` | 541–545 | Add `"posted_self_employed"` to `validate_form_data` accepted set | **Hard fail** — "Unsupported status_profile for this visual template" at render time |
| 8 | `scripts/finalize_a1.py` | 152 / 160 | `VARIANT_PARAMETERS` `status_profiles` per variant: add `posted_self_employed` to the self-employed variant | The row matches no variant, so the wrong variant policy applies |
| 9 | `scripts/finalize_a1.py` | 476–483 | `validate_review` blockers: add `posted_self_employed` to supported set | The row is rejected as an unsupported status profile |
| 10 | `scripts/finalize_a1.py` | 869 | `employment.kind` mapping: add `posted_self_employed` → `"self_employed"` | The employment kind stays `"employee"` and contradicts 4.1.2 |
| 11 | `scripts/finalize_a1.py` | 888 | Activity default `DE, CZ`: add `posted_self_employed` to default set | No host-State territory is proposed for 5.2 |
| 12 | `scripts/a1_completion_preview.py` | 120 | `status_profile_choices`: include `posted_self_employed` | The undecided worksheet never offers the posted-self-employed option |

Layout already declares `status_posted_self_employed` checkbox at page 1 (section 3.3) — coordinate exists, no layout change needed.

Three of these (6, 8, 12) are *silent* failures: the row renders, but with a wrong or missing value. The rest raise. Sites 6, 8 and 12 are the ones a five-step activation list would miss.

---

## 16. Corrections to prior architecture notes

- `status_posted_self_employed` is at `scripts/a1_core.py:450`, not `:392`
- Layout key is `status_posted_self_employed`, not `3.3_posted_self_employed`
- `tests/test_a1_core.py` has 21 tests, not 27
- The seven A1 suites hold **124 tests** (21 + 7 + 22 + 18 + 23 + 26 + 7), not 71
- `certificate.document_id` and `meta.*` entries are not layout keys — document_id is drawn in the page header, meta entries are form metadata
- `tests/test_a1_completion_preview.py` is registered under `a1_audit_path_dependencies` package in `change-packages.yml`
- Status 3.3 requires **12** code changes, not 5 and not 9 — the count of 9 omitted `mark_provisional` 5.1 blanking (`a1_core.py:485–490`), the per-variant `status_profiles` (`finalize_a1.py:152/160`) and the preview profile choices (`a1_completion_preview.py:120`). Three of the twelve fail *silently* rather than raising, so an incomplete activation list produces a wrong certificate rather than an error
- Real defect found and fixed: `a1_completion_preview.py:120` omitted `self_employed_multi_state` from `status_profile_choices` — now includes all three supported profiles

This document is registered under the `governance_truth` package in `change-packages.yml`.
