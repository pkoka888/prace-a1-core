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
      "date": null,
      "id": "DEC-006",
      "state": "proposed-default",
      "status": "active",
      "title": "Django modular-monolith baseline"
    },
    {
      "approver": "Pavel",
      "date": null,
      "id": "DEC-007",
      "state": "prototype-required",
      "status": "active",
      "title": "MFA package"
    },
    {
      "approver": "Pavel",
      "date": null,
      "id": "DEC-008",
      "state": "prototype-required",
      "status": "active",
      "title": "Background queue package"
    },
    {
      "approver": "Pavel/sysadmin",
      "date": null,
      "id": "DEC-009",
      "state": "prototype-required",
      "status": "active",
      "title": "Protected storage implementation"
    },
    {
      "approver": "Pavel",
      "date": null,
      "id": "DEC-010",
      "state": "prototype-required",
      "status": "active",
      "title": "Audit package and project-owned event boundary"
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
      "state": "awaiting-pavel",
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
  "generated_or_reviewed_at": "2026-08-13T13:28:00Z",
  "historical_or_superseded": [
    {
      "id": "B",
      "status": "historical",
      "successor": "L"
    },
    {
      "id": "C",
      "status": "historical",
      "successor": "L"
    },
    {
      "id": "D",
      "status": "superseded",
      "successor": "N"
    },
    {
      "id": "I",
      "status": "superseded",
      "successor": "H"
    },
    {
      "id": "consolidated-roadmap",
      "status": "historical",
      "successor": "M0"
    }
  ],
  "lanes": [
    {
      "deps": [
        "R"
      ],
      "id": "a1-lane",
      "status": "planned",
      "title": "Separate A1 operations"
    },
    {
      "deps": [
        "L",
        "M",
        "F",
        "E",
        "N",
        "O",
        "H"
      ],
      "id": "critical-path",
      "status": "active",
      "title": "Release 1A critical path"
    },
    {
      "deps": [
        "G",
        "J",
        "K",
        "P",
        "AC"
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
    "B",
    "C",
    "D",
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
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "M",
    "M0",
    "M1A",
    "M1B",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "a1-lane",
    "consolidated-roadmap",
    "critical-path",
    "parallel"
  ],
  "plans": [
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "AC",
      "milestone": "M1B+",
      "owner": "product engineering + Czech/German accounting specialists",
      "sources": [
        "plans/2026-08-13-plan-ac-accounting-automation-research.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan AC — Accounting and Invoice Automation Research"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "AD",
      "milestone": "M1B",
      "owner": "product engineering + Czech/German accounting specialists",
      "sources": [
        "plans/2026-08-14-plan-ad-invoice-ingestion-foundation.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan AD — Invoice Ingestion and Reviewed Export Foundation"
    },
    {
      "decision_state": "proposed-default",
      "executable": true,
      "id": "AE",
      "milestone": "M0",
      "owner": "primary agent",
      "sources": [
        "plans/2026-08-14-plan-ae-repository-workflow-dual-remotes-ci-automation.md",
        "change-packages.yml",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan AE — Repository Workflow, Dual Remotes, and CI Automation"
    },
    {
      "decision_state": "not-applicable",
      "executable": false,
      "id": "B",
      "milestone": "historical",
      "owner": "primary agent",
      "sources": [
        "plans/2026-08-11-plan-b-opencode-cleanup-workflows.md",
        "plans/INDEX.md"
      ],
      "status": "historical",
      "title": "Plan B — OpenCode Cleanup Workflows (historical)"
    },
    {
      "decision_state": "not-applicable",
      "executable": false,
      "id": "C",
      "milestone": "historical",
      "owner": "primary agent",
      "sources": [
        "plans/2026-08-11-plan-c-opencode-research.md",
        "plans/INDEX.md"
      ],
      "status": "historical",
      "title": "Plan C — OpenCode Research (historical)"
    },
    {
      "decision_state": "superseded",
      "executable": false,
      "id": "D",
      "milestone": "M1",
      "owner": "product owner",
      "sources": [
        "plans/2026-08-12-plan-d-product-research-and-deployment.md",
        "plans/INDEX.md"
      ],
      "status": "superseded",
      "title": "Plan D — Product Research and Deployment (superseded)"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "E",
      "milestone": "M1A",
      "owner": "product engineering",
      "sources": [
        "plans/2026-08-12-plan-e-architecture-proofs-and-adr.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan E — Architecture Proofs and ADR-001"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "F",
      "milestone": "M1A",
      "owner": "product owner",
      "sources": [
        "plans/2026-08-12-plan-f-jan-workflow-discovery.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan F — Jan Workflow Discovery"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "G",
      "milestone": "M1B/M6",
      "owner": "product research",
      "sources": [
        "plans/2026-08-12-plan-g-german-market-and-competitors.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan G — German Market and Competitor Research"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "H",
      "milestone": "M1A–M3",
      "owner": "product design",
      "sources": [
        "plans/2026-08-12-plan-h-ux-ui-and-copy-research.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan H — UX, UI, and Copy Research"
    },
    {
      "decision_state": "superseded",
      "executable": false,
      "id": "I",
      "milestone": "M1",
      "owner": "product owner",
      "sources": [
        "plans/2026-08-12-plan-i-marketing-and-business-validation.md",
        "plans/INDEX.md"
      ],
      "status": "superseded",
      "title": "Plan I — Marketing and Business Validation (superseded)"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "J",
      "milestone": "M1A–M5",
      "owner": "product owner + legal",
      "sources": [
        "plans/2026-08-12-plan-j-data-protection-and-legal.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan J — Data Protection and Legal"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "K",
      "milestone": "M0–M5",
      "owner": "server sysadmin; product engineering verifies",
      "sources": [
        "plans/2026-08-12-plan-k-server62-readiness.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan K — server62 Production Readiness"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "L",
      "milestone": "M0–M1",
      "owner": "primary agent with Pavel approval for publication",
      "sources": [
        "plans/2026-08-12-plan-l-agent-operating-model.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan L — Agent, Skill, Workflow, and Git Operating Model"
    },
    {
      "decision_state": "prototype-required",
      "executable": false,
      "id": "M",
      "milestone": "M1 and continuous",
      "owner": "product design + engineering",
      "sources": [
        "plans/2026-08-12-plan-m-visual-planning-cockpit.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md",
        "planning/catalog.json"
      ],
      "status": "active",
      "title": "Plan M — Generated Visual Planning Cockpit"
    },
    {
      "decision_state": "prototype-required",
      "executable": false,
      "id": "N",
      "milestone": "M1A–M1B",
      "owner": "product owner + domain research",
      "sources": [
        "plans/2026-08-12-plan-n-full-platform-role-and-data-discovery.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "planned",
      "title": "Plan N — Release 1A Role and Data Discovery"
    },
    {
      "decision_state": "prototype-required",
      "executable": false,
      "id": "O",
      "milestone": "M1A–M1B",
      "owner": "product engineering",
      "sources": [
        "plans/2026-08-12-plan-o-database-and-transaction-architecture.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "planned",
      "title": "Plan O — Release 1A Database and Transaction Architecture"
    },
    {
      "decision_state": "prototype-required",
      "executable": true,
      "id": "P",
      "milestone": "M1B",
      "owner": "product engineering + payroll specialists",
      "sources": [
        "plans/2026-08-12-plan-p-payroll-and-finance-architecture.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "active",
      "title": "Plan P — Payroll and Finance Architecture"
    },
    {
      "decision_state": "accepted",
      "executable": false,
      "id": "Q",
      "milestone": "M0",
      "owner": "primary agent; Pavel approves exact remote/destructive actions",
      "sources": [
        "plans/2026-08-12-plan-q-repository-history-reference-privacy.md",
        "docs/decisions/decision-register.md",
        "plans/INDEX.md"
      ],
      "status": "accepted",
      "title": "Plan Q — Repository History, Reference, and Privacy Remediation"
    },
    {
      "decision_state": "prototype-required",
      "executable": false,
      "id": "R",
      "milestone": "A1 operations",
      "owner": "primary A1 production agent",
      "sources": [
        "plans/2026-08-12-plan-r-a1-production-stabilization.md",
        "AGENTS.md",
        "roadmap.md",
        "plans/INDEX.md"
      ],
      "status": "blocked",
      "title": "Plan R — A1 Production Stabilization"
    },
    {
      "decision_state": "not-applicable",
      "executable": false,
      "id": "consolidated-roadmap",
      "milestone": "historical",
      "owner": "primary agent",
      "sources": [
        "plans/2026-08-11-consolidated-roadmap.md",
        "roadmap.md"
      ],
      "status": "historical",
      "title": "2026-08-11 Consolidated Roadmap (historical)"
    }
  ],
  "release_1a_path": [
    "L",
    "M",
    "F",
    "E",
    "N",
    "O",
    "H"
  ],
  "schema_version": "1.0"
};
