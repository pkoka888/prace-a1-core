# A1 data and automation gap analysis

Status: proposed, 2026-10-20. Companion to the
[field → source mapping](a1-field-source-mapping.md) (one hood per topic),
the [automation scenarios](a1-automation-scenarios.md), the
[block options](a1-block-options.md), and the
[LangGraph integration guide](langgraph-integration.md). No schema, migration,
record import, evidence acceptance or real-data activation is proposed or
performed here.

Severity: **S1** blocks a correct certificate for a real case; **S2** blocks
full automation or leaves a gate weaker than intended; **S3** limits coverage
or evidence quality but does not block a correct certificate.

Ownership: *Engineering* may act; *Jan* supplies the missing business fact;
*Infrastructure* owns host and service changes.

## 1. Summary

| # | Gap | Severity | Owner | Topic |
|---|---|---|---|---|
| G1 | Status 3.3 (posted self-employed) cannot be expressed | S1 | Jan → Engineering | E |
| G2 | 17 of 55 official field positions are not rendered | S3 | Engineering | W, C, O |
| G3 | No `LegalEntity` master; employer facts are unqueryable JSON | S2 | Engineering | E |
| G4 | No `Institution` master; OSSZ data is files only | S2 | Engineering | O |
| G5 | The `status_profile` enum is coarser than the official status set | S1 | Jan → Engineering | E |
| G6 | Section 3 and 4.1 are stored in one coarse enum, not two facts | S2 | Engineering | E |
| G7 | The quality gate cannot validate the tree root of `output/provisional` | S2 | Engineering | C, P |
| G8 | LangGraph orchestrator had three defects; two fixed, one open | S2 | Engineering | — |
| G9 | The venv did not match the declared pinned experiment dependencies | S2 | Engineering | — |
| G10 | Checkpoint resume is a stub in the orchestrator | S2 | Engineering | — |
| G11 | The `no_fixed_address` (5.3) branch is unreachable | S3 | Engineering | A |
| G12 | 1.9 (State-of-stay address) has no model field | S3 | Engineering | W |
| G13 | Business facts absent from the model (NACE, replacing worker, 1.9) | S2 | Jan | E, W |
| G14 | Local-override policy conflates display defaults with content defaults | S2 | Engineering | A, C |
| G15 | Review flags remain flat strings without actor/time/scope | S2 | Engineering | P |
| G16 | A sole trader's business-registration identifier was committed in three documents | S1 | Engineering — **fixed in this increment** | P, E |
| G17 | Country and territory codes are unvalidated free text | S2 | Engineering | A, O, W |

## 2. Topic W — person identity

### G2 — official positions not rendered (17 of 55)

| Missing | Reason | Severity | Recommendation |
|---|---|---|---|
| 1.9.1–1.9.4 | R6: the State-of-stay address differs from the residence when the person is posted away. Merging it into 1.8 would misstate the residence. | S3 | Add nullable model fields now; render only when `stay_country_code != residence.country_code` |
| 2.5 | R9: the certificate states its own provisionality; today only an overlay notice says it | S3 | Add a layout coordinate; tick from `form["meta"]["provisional"]` |
| 2.6 | R7: a real legal condition under Reg. 883/2004; hardcoded `False` with no source | S3 | Add the coordinate; keep the value false until a reviewed source exists |
| 3.5–3.12 (8) | R1: the official status set has 12 members; the generator models 3 | S3 | Out of scope — but the generator must **refuse** a case whose situation needs 3.3–3.12 rather than emit a wrong status |
| 6.7 / 6.8 / 6.9 | R10: official institution fields. The profiles already carry the contact data; it never received layout coordinates | S3 | Add coordinates and render from the profile. This closes the open question already recorded in the requirements matrix ("Is the blank fax field … an intentional Section 6 requirement, a tolerated blank, or an artifact of the manually corrected PDF?") |

### G12 — no model field for the State of stay

`WorkerIdentityRevision.confirmed_fields` has no `stay_*` keys. Adding them
as nullable is safe: existing rows keep their original shape until a separate
migration backfills. Nothing in the current workflow reads them, so the
additive migration carries no behavioural risk.

## 3. Topic E — employer, role and situation

### G1 — status 3.3 cannot be expressed (S1, needs Jan)

`status_posted_self_employed` is hardcoded `False`
(`scripts/a1_core.py:450`, "Not derivable from current profiles"). The
official 3.3 is *Posted self-employed person* under Art. 12(2) Reg. 883/2004
— the ordinary case for an OSVČ client who is posted.

Extending the enum is not a one-line change: 3.3 needs the 4.1.2 self-employed
employer block, the 5.1/5.2 activity block and a coherent 2.2/2.3 period. The
decision needed from Jan: **does the agency ever issue posted-self-employed
A1 forms?** If yes, the enum grows with a tested case; if no, the generator
should fail closed on such a row and the fact can be recorded once.

The full activation path is **23 code sites**, listed with the failure mode of
each in [the field mapping §15](a1-field-source-mapping.md#15-status-33-switchable-design-default-no).
**Sixteen** of the twenty-three fail *silently* rather than raising, so an
incomplete activation list produces a wrong certificate rather than an error.
That is why the count matters. The raising sites are the accepted set in
`a1_core.py`, the `validate_form_data` set, the three `finalize_a1.py`
guards, the preview `PROFILES` map and the portal input whitelist; the
silent ones include the `employment["kind"]` mappings, the Section 5.1
blanking, the per-variant `status_profiles`, the preview profile choices, the
assignment-facts choice list and the quality-gate branches.

### G5 — the status enum is coarser than the official set

`status_profile` accepts three values where the official form has twelve
statuses. The mapping is a deliberate narrowing (posting, multi-state
employee, multi-state self-employed) and covers the cases this agency issues.
The gap is that the narrowing is not *declared*: nothing in the code states
"3.5–3.12 are out of scope". A reviewer cannot tell an intentional scope
limit from an omission.

### G6 — one coarse enum carries two distinct facts

`status_profile` simultaneously determines the Section 3 status and the
Section 4.1 employer kind. That coupling is *why* the two can never
disagree, and it is worth keeping — but it is stored as one opaque string.
**Update, 2026-10-21.** The CZ-NACE main activity now has a home:
`Assignment.nace_code`, nullable, and carried into the assignment fact.
The State-of-stay address (1.9) remains without a home, and it is a bigger
piece than a column: it needs a parallel address field set in the identity
proposal chain, so it is recorded as gate D13 rather than silently dropped.

**Update, 2026-10-20.** Decisions D1b and D10 were taken: the model now
carries `prior_activity_start` and `replaces_worker` on the `Assignment`
(migration `0021_a1_situation_facts`), and the issuance gate refuses a
posting that does not answer the replacement question or whose certificate
covers more than 24 months. `legal_basis` was dropped as derivable from the
status profile, and `nace_code` moved to the A block. The remaining two
facts — the CZ-NACE main activity and the State of stay — are still absent.

Under the [employer-as-organization decision](a1-field-source-mapping.md#9-the-employer-as-organization-decision)
the two facts separate into `Employment.role` (employee / self_employed) and
`Employment.situation` (posted / multi_state / in_state), and both become
queryable without changing a single rendered value.

### G13 — business facts with no home in the model (closed for two of them)

Six official or mandatory facts have nowhere to live. The first three are
the situation facts that D10 introduces; the last three are the business
facts G13 has always carried:

| Fact | Where the authority requires it | Today |
|---|---|---|
| Legal basis (Art. 11 / 12 / 13 / 16) | the situation decides which legislation applies | absent |
| Posting start and end | Art. 12: the activity does not exceed 24 months | absent |
| Prior activity start | Art. 14(3) Reg. 987/2009: the self-employed must already have pursued the activity; two months is normally sufficient | absent |
| Replacing another posted worker | ČSSZ: "Údaj o nahrazování jiného vyslaného pracovníka je povinný v situaci vyslání" | absent |
| NACE main activity | ČSSZ: "povinně označte jeden (hlavní) obor činnosti" | absent |
| State of stay (1.9) | official form 1.9.1–1.9.4 | absent |

All three are **business facts Jan must supply**, and each needs a nullable
model field plus a rule that keeps it blank until supplied. The rule matters
more than the field: a blank that blocks one A1 operation must never block
saving the worker.

### G3 — no `LegalEntity` master

Employer facts live inside `Assignment.a1_facts_json` as structured JSON.
That is honest about the versioned-relationship part, but it means:

- the same employer repeated across 30 workers exists 30 times with no shared
  identity;
- "which clients work for employer X" is a JSON scan, not a query;
- ARES enrichment (the ARES-enriched employer record under `a1/`) has no key to attach to;
- 4.2 cannot be checked for uniqueness or cross-checked against a registry.

Severity S2: it does not block a correct certificate, but it blocks reuse,
deduplication and registry verification — and the employer is the field most
likely to be reused across a whole cohort.

## 4. Topic A — activity and territory

### G11 — the 5.3 branch is unreachable

`no_fixed_address` is hardcoded `False` (`scripts/a1_core.py:404`, "No
reviewed source field exists for this checkbox yet"). R5 makes 5.2 and 5.3
alternatives, so an address-less activity (an international truck driver is
the ČSSZ example) has no representation: the renderer would always print the
5.2 territory. The source field is a fact, not a policy, so the fix is a
nullable field plus a review decision, not a default.

### G14 — display defaults and content defaults share one policy file

`config/a1_provisional.json` declares `"policy_application":
"REVIEWED_VALUES_ONLY"` and warns that "These policy display defaults do not
overwrite review.csv", yet `activity_address: "DE, CZ"` is not a display
default — it lands in official field 5.2 as the content of the certificate.

The value itself stays (the Section 5 policy in this repository requires it).
What must change is the classification: the policy file needs a distinct
`content_defaults` block, each entry carrying its own unverified-provenance
label, and the promotion path to the authoritative render must be blocked
separately from the promotion path for display defaults. Severity S2 because
a reader of the current file cannot tell which defaults are safe to promote.

## 5. Topic O — issuing institution

### G4 — no `Institution` master

Institution data is 11 JSON profiles plus `config/institution.json`, each
carrying `source_url`, `verified_on` and a runtime sha256. That is good
provenance, but it means:

- the profiles are selected by path convention, not by key;
- there is no query for "every case handled by OSSZ Teplice";
- the institution a case used is a *string* in the snapshot, not a reference;
- 6.7/6.8/6.9 (G2) have nowhere structured to live once rendered.

The recommendation is **not** to migrate the files into a mutable table — that
would discard the provenance `validate_profile` and `publish_input_cohort`
depend on. The recommendation is a read-only `Institution` master **seeded
from** the reviewed files, with the files retained as the evidence of record
and the seed operation audited.

## 6. Topic C and P — certificate, provenance, gates

### G7 — the quality gate cannot validate the tree root

`require_completed_generation(pdf_dir)` compares the manifest's declared
`{path: sha256}` against every `A1_*.pdf` in `pdf_dir` and requires exact
equality. The tree root of `output/provisional` holds 26 PDFs that **no
surviving manifest describes** (verified: the 2026-09-08 `validate_manifest.json`
matches 0 of 24; the 2026-09-14 and 2026-09-16 manifests match 0 of 24),
because two of them are V6-path orphans and the rest predate the current
manifests. The gate is therefore only satisfiable for a **package directory**,
never for the tree root.

That is a documentation/expectation gap as much as a code gap: the tree root
looks like a publishable package and is not one. Options: document the tree
root as an archive index and never target it, or move legacy root PDFs into
an archive directory. Both need the same precondition — the two Oct-19
orphans must be classified first.

### G15 — review flags are flat strings

`identity_reviewed`, `certificate_reviewed`, `approved_for_pdf` and
`validated_by_user` carry a value but no actor, time or scope. The
[field mapping](release-1a-field-mapping.md) already specifies the target
(typed entries in `A1Case.evidence_notes` with kind, subject, actor, time,
revision/hash, result). The gap is that the four flags are only **CSV and
export row keys** (`portal/release1a/a1_exports.py`, `scripts/finalize_a1.py`),
not model columns, so they carry no actor, time or scope and no typed
decision backs them: a YES cannot be attributed. Severity S2: it weakens the
evidence chain, and the field-mapping contract already treats the flat flags
as historical claims rather than authority.

## 7. Automation gaps (LangGraph)

Measured on 2026-10-20 against the installed stack
(`langgraph 1.2.11`, `langgraph-checkpoint-postgres 3.1.2`,
`langgraph-checkpoint-sqlite 3.1.1`).

### G8 — orchestrator defects (two fixed, one open)

| Defect | Symptom | Status |
|---|---|---|
| `a1_private_dir` used before assignment | `UnboundLocalError: cannot access local variable 'a1_private_dir'` on every `run` invocation — the module-level function was shadowed by a local rebinding three lines later | **Fixed.** The local was renamed to `private_dir` and hoisted above its first use |
| State channel named `checkpoint_id` | `ValueError: Channel name 'checkpoint_id' is reserved` at `graph.compile()`. LangGraph 1.x reserves `checkpoint_id`, `checkpoint_map`, `checkpoint_ns` and `configurable`. The script was written against the 0.3.x API | **Fixed.** The channel was renamed `workflow_run_id`; the CLI argument keeps its user-facing name |
| A dry run wrote into the protected output tree | `--dry-run` overwrote `output/provisional/generation_manifest.json` with a 130-byte stub and created `output/qa_report.json`. The canonical publisher's manifest is the evidence that a generation completed, and `require_completed_generation` reads it | **Fixed.** A dry run now writes nothing; the simulated manifest and QA report go to stdout only. Covered by `tests/test_langgraph_a1_orchestrator.py` |

The third defect was found by running the tool, not by reading it. The
overwritten manifest was restored from the in-tree preserved copy of the
2026-09-16 canonical run (`run_id eb257cfb-…`, receipt
`a1/receipts/eb257cfb-….json`, status `completed`); the restored file is
8183 bytes, mode 0600, byte-identical to
`output/provisional/5214b64f-7646-4764-8dde-cd95ed30d6c7/generation_manifest.json`.
The discovery inventory's 2026-09-17 record of the same file (8183 bytes,
mode 0600) matches. The exact bytes of the 2026-09-08 manifest that preceded
it are not recoverable — no surviving copy matches the current root PDFs.

### G9 — the environment did not match the declared contract

`config/agent_ops_workflow.v1.json` declares `langgraph-checkpoint-sqlite
3.1.1` as a pinned dependency and
`config/agent_ops_workflow.v1.requirements.txt` lists it, but it was not
installed in the venv; `langgraph-checkpoint-postgres 3.1.2` was installed and
declared nowhere. Consequently all 37 agent-ops tests failed at setup with
`ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'`, and
`test_pinned_experiment_dependencies` failed with
`PackageNotFoundError`.

**Resolved:** `langgraph-checkpoint-sqlite==3.1.1` was installed into the venv
from the already-pinned repository file. The suite then passes: **37 passed in
176.67s**. The suite also requires the documented in-repository `--basetemp`
(`runtime/portal/temporary/...`); with pytest's default `/tmp` the
`private_directory` guard correctly refuses to run, which is a feature, not a
bug.

The boundary that must stay: the main `requirements.txt` does **not** declare
LangGraph, and must not. The core stays clean of LangGraph imports, so the
canonical generator runs without it.

### G10 — checkpoint resume is a stub

`cmd_run` answers `--resume` with "Full checkpoint resume requires database
implementation" and returns 0 — a successful exit code for a no-op. The
`PostgresSaver` path itself works (`scripts/test_langgraph_install.py` runs
an ephemeral PostgreSQL cluster and round-trips a checkpoint), and the
agent-ops workflow proves durable resume and recovery semantics against a
SQLite checkpoint. So the *capability* is proven; the *A1 workflow's* resume
is not wired. Severity S2: an operator told "resuming" would believe the run
continued when it did not.

### G16 — a business-registration identifier was committed (S1, fixed)

Three architecture documents cited the ARES-enriched employer record by its
file name, and the file name embeds the employer's **IČO**. For a sole trader
the IČO *is* a natural person's identity: it is the person's registration in
the commercial register, it is publicly searchable in ARES, and it resolves
to a name. The repository's own rule places `a1/` and `evidence/` outside
version control, and the evidence files that carry this identifier are
untracked — so the identifier in a committed document contradicted the
repository's own treatment of the same identifier elsewhere.

The fix removed the identifier from the three documents and from a fourth
written earlier, and extended `scripts/check_git_content.py` — the existing
guard that already scans HEAD blobs for credential signatures — with a
business-registration check. The detector is deliberately narrow, because a
bare eight-digit check-digit test is far too noisy: over HEAD it produced 60
hits, almost all dates in `YYYYMMDD` form and synthetic benchmark ids. The
shipped rule is: eight digits, word-bounded, not a calendar date, passing
the IČO check digit, within 80 characters of a registration keyword
(`IČO`, `ico`, ARES, *identifikační*, *obchodní jméno*, `employer_id`), and
not under `research/synthetic/`, which is synthetic by construction. On the
pre-fix tree that rule matched exactly the three offending documents and
nothing else in the repository, so it is a usable regression guard rather
than a noise generator. The guard reports the path only, never the value.

### G17 — country and territory codes are unvalidated free text (S2)

Every "Country code" field on the official form — 1.8.4, 1.9.4, 4.4.2, 6.5 —
is an ISO 3166-1 alpha-2 code, and the form's own footnote fixes the domain
of a "State": *"any European Union country, plus Iceland, Liechtenstein,
Norway and Switzerland"*, with the United Kingdom added for the Withdrawal
Agreement bilateral cases. The repository uses the two-letter convention
(`"country_code": "CZ"` in the institution profiles, `kodStatu` in the ARES
records) but validates it nowhere: a typo in `activity.address` or
`employment.country_code` would render as an unknown territory with no
diagnostic.

The two codes in the policy default are unambiguous and were verified against
the repository's own evidence: **DE is Germany and CZ is Czechia**; Denmark
would be DK, and the repository contains no reference to Denmark or DK
anywhere. Its posting scenario settles the meaning — `cz_employee_to_de`
sets field 2.1 to `CZ`, field 4.4.2 to `CZ` and field 5.2 to `DE`, which is a
Czech worker posted to **Germany**. The default `DE, CZ` is therefore a
territory list of Germany and Czechia, and it already includes the home
State; its real deficiencies are that it is an untyped comma-joined string,
that it is a labelled policy proposal rather than a reviewed value, and that
nothing checks the codes against the closed State domain.

## 7b. Findings from the decision increment

**The employment block had no source status — now it does (gate D15).** The
repository said where the activity, the certificate and the signatory came
from (`activity_source_status`, `certificate_source_status`,
`signatory_source_status`) and said nothing about the **employer**. Section 4
of the form — the code, the name and the seat — is a legal claim about a
counterparty, and a hand-typed employer name in a review row was
indistinguishable from a registry-verified one. The two reviewed employer
records made that visible: both are sole traders whose registry record
carries a name and a seat, and both review rows carry free text for the same
facts.

The export now compares the row with the register and records the answer in
`employment_source_status`: `REGISTRY_VERIFIED` when they agree,
`DIVERGES_FROM_REGISTER` when they do not, and the column is **absent**
when there is no reviewed record — absence is "not stated", and the reviewer
decides. A divergent employer is refused before issue, because Section 4 is a
legal claim. The row is never silently replaced: the divergence is reported
and the operator reconciles it.

**The file path learns it too.** The generator reads a review CSV and must
not reach the network or the database, so a hand-written row could still
carry an employer the register contradicts while the portal's export could
not. `scripts/import_ares_legal_entity.py --annotate` closes that: it reads
the registration numbers out of the review file, compares each row against the
register, and writes the status into the file. The comparison itself is the
review contract's, so the export and the import path agree.

**One of the agency's own employment identifiers is not a Czech
registration number.** The review data names three: two are eight-digit
numbers the register accepts, and the third is **nine digits** with the
country recorded as CZ, which the register refuses with `ARES_HTTP_400`. A
Czech IČO is eight digits, so the value is either a data-entry error or a
foreign registration number recorded with the wrong country. The import
reports it and continues with the rest, which is the behaviour a batch
import needs, but the value itself is the operator's to correct — it is not
guessed at, and the registry's refusal is the evidence.

**The import could discover the identifiers itself.** Running it with no
arguments now reads the registration numbers out of the agency's own review
data and retrieves each for review, so the first step is one command rather
than one command per employer. It still never invents a subject: the
numbers come from the reviewed rows, and the ones still pending are skipped.

**The client-confirmation copy failed its own quality gate.** The copy was
rendered by the placeholder framework, which erased 279, 610 and 40 template
pixels on the three pages against a limit of 24, so the document the agency
sends to a client never passed the gate meant to vouch for it. The threshold
is tuned for the coordinate renderer, which stays within it. This predated
the decision increment and was found while implementing D2, because the
decision needs the copy to carry a notice and the placeholder framework
cannot draw one. The copy now uses the coordinate renderer — the documented
V1 path — which draws the notice natively, satisfies the threshold, and
removes the need for a second notice mechanism. The placeholder framework
remains the documented vector-template alternative.

**The notice rule in the quality gate was unconditional.** It forbade the
provisional notice in any PDF, which was right when no published document
carried it and wrong once the client copy was marked on purpose. The rule is
now scoped: the notice is **required** in a client-confirmation package and
**forbidden** in an authoritative one, decided from the generation manifest's
status. A certificate that said it was a draft would be self-contradictory,
and a copy that said it was a draft but did not would be misleading.

**The 44-column review contract was a hard ceiling.** It is now the
*required* set, with two documented optional columns for the Article 12
situation facts. A review file without them still reads and is
byte-identical to before; a file with them carries the facts so the issuance
gate can check them. The alternative — extending the required contract — would
have broken every external consumer of the export for two validation-only
fields that are not on the form.

## 8. What is explicitly not a gap

- The 44-column CSV contract, `read_review` arity guard, `finalize_a1`
  validation gates, the provisional notice and the issuance workflow are
  unchanged by this analysis.
- Official A1 issuance remains outside v1 scope.
- The two Oct-19 V6 orphan PDFs are already classified and excluded from the
  audited package set; G7 is about the tree root, not about those two files.
- LangGraph is not needed for any of the six topics. It is an optional
  orchestration layer over a deterministic core, and none of G1–G15 requires
  it.
