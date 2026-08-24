# Release 1A UX and Localization Contract

**State:** synthetic-default; operator validation required before real-data pilot

The four journeys use Czech-first task language: `Pracovníci`, `Dokumenty`,
`Přiřazení`, `A1 případy`, `Úkoly`, and `Historie`. Desktop presents document and
proposal side-by-side; mobile presents one field plus an explicit document-crop
action. Status is conveyed by text and icon, never color alone.

Every screen defines loading, empty, invalid, forbidden, expired, interrupted,
retry, success, and stale states where applicable. Destructive or irreversible
actions require an explicit consequence and confirmation. Errors appear in a
summary and beside the field; focus moves predictably without erasing input.

Acceptance requires keyboard completion, visible focus, semantic labels and
headings, programmatic error association, 200% zoom, 320 px reflow, adequate
contrast, and no pointer-only operation. Czech is the source locale. German
strings require completeness checks, expansion-safe layouts, locale-aware dates
and numbers, and a named terminology reviewer before partner activation.

```text
Přehled → Pracovník → Dokument → Kontrola OCR → Přiřazení → A1 připravenost
             ↘ chyba/zakázáno/obnova ↗             ↘ zastaralý balíček
```

This is Plan H input, not a final visual design or usability acceptance result.
