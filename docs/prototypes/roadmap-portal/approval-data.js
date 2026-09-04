window.APPROVAL_REGISTER = {
  "records": [
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "DEC-012 and every real-data activation and PLAN-INFRA recovery gate remain separate.",
      "approval_evidence": "Pavel approved ADR-001, Django and all listed recommended selections in the project conversation.",
      "approved_at": "2026-08-17",
      "approver": "Pavel",
      "checks": [
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-MFA",
          "id": "E-MFA",
          "label": "MFA bypass, recovery and session invalidation tests",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-TENANT",
          "id": "E-TENANT",
          "label": "Organization isolation across queryset, view, form, task, Admin and download",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-JOBS",
          "id": "E-JOBS",
          "label": "Retry, duplicate, timeout and crash recovery with one business effect",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-STORAGE",
          "id": "E-STORAGE",
          "label": "Quarantine, content validation and zero-byte unauthorized delivery",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-AUDIT",
          "id": "E-AUDIT",
          "label": "Required audit coverage with no sensitive payloads",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-A1",
          "id": "E-A1",
          "label": "Django-independent A1 boundary and deterministic stale-output behavior",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-DEPS",
          "id": "E-DEPS",
          "label": "Pinned supported versions, licenses and vulnerability review",
          "status": "passed"
        },
        {
          "evidence": "docs/architecture/adr-001-evidence/manifest.json#E-ROLLBACK",
          "id": "E-ROLLBACK",
          "label": "Synthetic deployment rollback and worker-version recovery",
          "status": "passed"
        }
      ],
      "choices": [
        {
          "approval": "approved",
          "deviation_reason": null,
          "id": "DEC-006",
          "label": "Aplikační architektura",
          "recommended": "Django 5.2 LTS modular monolith, Python 3.13, PostgreSQL, templates + targeted HTMX",
          "selected": "Django 5.2 LTS modular monolith, Python 3.13, PostgreSQL, templates + targeted HTMX"
        },
        {
          "approval": "approved",
          "deviation_reason": null,
          "id": "DEC-007",
          "label": "MFA",
          "recommended": "django-allauth[mfa] with mandatory TOTP for privileged roles",
          "selected": "django-allauth[mfa] with mandatory TOTP for privileged roles"
        },
        {
          "approval": "approved",
          "deviation_reason": null,
          "id": "DEC-008",
          "label": "Úlohy na pozadí",
          "recommended": "django-q2 with ORM broker and idempotent jobs",
          "selected": "django-q2 with ORM broker and idempotent jobs"
        },
        {
          "approval": "approved",
          "deviation_reason": null,
          "id": "DEC-009",
          "label": "Chráněné soubory",
          "recommended": "Encrypted filesystem, opaque keys and authorized Nginx X-Accel-Redirect delivery",
          "selected": "Encrypted filesystem, opaque keys and authorized Nginx X-Accel-Redirect delivery"
        },
        {
          "approval": "approved",
          "deviation_reason": null,
          "id": "DEC-010",
          "label": "Audit",
          "recommended": "Project-owned append-only AuditEvent; django-auditlog only as an optional diff helper",
          "selected": "Project-owned append-only AuditEvent; django-auditlog only as an optional diff helper"
        }
      ],
      "dependencies": [],
      "human_decision": "approved",
      "id": "ADR-001",
      "implementation_gate": "open",
      "implementation_gate_reason": null,
      "owner": "product engineering",
      "scope": "Schválení technického směru a vybraných komponent; není to potvrzení testů, povolení produkčního nasazení ani aktivace reálných dat.",
      "source": "docs/decisions/ADR-001-jan-portal-architecture.md",
      "title": "Architektura soukromého portálu Release 1A",
      "validation": "passed"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "Production migration, deployment and real-data activation remain separately gated.",
      "approval_evidence": "docs/release-1a/unblock-review-packet.md authorizes recommended reversible synthetic defaults; contract contains no invented operational fact.",
      "approved_at": "2026-08-17",
      "approver": "Pavel/Jan delegated defaults",
      "checks": [
        {
          "evidence": "docs/decisions/ADR-002-release-1a-data-and-transactions.md",
          "id": "O1A-CONTRACT",
          "label": "Minimum Release 1A data and transaction acceptance checks are explicit and backed by synthetic isolation/concurrency evidence",
          "status": "passed"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "ADR-001",
          "required_gate": "implementation-open"
        }
      ],
      "human_decision": "approved",
      "id": "ADR-002",
      "implementation_gate": "open",
      "implementation_gate_reason": null,
      "owner": "product engineering",
      "scope": "Reversible synthetic M2 schema, tenancy, transaction, audit, deletion, protected-file and migration contract only.",
      "source": "docs/decisions/ADR-002-release-1a-data-and-transactions.md",
      "title": "Release 1A data and transaction architecture",
      "validation": "passed"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "Observed journeys, named delegates, operational terminology and real-data approval remain pending.",
      "approval_evidence": "docs/release-1a/unblock-review-packet.md records trusted-default instruction and its limits.",
      "approved_at": "2026-08-17",
      "approver": "Jan delegated trust recorded by project user",
      "checks": [
        {
          "evidence": "docs/architecture/release-1a-catalog.json",
          "id": "JAN-DEFAULTS",
          "label": "Fields, Czech labels, roles, states, safe scan/download, assignment and manual-submission defaults are represented with exception-only remaining inputs",
          "status": "passed"
        }
      ],
      "choices": [],
      "dependencies": [],
      "human_decision": "approved",
      "id": "REV-001",
      "implementation_gate": "open",
      "implementation_gate_reason": null,
      "owner": "product owner",
      "scope": "Acceptance of repository-supported recommended defaults for the synthetic prototype; genuine operational facts remain explicit exceptions.",
      "source": "docs/release-1a/unblock-review-packet.md",
      "title": "Jan Phase-1 recommended defaults",
      "validation": "passed"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "Real-data portal activation requires separate authorization per real-data-rules.md and PLAN-REAL-DATA gates Sprint 1–4.",
      "approval_evidence": null,
      "approved_at": null,
      "approver": "Jan or Pavel as Jan's delegate",
      "checks": [
        {
          "evidence": "Release1aAcceptance record in db",
          "id": "REV-FRONTEND-1",
          "label": "All four Kontrola Release 1A sections marked DONE",
          "status": "pending"
        },
        {
          "evidence": "runtime/portal/synthetic-review/readiness.json",
          "id": "REV-FRONTEND-2",
          "label": "Automated readiness (verify_synthetic_review_readiness.sh) passed",
          "status": "pending"
        },
        {
          "evidence": "allauth MFA Authenticator table",
          "id": "REV-FRONTEND-3",
          "label": "Non-superuser reviewer accounts with real TOTP enrollment",
          "status": "pending"
        },
        {
          "evidence": "Release1aAcceptance record in db",
          "id": "REV-FRONTEND-4",
          "label": "Immutable Release1aAcceptance receipt generated",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "ADR-001",
          "required_gate": "implementation-open"
        },
        {
          "id": "ADR-002",
          "required_gate": "implementation-open"
        }
      ],
      "human_decision": "proposed",
      "id": "REV-002",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "J2 requires real quarantine, OCR bytes-from-storage, failure/retry, and protected download — not yet implemented. J4 requires immutable snapshots, generated previews, and staleness handling — not yet implemented. Jan should not mark those sections DONE.",
      "owner": "product owner",
      "scope": "J1–J4 workflow and frontend behavior observed via Kontrola Release 1A; synthetic data only; not production deployment, not real-data activation, not public recruitment site.",
      "source": "docs/operations/release-1a-review-environment.md",
      "title": "Release 1A frontend acceptance",
      "validation": "pending"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "Requires PLAN-REAL-DATA completion plus explicit operator/legal/sysadmin approval per real-data-rules.md.",
      "approval_evidence": null,
      "approved_at": null,
      "approver": "pending — operator + legal + sysadmin required",
      "checks": [
        {
          "evidence": "PLAN-REAL-DATA S1-P0-*",
          "id": "REV-DATA-S1",
          "label": "Sprint 1 P0 security and functional: capability enforcement, protected storage, OCR bytes-from-storage, immutable decisions, identity revisions",
          "status": "pending"
        },
        {
          "evidence": "PLAN-REAL-DATA S2-P1-*",
          "id": "REV-DATA-S2",
          "label": "Sprint 2 P1 DB/recovery: migrations, composite tenant FKs, idempotency, locking, audit/outbox",
          "status": "pending"
        },
        {
          "evidence": "PLAN-REAL-DATA S3-M3-*",
          "id": "REV-DATA-S3",
          "label": "Sprint 3 M3 completeness: IntakeItem, retention fields, translation coverage, WCAG 2.2 AA",
          "status": "pending"
        },
        {
          "evidence": "PLAN-REAL-DATA S4-M4-*",
          "id": "REV-DATA-S4",
          "label": "Sprint 4 M4/M5 gates: A1 snapshots/artifacts, backup/restore, REV-002 approved",
          "status": "pending"
        },
        {
          "evidence": "Signed acknowledgment record",
          "id": "REV-DATA-OPERATOR",
          "label": "Operator trained; incident procedures and access protocols signed",
          "status": "pending"
        },
        {
          "evidence": "Legal approval record",
          "id": "REV-DATA-LEGAL",
          "label": "Legal counsel reviewed and approved data processing basis",
          "status": "pending"
        },
        {
          "evidence": "Restore test evidence",
          "id": "REV-DATA-BACKUP",
          "label": "Encrypted backup verified: pg_dump + protected files + manifest + off-host copy + isolated restore",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "REV-002",
          "required_gate": "implementation-open"
        },
        {
          "id": "ADR-001",
          "required_gate": "implementation-open"
        },
        {
          "id": "ADR-002",
          "required_gate": "implementation-open"
        }
      ],
      "human_decision": "proposed",
      "id": "REV-003",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "Sprint 1 (P0 security), Sprint 2 (P1 DB/recovery), Sprint 3 (M3 completeness), Sprint 4 (M4/M5 gates) all required to pass before activation. See PLAN-REAL-DATA.",
      "owner": "product engineering + product owner + legal + sysadmin",
      "scope": "Authorizes real PII upload, OCR processing, document storage, and worker identity management in the portal. Does not authorize public deployment, GitLab CI, or production infrastructure changes. Separate explicit approval required from operator, legal counsel, and sysadmin.",
      "source": "plans/PLAN-REAL-DATA.md",
      "title": "Real-data portal activation",
      "validation": "pending"
    }
  ],
  "schema_version": "1.0",
  "updated_at": "2026-09-04T12:00:00+02:00"
};
