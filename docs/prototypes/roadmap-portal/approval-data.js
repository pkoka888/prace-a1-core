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
      "activation_gate": "not-applicable",
      "activation_gate_reason": null,
      "approval_evidence": null,
      "approved_at": null,
      "approver": "pending — engineering gate only",
      "checks": [
        {
          "evidence": "tests/security/test_capabilities.py",
          "id": "ENG-AUTH",
          "label": "Capability matrix enforced in every view and service action; default-deny for organization/record/role/action",
          "status": "pending"
        },
        {
          "evidence": "tests/architecture/test_protected_storage.py",
          "id": "ENG-J2-STORAGE",
          "label": "Django Storage abstraction for quarantine/protected documents; authorized download returns bytes; unauthorized returns zero bytes",
          "status": "pending"
        },
        {
          "evidence": "tests/portal/test_intake_scanner.py",
          "id": "ENG-J2-SCANNER",
          "label": "Scanner adapter fail-closed: unavailable/error blocks processing; not advisory",
          "status": "pending"
        },
        {
          "evidence": "tests/portal/test_ocr_bytes_from_storage.py",
          "id": "ENG-J2-OCR",
          "label": "OCR reads bytes from storage.open(opaque_key); failures visible and retryable; no silent swallowing",
          "status": "pending"
        },
        {
          "evidence": "tests/portal/test_field_decision_immutability.py",
          "id": "ENG-J2-IMMUTABLE",
          "label": "FieldProposal immutable from creation; FieldDecision append-only; one final decision per proposal; zero-field confirmation rejected",
          "status": "pending"
        },
        {
          "evidence": "tests/portal/test_identity_revision.py",
          "id": "ENG-J2-REVISION",
          "label": "WorkerIdentityRevision created on confirmation; readiness reads authoritative revision",
          "status": "pending"
        },
        {
          "evidence": "tests/portal/test_concurrent_edits.py",
          "id": "ENG-J3-CONCURRENCY",
          "label": "Optimistic locking on Worker and Assignment; two concurrent edits yield one success + one stale response",
          "status": "pending"
        },
        {
          "evidence": "tests/a1/test_a1_snapshots.py",
          "id": "ENG-J4-SNAPSHOT",
          "label": "A1InputSnapshot and A1Artifact created per A1 case; bytes stored in protected storage",
          "status": "pending"
        },
        {
          "evidence": "tests/a1/test_a1_quality_gate.py",
          "id": "ENG-J4-PREVIEW",
          "label": "Deterministic A1 generation with fresh all-page preview QA; human visual validation mandatory",
          "status": "pending"
        },
        {
          "evidence": "portal/release1a/services.py A1 state machine",
          "id": "ENG-J4-STATE",
          "label": "A1 internal states: draft/ready-for-review/generated/QA-passed/approved/stale/failed; source revision marks artifacts stale; issued/submitted never overwritten",
          "status": "pending"
        },
        {
          "evidence": "runtime/portal/synthetic-review/axe.json",
          "id": "ENG-A11Y",
          "label": "WCAG 2.2 AA: axe-core automated pass; manual keyboard/focus/zoom/reflow/screen-reader checks",
          "status": "pending"
        },
        {
          "evidence": "tests/migrations/test_executor_transitions.py",
          "id": "ENG-MIGRATION",
          "label": "Forward-only migrations after 0007; MigrationExecutor transitions from 0005/0006/0007 on PostgreSQL",
          "status": "pending"
        },
        {
          "evidence": "CI run or local pytest run",
          "id": "ENG-BUILD",
          "label": "All pytest tests pass; manage.py check clean; makemigrations --check clean; git tree clean at approval time",
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
      "id": "ENG-001",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "Engineering prerequisites (authorization, J2 storage/OCR, J3 concurrency, J4 artifacts, accessibility, migrations, build integrity) not yet implemented",
      "owner": "product engineering",
      "scope": "Engineering prerequisites for synthetic J1-J4 review: authorization/capability enforcement, J2 storage/OCR/quarantine/scanner, J3 concurrency/optimistic-locking, J4 A1 snapshots/artifacts/staleness, accessibility WCAG 2.2 AA, migrations, build integrity. Must pass before runtime approval button is enabled.",
      "source": "docs/operations/release-1a-review-environment.md",
      "title": "Engineering readiness for synthetic J1–J4 review",
      "validation": "pending"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "Real-data portal activation requires separate authorization per real-data-rules.md and PLAN-REAL-DATA.",
      "approval_evidence": null,
      "approved_at": null,
      "approver": "Jan or Pavel as Jan's explicit delegate",
      "checks": [
        {
          "evidence": "Release1aAcceptance record in db",
          "id": "REV-FRONTEND-1",
          "label": "All four Kontrola Release 1A sections marked DONE after ENG-001 is open",
          "status": "pending"
        },
        {
          "evidence": "runtime/portal/synthetic-review/readiness.json",
          "id": "REV-FRONTEND-2",
          "label": "Automated readiness passed (verify_synthetic_review_readiness.sh)",
          "status": "pending"
        },
        {
          "evidence": "allauth MFA Authenticator table + meeting notes",
          "id": "REV-FRONTEND-3",
          "label": "Non-superuser reviewer accounts with real TOTP enrollment; Jan or explicitly delegated Pavel performed J1–J4",
          "status": "pending"
        },
        {
          "evidence": "Release1aAcceptance record in db",
          "id": "REV-FRONTEND-4",
          "label": "Immutable Release1aAcceptance receipt generated with correct hashes (HEAD, build ID, scope, approvals)",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "ENG-001",
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
      "id": "REV-002",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "ENG-001 must open first. Runtime approval button depends on ENG-001, not REV-002.",
      "owner": "product owner",
      "scope": "J1–J4 workflow and frontend behavior observed via Kontrola Release 1A; synthetic data only; not production deployment, not real-data activation, not public recruitment site. Human_decision becomes approved only after the acceptance receipt is created.",
      "source": "docs/operations/release-1a-review-environment.md",
      "title": "Release 1A frontend acceptance",
      "validation": "pending"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "OPS-001 must be approved before real-data activation",
      "approval_evidence": null,
      "approved_at": null,
      "approver": "pending — operator approval required",
      "checks": [
        {
          "evidence": "docs/operations/operator-workflow.md",
          "id": "OPS-WORKFLOW",
          "label": "Operator workflow documented for all intake, OCR, worker, assignment, and A1 preparation tasks",
          "status": "pending"
        },
        {
          "evidence": "docs/architecture/release-1a-catalog.json roles section",
          "id": "OPS-ROLES",
          "label": "Named roles and delegated users defined: organization admin, final approver, operator record preparer, privacy administrator, system worker (no interactive account)",
          "status": "pending"
        },
        {
          "evidence": "docs/training/operator-training.md",
          "id": "OPS-TRAINING",
          "label": "Training materials complete and reviewed by Jan",
          "status": "pending"
        },
        {
          "evidence": "docs/security/incident-response.md",
          "id": "OPS-INCIDENT",
          "label": "Incident response procedures documented and acknowledged",
          "status": "pending"
        },
        {
          "evidence": "docs/security/real-data-rules.md",
          "id": "OPS-RETENTION",
          "label": "Retention and deletion procedures documented; legal hold handling defined",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "REV-002",
          "required_gate": "approved"
        },
        {
          "id": "ADR-001",
          "required_gate": "implementation-open"
        }
      ],
      "human_decision": "proposed",
      "id": "OPS-001",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "Operator workflow, role definitions, training materials, and incident procedures not yet documented or signed",
      "owner": "product owner + operator",
      "scope": "Operator documentation: workflow for document intake, OCR confirmation, worker management, A1 preparation; named roles and delegated users; training materials; incident response procedures; retention and deletion procedures.",
      "source": "plans/PLAN-REAL-DATA.md",
      "title": "Operator workflow, roles, training, and incident procedures",
      "validation": "pending"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "LEG-001 must be approved before real-data activation",
      "approval_evidence": null,
      "approved_at": null,
      "approver": "pending — legal counsel approval required",
      "checks": [
        {
          "evidence": "docs/legal/purpose-legal-basis.md",
          "id": "LEG-PURPOSE",
          "label": "Purpose limitation and legal basis documented per document type; no global consent as default",
          "status": "pending"
        },
        {
          "evidence": "docs/legal/identity-document-review.md",
          "id": "LEG-IDDOC",
          "label": "Identity document processing reviewed: PAuswG §20(2) copy recognition, BDSG §26 employment-relationship necessity",
          "status": "pending"
        },
        {
          "evidence": "docs/architecture/release-1a-catalog.json document section",
          "id": "LEG-REDACTION",
          "label": "Selective verification/redaction supported instead of mandatory full OP/ZP scan retention",
          "status": "pending"
        },
        {
          "evidence": "docs/legal/data-subject-rights.md",
          "id": "LEG-DSR",
          "label": "Data subject rights procedures documented (access, correction, deletion)",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "REV-002",
          "required_gate": "approved"
        },
        {
          "id": "ADR-001",
          "required_gate": "implementation-open"
        }
      ],
      "human_decision": "proposed",
      "id": "LEG-001",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "Legal review of purpose/legal-basis documentation and identity-document processing not yet completed",
      "owner": "legal",
      "scope": "Legal review: purpose limitation per record type, applicable lawful basis (not blanket consent), identity document processing under PAuswG/BDSG §26, selective verification/redaction preference, retention minimums, data subject rights procedures.",
      "source": "plans/PLAN-REAL-DATA.md",
      "title": "Purpose, legal basis, and identity-document processing review",
      "validation": "pending"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "INF-001 must be approved before real-data activation",
      "approval_evidence": null,
      "approved_at": null,
      "approver": "pending — sysadmin approval required",
      "checks": [
        {
          "evidence": "sysadmin encryption verification report",
          "id": "INF-ENCRYPT",
          "label": "Filesystem encryption-at-rest enabled and verified on all protected storage paths",
          "status": "pending"
        },
        {
          "evidence": "docs/operations/backup-manifest.json",
          "id": "INF-BACKUP",
          "label": "Encrypted pg_dump created; protected file snapshots created; manifest with integrity hashes generated",
          "status": "pending"
        },
        {
          "evidence": "off-host copy verification record",
          "id": "INF-OFFHOST",
          "label": "Off-host backup copy confirmed and integrity-verified",
          "status": "pending"
        },
        {
          "evidence": "docs/operations/restore-test-evidence.md",
          "id": "INF-RESTORE",
          "label": "Isolated application-level restore tested; hash matches pg_dump output; all artifacts verified",
          "status": "pending"
        },
        {
          "evidence": "docs/operations/monitoring-config.md",
          "id": "INF-MONITOR",
          "label": "Monitoring configured for portal availability and protected storage integrity",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "REV-002",
          "required_gate": "approved"
        },
        {
          "id": "ADR-001",
          "required_gate": "implementation-open"
        }
      ],
      "human_decision": "proposed",
      "id": "INF-001",
      "implementation_gate": "blocked",
      "implementation_gate_reason": "Infrastructure evidence (encryption, backup, restore) not yet verified",
      "owner": "sysadmin",
      "scope": "Infrastructure evidence: filesystem encryption-at-rest verified per DEC-009, encrypted pg_dump with reviewed key, protected file snapshots, manifest with integrity hashes, off-host copy confirmed, monitoring configured, isolated application-level restore tested.",
      "source": "plans/PLAN-REAL-DATA.md",
      "title": "Infrastructure: encryption, backup, off-host copy, monitoring, and isolated restore",
      "validation": "pending"
    },
    {
      "activation_gate": "blocked",
      "activation_gate_reason": "Requires REV-003 human_decision: approved plus all prerequisite approvals and Sprint 1–4 gates",
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
          "label": "Sprint 4 M4/M5 gates: A1 snapshots/artifacts, backup/restore, OPS-001, LEG-001, INF-001 approved",
          "status": "pending"
        }
      ],
      "choices": [],
      "dependencies": [
        {
          "id": "REV-002",
          "required_gate": "approved"
        },
        {
          "id": "OPS-001",
          "required_gate": "approved"
        },
        {
          "id": "LEG-001",
          "required_gate": "approved"
        },
        {
          "id": "INF-001",
          "required_gate": "approved"
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
      "implementation_gate_reason": "REV-002, OPS-001, LEG-001, INF-001, and Sprint 1–4 implementation all required before activation",
      "owner": "product engineering + product owner + legal + sysadmin",
      "scope": "Authorizes real PII upload, OCR processing, document storage, and worker identity management in the portal. Does not authorize public deployment, GitLab CI, or production infrastructure changes. Separate explicit approval required from operator, legal counsel, and sysadmin.",
      "source": "plans/PLAN-REAL-DATA.md",
      "title": "Real-data portal activation",
      "validation": "pending"
    }
  ],
  "schema_version": "1.0",
  "updated_at": "2026-09-04T18:00:00+02:00"
};
