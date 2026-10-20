# A1 topic data architecture (one hood per topic) — architecture solution

Status: proposed, 2026-10-20. Non-PII. Synthetic examples only. This solution
proposes a data arrangement; it does not implement a schema, migrate records,
accept evidence or activate real data.

Companions: the
[field → source mapping](../a1-field-source-mapping.md) (the per-field
contract), the [gap analysis](../a1-gap-analysis.md) (what is missing), the
[automation scenarios](../a1-automation-scenarios.md) (the what-if), and the
[LangGraph guide](../langgraph-integration.md) (the orchestration boundary).

## 1. The problem this solves

The A1 data is currently spread across four places that do not know about each
other:

| Place | What it holds | Problem |
|---|---|---|
| `a1/employees_normalized.json` | scan-derived person facts | flat, per-person, no query |
| `a1/review.csv` (44 columns) | a flattened projection of every topic | mixes person, employer, institution, authority and flags in one row |
| `a1/cohort.json` | issuance authority: dates and certificate numbers | not an employee list; easy to mistake for one |
| `portal/release1a` models | the durable records the generator never reads | a parallel universe |

The generator reads the first three and ignores the fourth. Every "why is
this value here?" question needs three files and a convention.

## 2. The solution: six topics, one owner each

Read the form as six topics. Each has one owner. A field is a *projection* of
its owner's fact, never a second copy.

| Topic | Hood | Owns | Official positions |
|---|---|---|---|
| **C** | Certificate | the issued document: run identity, header number, validity period, issue date | header, 2.2, 2.3, 2.4, 2.5, 6.10 |
| **W** | Person | the natural person: identity and habitual residence | 1.1–1.9.4 |
| **E** | Employer, role, situation | the counterparty, the role and the situation | 3.1–3.4, 4.1.1, 4.1.2, 4.2, 4.3, 4.4.1–4.4.4 |
| **A** | Activity | what is done, and where, in the host State | 5.1, 5.2, 5.3 |
| **O** | Institution | the issuing body | 2.1, 2.6, 6.1–6.9, 6.11 |
| **P** | Provenance | whether a value is real, who confirmed it, from which source | no field; answers for every field |

Two invariants:

1. **One owner per fact.** A value is stored once. No value can disagree with
   itself, because there is no second copy to disagree with.
2. **Derived fields are never stored.** Ten of the 38 rendered positions are
   computed: the gender pair at 1.1, the four Section 3 status boxes, the two
   Section 4.1 kind boxes, 2.4 and 5.3. Section 3 and 4.1 are the *same* fact
   projected twice — the employment's role and situation — which is exactly
   why they can never contradict each other.

The topic assignment is machine-checked: the verification in
`a1-field-source-mapping.md` §12 asserts that the 40 layout keys partition
into the six topics with no overlap and no remainder.

## 3. The employer-as-organization decision

**Question: can the employer be an "organization"?**

**Answer: yes as a concept, no as the same table.**

`Organization` in this repository is the **tenant** — the isolation boundary.
Every tenant-scoped model inherits `TenantModel`, which puts an
`organization` foreign key on it, and `Organization` itself carries only
`key` and `label`.

The employer is a **counterparty** that happens to be a legal person. Three
facts force them apart:

1. **Isolation.** If the employer were an `Organization` row, "all workers in
   organization X" would mix the agency with the agency's customers, and the
   tenant foreign key would point at a customer.
2. **Shape.** Section 4 needs a legal name, a registration id, a registered
   address, a country code and — for a foreign employer — a foreign
   registration number. `key`/`label` cannot hold that.
3. **An existing rule forbids it.** The
   [44-column mapping](../release-1a-field-mapping.md) states for
   `employment_id`: "never use tenant `Organization.key` as employer evidence".

So the model gets its own master entity, and the concept the question intuits
is preserved:

```
Master data (not tenant-scoped; carries provenance)
├── LegalEntity     employer / self-employed business / foreign employer
│     registration_id, legal_name, legal_form, country_code,
│     registered_address, source, verified_on, content_sha256
└── Institution     the issuing body (OSSZ / ČSSZ)
      code, name, address, country_code, contact, signatory,
      source, verified_on, content_sha256

Tenant-scoped facts
├── Worker          the person                                  (topic W)
├── Employment      worker ↔ LegalEntity: role, situation, period (topic E)
├── Activity        what/where in the host State, per employment (topic A)
├── A1Case          the certificate: institution, dates, snapshot  (topic C)
└── Evidence        proposals, decisions, provenance               (topic P)
```

`LegalEntity` and `Institution` are **master data**: reference records shared
across tenants, each carrying where it came from and when it was verified.
That is exactly the shape the current `config/institutions/*.json` profiles
already have (`source_url`, `verified_on`, runtime sha256) and exactly what
`config/address_enrichment.json` produces for employers via ARES.

### 3.1 The files become seeds, not the database

The JSON files stop being the store. They become **immutable import inputs
with provenance**, projected into the master tables; the tables are what the
generator reads; the files stay as the evidence of record. This is the
difference between a migration and an import, and it is why the provenance
survives: a plain migration into a mutable table would discard exactly the
metadata `validate_profile` and `publish_input_cohort` depend on.

### 3.2 `legal_form` collapses an awkward distinction

Today "employee" versus "self-employed" is baked into `status_profile`, and
that one string drives 4.1.1/4.1.2. Under the new model:

| | today | proposed |
|---|---|---|
| who the counterparty is | JSON in the assignment | `LegalEntity` with a `legal_form` |
| what the person does for them | folded into `status_profile` | `Employment.role` |
| what the situation is | folded into `status_profile` | `Employment.situation` |
| 4.1.1 / 4.1.2 | derived from the enum | projected from `Employment.role` |
| Section 3 status | derived from the enum | projected from role + situation |

A sole trader is then a `LegalEntity` with `legal_form = sole_trader` whose
identity is the person's own registration id — the same entity table serves
employers and OSVČ, and the Section 4 block for an OSVČ is a normal row
rather than a special case inside the renderer.

## 4. How this lands without breaking anything

The order matters, because the 44-column CSV contract, the validation gates,
the provisional notice and the issuance workflow must not change.

| Step | Change | Risk |
|---|---|---|
| 1 | Add `LegalEntity` and `Institution` master tables, nullable, no backfill | none — additive |
| 2 | Seed them from the reviewed profile files and the ARES-derived employer records, with the source hash carried on each row | none — the files stay authoritative until the seed is reviewed |
| 3 | Add `Employment.role` and `Employment.situation` as nullable, derived from the existing `status_profile` on read | none — one source of truth during the transition |
| 4 | Project the CSV and the direct-core form data from the new owners; keep the 44-column export byte-compatible | medium — the export is the compatibility seam and must not move |
| 5 | Add the missing official positions (1.9.x, 2.5, 2.6, 6.7–6.9) as nullable model fields and layout coordinates | low — additive, and the values stay blank until sourced |
| 6 | Retire `a1/cohort.json` and `a1/employees_normalized.json` as *editable* inputs, keeping them as compatibility exports | medium — other consumers exist |

Steps 1–3 are schema-only and can be accepted independently of any cutover.
Step 4 is where the generator starts reading the database instead of files, and
it is the step that needs the DB-MIG acceptance run.

## 5. What this solution does not decide

- Whether the agency ever issues posted-self-employed A1 forms (official
  status 3.3). That is a business fact, and it blocks the `Employment.situation`
  enum from being complete.
- Whether the 15 unrendered official positions get layout coordinates now or
  later.
- Whether `a1/cohort.json` and `a1/employees_normalized.json` are retired or
  kept as read-only compatibility exports.
- Any change to the 44-column contract, the validation gates, the provisional
  notice, or the issuance workflow. None is proposed here.

## 6. Known limitations

- Documentation only. No schema, migration, seed, record import, evidence
  acceptance or real-data activation is performed or claimed.
- The seed step needs a reviewed selection manifest; no selection is proposed
  here.
- Master data shared across tenants is a deliberate choice with a deliberate
  risk: a correction to an `Institution` or `LegalEntity` must not silently
  reach an already-issued certificate. The existing per-case
  `A1Case.source_snapshot_json` pinning is what prevents that, and the new
  arrangement must preserve it.
- Official A1 issuance remains outside v1 scope.

## 7. Reproduce / verify

```bash
venv/bin/python -m pytest tests/test_langgraph_a1_orchestrator.py -q
venv/bin/python scripts/validate_planning.py
```

The per-field completeness and the six-topic partition are checked by the
script in `a1-field-source-mapping.md` §12.
