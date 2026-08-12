# A1 Release Gate — Current Status

This documents the state of the A1 release gate after the privacy remediation and
local history rewrite. It is intentionally conservative: the package remains
labelled `client-confirmation` / `provisional` and regeneration is blocked.

## Font (Czech-capable)

- The renderer resolves a Czech-capable TTF via `_register_font()` in
  `scripts/a1_core.py`, trying in order: bundled `assets/fonts/DejaVuSans.ttf`,
  then common system locations (`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`).
- No bundled font is currently committed, so the build depends on the host
  providing `DejaVuSans`. To make this reproducible and hash-locked:
  - Commit `assets/fonts/DejaVuSans.ttf` to the repository.
  - Record its SHA-256 here and assert it at runtime before rendering.
- System font observed at `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
  (SHA-256 `57f73e11f51999432bf7ab22ce55b6f945d5eca1bf824404cfa9ec2e3718c84e`).
  This is **informational only**; do not rely on the host copy for release builds.

## Birth-number / identity validation

- `scripts/finalize_a1.py::_birth_number_matches_dob` validates that the
  insurance/birth number is consistent with the person's date of birth and sex,
  including the female month-offset rule (month + 50).
- It does **not** assert the Czech checksum digit. Add checksum validation before
  promotion so malformed numbers fail closed.

## Deterministic validation (implemented)

- Birth place, nationality, and full residence are validated deterministically in
  `scripts/finalize_a1.py`.
- The quality gate (`scripts/a1_quality_gate.py`) is **fail-closed**: it refuses a
  PASS when reviewed `employment_*` (Section 4) columns are absent, when
  certificate document IDs are not unique, or when any legacy/forbidden text is
  present.

## Checkbox geometry

- `employee_multi_state` checkbox geometry is **not** implemented. The current
  cohort is self-employed multi-state only. Resolve checkbox geometry on page two
  before enabling `employee_multi_state`; do not enable it prematurely.

## QA manifest

- `validate` writes a hash-bound manifest covering input files, generated PDFs,
  previews, and the QA report.
- TODO: also record the source commit and SHA-256 of `scripts/*.py`,
  `templates/a1_background.pdf`, and `config/a1_layout.json` in the manifest so a
  package is reproducible and traceable.

## Evidence preservation

- Canonical provisional artifacts and their hash-bound evidence are kept only in
  the protected gitignored project `output/` tree. Do not create or rely on an
  external project backup path. Validate existing material against its manifests;
  regeneration must follow the canonical pipeline and current approval gates.
- Promotion to `output/pdf/` requires, in addition to the above: authoritative
  certificate/signatory evidence, a visual PASS, and `validated_by_user=1` for all
  11 records, and reviewed Section 4 fields for every person.
