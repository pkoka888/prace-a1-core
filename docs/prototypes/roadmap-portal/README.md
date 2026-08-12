# Roadmap and Jan Portal Visual Prototype

Open [`index.html`](index.html) in a browser. The prototype is self-contained, uses no external assets, and contains synthetic data only.

It demonstrates:

- three equivalent roadmap views: milestone journey, workstream board, and dependency map;
- a decision-status panel;
- Jan portal dashboard, OCR confirmation, worker/assignment, and A1 readiness screens;
- the confirmed simple OCR behavior: the logged-in uploader corrects or confirms values and the action is attributed to that user.
- the approved distinction between the sole real-data activation gate and non-blocking server-readiness work.

This is the seed of the living visual planning cockpit and remains derived,
synthetic presentation—not application architecture, production code, or an
independent source of status. Plan M will bind its planning views to a validated
repository catalog. Product implementation should reproduce accepted behavior
using Django templates and progressive enhancement rather than copying prototype
JavaScript into production.

Authoritative sources:

- [Roadmap](../../../roadmap.md)
- [PRD](../../../prd.md)
- [Decision register](../../decisions/decision-register.md)
- [Real-data policy](../../security/real-data-rules.md)
- [Plan M](../../../plans/2026-08-12-plan-m-visual-planning-cockpit.md)
