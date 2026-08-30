window.PLANNING_CATALOG = {
  "decisions": [
    {
      "approver": "Pavel",
      "date": "2026-08-12",
      "id": "DEC-001",
      "state": "accepted",
      "status": "accepted",
      "title": "Persistent project root"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-12",
      "id": "DEC-002",
      "state": "accepted",
      "status": "accepted",
      "title": "Jan-first private portal is Release 1A"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-12",
      "id": "DEC-003",
      "state": "accepted",
      "status": "accepted",
      "title": "Stable worker plus effective-dated activity profiles"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-12",
      "id": "DEC-004",
      "state": "accepted",
      "status": "accepted",
      "title": "OCR values require human confirmation; Jan/Pavel/delegated admins have broad 1A workflow authority"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-12",
      "id": "DEC-005",
      "state": "accepted",
      "status": "accepted",
      "title": "Assignment overlap warns instead of universally blocking"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-17",
      "id": "DEC-006",
      "state": "accepted",
      "status": "accepted",
      "title": "Django modular-monolith baseline"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-17",
      "id": "DEC-007",
      "state": "accepted",
      "status": "accepted",
      "title": "django-allauth[mfa] with mandatory privileged-role TOTP"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-17",
      "id": "DEC-008",
      "state": "accepted",
      "status": "accepted",
      "title": "django-q2 ORM-broker background queue"
    },
    {
      "approver": "Pavel/sysadmin",
      "date": "2026-08-17",
      "id": "DEC-009",
      "state": "accepted",
      "status": "accepted",
      "title": "Encrypted filesystem with authorized Nginx internal delivery"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-17",
      "id": "DEC-010",
      "state": "accepted",
      "status": "accepted",
      "title": "Project-owned append-only AuditEvent boundary"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-12",
      "id": "DEC-011",
      "state": "not-applicable",
      "status": "accepted",
      "title": "Separate public frontend"
    },
    {
      "approver": "Pavel",
      "date": null,
      "id": "DEC-012",
      "state": "prototype-required",
      "status": "active",
      "title": "Activate new real-data portal use"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-13",
      "id": "DEC-013",
      "state": "accepted",
      "status": "accepted",
      "title": "Require the 15 GiB/15% capacity gate and tested encrypted backup/restore before real-data activation"
    },
    {
      "approver": "Pavel",
      "date": "2026-08-13",
      "id": "DEC-014",
      "state": "accepted",
      "status": "accepted",
      "title": "Confirm published sanitized checkpoint c01aa2b as the approved repository baseline"
    },
    {
      "approver": "accounting-specialist (role required for acceptance)",
      "date": null,
      "id": "DEC-015",
      "state": "prototype-required",
      "status": "active",
      "title": "Accounting-specialist acceptance of invoice ground truth and AD implementation boundary"
    },
    {
      "approver": "Pavel",
      "date": null,
      "id": "DEC-016",
      "state": "proposed-default",
      "status": "active",
      "title": "GitLab secondary backup and CI activation with GitHub authoritative"
    }
  ],
  "generated_or_reviewed_at": "2026-08-30T00:00:00Z",
  "historical_or_superseded": [
    {
      "id": "PLAN-HISTORY",
      "status": "historical",
      "successor": "PLAN-INFRA"
    }
  ],
  "lanes": [
    {
      "deps": [
        "PLAN-A1"
      ],
      "id": "a1-lane",
      "status": "planned",
      "title": "Separate A1 operations"
    },
    {
      "deps": [
        "PLAN-INFRA",
        "PLAN-WORKERS"
      ],
      "id": "critical-path",
      "status": "active",
      "title": "Release 1A critical path"
    },
    {
      "deps": [
        "PLAN-LEGAL",
        "PLAN-INFRA",
        "PLAN-INVOICE"
      ],
      "id": "parallel",
      "status": "active",
      "title": "Parallel non-blocking work"
    }
  ],
  "milestones": [
    {
      "id": "M0",
      "status": "active",
      "title": "M0: Organize a coherent foundation"
    },
    {
      "id": "M1A",
      "status": "active",
      "title": "M1A: Release 1A implementation readiness"
    },
    {
      "id": "M1B",
      "status": "planned",
      "title": "M1B: Broader platform design"
    },
    {
      "id": "M2",
      "status": "planned",
      "title": "M2: Build the shared synthetic foundation"
    },
    {
      "id": "M3",
      "status": "planned",
      "title": "M3: Employee, document, OCR, and assignment workflow"
    },
    {
      "id": "M4",
      "status": "planned",
      "title": "M4: A1 preparation"
    },
    {
      "id": "M5",
      "status": "planned",
      "title": "M5: Controlled real-data pilot"
    },
    {
      "id": "M6",
      "status": "planned",
      "title": "M6: Later releases and public growth"
    }
  ],
  "missing_gate_items": [
    "DEC-001",
    "DEC-002",
    "DEC-003",
    "DEC-004",
    "DEC-005",
    "DEC-006",
    "DEC-007",
    "DEC-008",
    "DEC-009",
    "DEC-010",
    "DEC-011",
    "DEC-012",
    "DEC-013",
    "DEC-014",
    "DEC-015",
    "DEC-016",
    "M0",
    "M1A",
    "M1B",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "PLAN-HISTORY",
    "a1-lane",
    "critical-path",
    "parallel"
  ],
  "plans": [
    {
      "decision_state": "prototype-required",
      "executable": false,
      "id": "PLAN-A1",
      "milestone": "A1 operations",
      "owner": "primary A1 production agent; operator approval required for regeneration",
      "sources": [
        "plans/PLAN-A1.md",
        "AGENTS.md"
      ],
      "status": "active",
      "title": "A1 production, repository history, and privacy baseline"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "PLAN-FREE-MODEL",
      "milestone": "M0–M1A",
      "owner": "primary agent; Codex integrates and accepts",
      "sources": [
        "plans/PLAN-FREE-MODEL.md",
        "config/free-model-eval/policy.json",
        "docs/research/2026-08-15-af2-free-model-trace-review-report.md"
      ],
      "status": "active",
      "title": "Bounded Codex-led free-model evaluation, trace repair, and capsule isolation"
    },
    {
      "decision_state": "not-applicable",
      "executable": false,
      "id": "PLAN-HISTORY",
      "milestone": "historical",
      "owner": "primary agent (maintenance only)",
      "sources": [
        "plans/PLAN-HISTORY.md",
        "plans/INDEX.md",
        "roadmap.md"
      ],
      "status": "historical",
      "title": "Archived superseded and historical plans"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "PLAN-INFRA",
      "milestone": "M0–M2",
      "owner": "product engineering + primary agent + server sysadmin",
      "sources": [
        "plans/PLAN-INFRA.md",
        "AGENTS.md"
      ],
      "status": "active",
      "title": "Architecture, operating model, planning cockpit, prototype, and infrastructure foundation"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "PLAN-INVOICE",
      "milestone": "M1B+",
      "owner": "product engineering + Czech/German accounting specialists",
      "sources": [
        "plans/PLAN-INVOICE.md",
        ".opencode/skills/market-research-evidence/SKILL.md",
        "docs/decisions/decision-register.md",
        "AGENTS.md"
      ],
      "status": "active",
      "title": "Accounting automation research and invoice ingestion foundation"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "PLAN-LEGAL",
      "milestone": "M1A–M6",
      "owner": "product owner + legal",
      "sources": [
        "plans/PLAN-LEGAL.md",
        "docs/security/real-data-rules.md",
        "AGENTS.md"
      ],
      "status": "active",
      "title": "Data protection, legal, market, and business validation"
    },
    {
      "decision_state": "accepted",
      "executable": true,
      "id": "PLAN-WORKERS",
      "milestone": "M1A–M3",
      "owner": "product owner + product design + product engineering",
      "sources": [
        "plans/PLAN-WORKERS.md",
        "AGENTS.md",
        "roadmap.md",
        "docs/decisions/2026-08-12-jan-release-1-solution-brief.md"
      ],
      "status": "active",
      "title": "Worker, role, data, UX, and OCR workflow discovery"
    }
  ],
  "release_1a_path": [
    "PLAN-INFRA",
    "PLAN-WORKERS"
  ],
  "schema_version": "1.0"
};
