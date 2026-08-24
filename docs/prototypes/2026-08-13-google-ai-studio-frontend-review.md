# Google AI Studio Frontend Prototype — Architecture and Import Review

**Status:** Provisional design evidence; rejected for direct import
**Review date:** 2026-08-13
**Owners:** product design and product engineering
**Related plans:** Plan E architecture proofs and Plan H UX/UI research

## Reviewed artifact

The review covered the untracked Google AI Studio export
`práce-v-německu.zip`, SHA-256
`5541ab9748d7edd4c50a979156765997e7a7b4fadb42d2333c9b7e6a2dca52c6`.
The archive remains local review input and is not an authoritative or tracked
project artifact. Do not publish or import it without a new review against the
same hash.

The export was inspected in disposable non-PII directories, which were removed
after review. No archive content was copied into the project.

## Decision input

The prototype is useful as synthetic visual evidence for the operator shell,
status presentation, provenance cards, OCR review layout, assignment-conflict
warning, and A1 readiness/staleness patterns. Those patterns may inform Plan H
wireframes and usability review after sanitization.

The export is **not accepted as production code or an architecture decision**.
ADR-001 must still select either the planned Django templates/HTMX approach or a
Next.js frontend with a separately specified Django API. The repository must not
silently maintain both implementations.

## Direct-import blockers

- The fixtures contain a real operator identity and email, violating the
  synthetic-only rule for prototypes and external-model output.
- Google AI/Gemini metadata, API-key instructions, branding, and dependencies are
  present even though the portal requires no Gemini runtime.
- Firebase, Tailwind-related, animation, and other unused dependencies conflict
  with the requested minimal Bootstrap-oriented implementation.
- Declared Next.js, React, ESLint, and lockfile/install behavior is inconsistent;
  an isolated dependency install did not complete reproducibly.
- ESLint failures are configured to be ignored during production builds.
- Required detail/review routes, tests, environment validation, error/loading
  boundaries, security headers, and production deployment artifacts are missing.
- Nearly every page and shared component is a Client Component rather than using
  a Server-Components-first boundary.
- The API layer is an in-memory fixture adapter without the required Django HTTP,
  CSRF, response validation, concurrency, authorization, and error contracts.
- Czech localization and metadata are incomplete, and several unapproved domain
  fields are prematurely encoded as frontend types.

## Reusable evidence

Reimplement selectively after the relevant Plan E/H/N/O decisions rather than
copying the archive wholesale:

- restrained Bootstrap-oriented design tokens;
- application navigation and work-queue dashboard concepts;
- visible status, warning, blocker, and stale-data treatments;
- field provenance presentation;
- abstract document/OCR comparison layout;
- A1 readiness checklist and official-certificate distinction;
- responsive operator-workflow concepts.

All reused examples must be recreated with clearly fictional data. No original
fixture, dependency graph, metadata, API adapter, environment file, or deployment
configuration is approved for reuse.

## Required next gate

1. Complete Plan E proofs and record ADR-001 before portal scaffolding.
2. If Next.js is selected, define a versioned Django API/auth/session/CSRF and
   protected-download boundary plus deployment/version-skew evidence.
3. Validate sanitized visual variants through Plan H with synthetic fixtures.
4. Freeze the Release 1A domain and transaction contracts through Plans N/O
   before turning provisional frontend types into production interfaces.
5. Import only reviewed, minimal, test-covered components into a clean accepted
   scaffold; do not extract the archive over the repository.

