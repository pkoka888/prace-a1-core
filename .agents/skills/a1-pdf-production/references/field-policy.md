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
- Keep `DE, CZ` exactly where the provisional activity territory is required.
- Fit by choosing a documented field-specific font size within limits. Never cover the template with a white text box, erase a colored rule, or silently truncate content.
- Position from the actual font ascent/descent and the field's declared row bounds. A field-specific adjustment is allowed only when recorded and regression-tested.

## Checkboxes

- Checkbox coordinates declare both page and rectangle.
- Checkbox values come from normalized form state, not from pixels in another employee PDF.
- For the current provisional self-employed multi-state profile, the intended state includes sections 3.4 and 4.1.2; all other selections must follow explicit form data.
- Draw a mark inside an existing canonical box. Do not redraw nearby labels, green squares, rules, or page artwork during population.

## Dates and identifiers

- Provisional issue dates must be different per employee, fall on Monday or Thursday, and be 61–180 days before the configured reference date.
- Sections 2.2 and 2.3 use the configured one-year provisional period; the end date is one day before the anniversary.
- Certificate IDs must be unique across the cohort. Their format or apparent sequence is not evidence that OSSZ issued them.

## Release states

- `output/provisional/` is for client/operator confirmation and may contain unconfirmed issuance fields.
- A row with `validated_by_user=0`, an unverified source status, or pending visual QA cannot be promoted to `output/pdf/`.
- Removing a visible draft notice does not convert a provisional document into an issued certificate; preserve that status in the manifest and checklist.
