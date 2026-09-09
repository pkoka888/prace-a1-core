# A1 field policy

## Authority and provenance

- Identity and cohort fields come only from `$A1_PRIVATE_DIR/a1/review.csv` and `$A1_PRIVATE_DIR/a1/cohort.json`, backed by the named protected sources and operator transcription. The removed `private/a1_final_review.csv` path must not be reintroduced.
- `config/a1_provisional.json` supplies non-personal provisional policy and placeholders only; it must never supply a person's identity or cohort membership.
- Office name, address, code, source URL, and current contact come from the selected JSON profile in `config/institutions/`.
- Activity, certificate ID, certificate period, issue date, and signatory remain provisional until authoritative OSSZ evidence and operator approval exist.
- Every transformed value must be traceable to its source file and source hash.

## Text

- Preserve Czech and Slovak diacritics.
- Display personal names in natural case, for example the synthetic names `Jan Novák` and `Eva Horáková`; do not force source uppercase into the PDF.
- Apply Czech address casing without changing abbreviations, house numbers, postal codes, or legal spelling.
- Preserve the reviewed activity territory, including the requested `DE` scope; global policy defaults never overwrite accepted row values.
- Employee-copy presentation omits Section 5 values and leaves 5.3 unselected; Section 5 applies to employees too, so this is a requested copy presentation, not a legal applicability rule. Required activity evidence remains in the reviewed input.
- Fit by choosing a documented field-specific font size within limits. Never cover the template with a white text box, erase a colored rule, or silently truncate content.
- Position from the actual font ascent/descent and the field's declared row bounds. A field-specific adjustment is allowed only when recorded and regression-tested.

## Checkboxes

- Checkbox coordinates declare both page and rectangle.
- Checkbox values come from normalized form state, not from pixels in another employee PDF.
- `posted_employee` selects 3.1 and 4.1.1; `employee_multi_state` selects 3.2 and 4.1.1; `self_employed_multi_state` selects 3.4 and 4.1.2. Section 3.3 denotes posted self-employment, not employees.
- Gender marks come from person data. The repaired template has no baked gender/2.4/5.3 selection; validity and no-fixed-address remain unselected without explicit evidence.
- Draw a mark inside an existing canonical box. Do not redraw nearby labels, green squares, rules, or page artwork during population.

## Dates and identifiers

- Preserve authoritative reviewed issue/start/end dates. The former Monday/Thursday/backdated placeholder policy is historical; never synthesize or replace accepted certificate dates.
- Certificate IDs must be unique across the cohort. Their format or apparent sequence is not evidence that OSSZ issued them.

## Release states

- `output/provisional/` is for client/operator confirmation and may contain unconfirmed issuance fields.
- A row with `validated_by_user=0` or an unverified source status fails canonical generation. Pending visual QA or missing artifact approval prevents promotion. Generation writes candidate/provisional packages, never reserved final destinations.
- Removing a visible draft notice does not convert a provisional document into an issued certificate; preserve that status in the manifest and checklist.
