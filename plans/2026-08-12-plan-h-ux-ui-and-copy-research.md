# Plan H — UX, UI, and Copy Research

**Status:** active
**Milestone:** M1A–M3
**Owner:** product design

## Objective

Define a calm, efficient Jan/operator portal experience and evidence-backed Czech/German product voice.

Synthetic wireframes and acceptance scripts may proceed from the operational
Plan L/M baseline and the recommended defaults in the Release 1A decision brief.
Observed completion by Jan/operator remains required for this plan's exit.

## Research and validation

- Research and propose the recommended UX before requesting user decisions. Present alternatives only where they materially affect workflow or architecture, with a textual/wireframe example for each.
- Inspect named regional and international recruitment, document-review, and operations products; record dated sources and specific patterns without copying protected designs or text.
- Map Jan and operator journeys for login/MFA, dashboard, employee creation, upload/quarantine, OCR review, assignment history, missing information, A1 case preparation, preview, errors, and audit/history.
- Produce low-fidelity desktop and mobile wireframes and test them with Jan and the operator using synthetic data.
- Define navigation, information hierarchy, status vocabulary, form/error/recovery behavior, keyboard/focus behavior, contrast, responsive targets, and WCAG-oriented acceptance checks.
- Define Czech-first language and precise formal German partner language; validate terminology with users and keep official-certificate claims out of product copy.
- Use the sanitized interaction patterns identified by the
  [Google AI Studio frontend review](../docs/prototypes/2026-08-13-google-ai-studio-frontend-review.md)
  as provisional wireframe input only. Recreate them with fictional data; do not
  import the archive, its fixtures, dependencies, API layer, or architecture.

## Deliverables

- Pattern/reference register with evidence and applicability.
- Approved journeys, navigation model, and low-fidelity wireframes.
- Component/content-state inventory covering loading, empty, error, success, forbidden, expired, and retry states.
- Copy principles and terminology input for `SOUL.md`.
- Usability findings and prioritized corrections.
- Czech/German localization contract covering terminology ownership, fallback, formatting, translation completeness, and content expansion.
- WCAG-oriented acceptance checks for keyboard operation, visible focus, 200% zoom, 320px reflow, error identification/recovery, and non-color-only statuses.

## Exit gate

Jan and operator can complete the four critical synthetic journeys—employee creation, document/OCR review, assignment update, and A1 preparation—without facilitator intervention or ambiguous status language.

## Exclusions

No public-site design, final visual brand, copied competitor text/layout, or unsupported trust/compliance claims.
