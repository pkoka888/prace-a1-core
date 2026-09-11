#!/usr/bin/env python3
"""Deterministic planning validator for the authorized repository.

Read-only by default. Validates planning/catalog.json against its JSON Schema
and its enumerated named governance checks (see ``build_checks``; the validator
is the authoritative source of the live check count, surfaced via ``--json``).
Uses --root for every filesystem lookup.

Exit contract:
  0  proven pass (all checks passed)
  1  confirmed validation failure (a check failed)
  2  environmental / unproven (jsonschema missing, schema file missing,
     git unavailable for the staged-path check, etc.)

The validator never prints sensitive staged content; it reports only the
matched forbidden token and a count.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------
VALID_KINDS = {"plan", "decision", "roadmap_milestone", "lane", "checkpoint"}
VALID_STATUSES = {
    "planned", "active", "blocked", "awaiting-review", "accepted",
    "completed", "superseded", "historical", "archived",
}
VALID_DECISION_STATES = {
    "proposed-default", "variant-selection-required", "prototype-required",
    "awaiting-pavel", "awaiting-jan", "accepted", "rejected", "superseded",
    "not-applicable",
}
VALID_EVIDENCE_STATES = {
    "none", "provisional", "synthetic-tested", "primary-source-verified",
    "operator-verified", "specialist-verified",
}
VALID_GATES = {
    "may-begin", "may-be-accepted", "may-be-implemented", "activation-gate",
    "specialist-gate", "separate-exact-approval", "evidence-only",
}
# Gates that block acceptance/implementation. "evidence-only" edges are
# explicitly excluded from cycle detection.
BLOCKING_GATES = VALID_GATES - {"evidence-only"}

# Exact required catalog IDs (34 — top-level set as of 2026-08-30).
# Subordinate work-package plans (OCR-SHARED-CORE-LOCAL, FREE-VISION-PROVIDER-SAFETY,
# A1-EVIDENCE-STATUS-REPAIR) are registered in the catalog and linked from parent
# plans, but are NOT top-level ID set members and do not appear in REQUIRED_IDS.
# They are validated through parent-plan source_links and the index entry.
REQUIRED_IDS = [
    # Milestones
    "M0", "M1A", "M1B", "M2", "M3", "M4", "M5", "M6",
    # Plans (consolidated set)
    "PLAN-INFRA", "PLAN-A1", "PLAN-WORKERS", "PLAN-INVOICE",
    "PLAN-LEGAL", "PLAN-FREE-MODEL", "PLAN-HISTORY",
    # Decisions
    "DEC-001", "DEC-002", "DEC-003", "DEC-004", "DEC-005", "DEC-006",
    "DEC-007", "DEC-008", "DEC-009", "DEC-010", "DEC-011", "DEC-012",
    "DEC-013", "DEC-014", "DEC-015", "DEC-016",
    # Lanes
    "critical-path", "parallel", "a1-lane",
]

# Forbidden stale source-link fragments (legacy / superseded paths).
FORBIDDEN_STALE_FRAGMENTS = (
    "data/a1_forms",
    "config/a1_field_coords.json",
    "config/a1_checkbox_coords.json",
    "config/a1_provisional.json",
    "private/a1_final_review.csv",
    "templates/a1_clean_background",
    "a1_form_overlay.pdf",
)
# Substrings that, if present in a staged path, indicate forbidden PII/secret
# handling. Only the matched token (not the path) is ever reported.
FORBIDDEN_PATH_TOKENS = (
    "a1", "scans", "ocr", "evidence", "output", "runtime", "secrets",
    "private", ".env", "review.csv", "employees", "cohort", "payroll",
    "credential", "password", "token", "apikey", "api_key",
)

# Plan governance paths are text-only planning/archive documentation, and the
# repo-wide `readme-*.md` convention documents pipelines whose names legitimately
# embed pipeline words (readme-scan-to-employees.md, readme-employees-to-a1-form.md).
# The forbidden tokens name real-data/runtime directories or secret filenames
# (e.g. "a1", "evidence", "employees", "payroll") that never live under these
# documentation paths. The token guard stays fully active for every other staged path.
APPROVED_STAGED_PATH_PREFIXES = ("plans/", "readme-")
# Exact reviewed architecture documents, also owned by change-packages.yml.
# Do not exempt the whole directory: nearby private files still fail below.
APPROVED_STAGED_DOCUMENT_PATHS = frozenset({
    "config/a1_checkbox_fix_receipt.json",
    "config/a1_template_repair_2026-09-06.json",
    "docs/architecture/A1_FRAMEWORKS.md",
    "docs/architecture/readme-a1-forms.md",
    "docs/architecture/release-1a-field-mapping.md",
    "docs/architecture/operator-a1-workflow.md",
    "docs/operations/runtime-manifest.md",
    "docs/operations/infra-return-work-order-2026-09-07.md",
    "docs/operations/infra-review-20260907T0230Z/HOST-READINESS.md",
    "docs/operations/infra-review-20260907T0230Z/INFRA-HANDOFF.md",
    "docs/operations/infra-review-20260907T0230Z/OCR-ROLLOUT.md",
    "docs/operations/infra-review-20260907T0230Z/PROMPT.md",
    "docs/operations/infra-review-20260907T0230Z/SECRETS-DATABASE.md",
    "docs/operations/infra-review-20260907T0230Z/SHA256SUMS",
    "docs/operations/infra-review-20260907T0230Z/VALIDATION.json",
    "docs/operations/wsgi-deployment-recipe.md",
    "docs/operations/opencode-work-orders/README.md",
    "docs/operations/opencode-work-orders/artifact-and-j4.md",
    "docs/operations/opencode-work-orders/organization-audit.md",
    "docs/operations/opencode-work-orders/provider-safety.md",
    "docs/operations/opencode-work-orders/release-audit.md",
    "docs/operations/opencode-work-orders/review-and-tests.md",
    "docs/research/2026-09-06-a1-engineering-delivery.md",
    "docs/research/2026-09-06-a1-session-architect-review.md",
    "docs/research/2026-09-06-ocr-local-web-workflow-report.md",
    "docs/research/2026-09-07-a1-stabilization.md",
    "docs/research/2026-09-07-infra-application-review.md",
    "docs/research/2026-09-07-research-audit.md",
    "docs/research/2026-09-07-runtime-j4-engineering.md",
    "docs/research/2026-09-08-agents-md-audit-and-skill-plan.md",
    "docs/research/2026-09-08-consolidation-plan-feedback.md",
    "docs/research/2026-09-08-local-a1-automation-review.md",
})
# Tracked source skill files. Skills are versioned agent instructions, not PII;
# their filenames legitimately embed pipeline words. The token guard stays active
# for any non-listed file under these skill directories.
APPROVED_STAGED_SKILL_PATHS = frozenset({
    ".agents/skills/a1-pdf-production/SKILL.md",
    ".agents/skills/a1-pdf-production/references/field-policy.md",
    ".opencode/skills/market-research-evidence/SKILL.md",
})
# Tracked source scripts/templates. Filenames legitimately embed pipeline words
# (ocr, evidence, scans, etc.). The token guard stays active for any non-listed
# file under scripts/.
APPROVED_STAGED_SCRIPT_PATHS = frozenset({
    "portal/templates/portal/a1_case_detail.html",
    "portal/templates/portal/a1_list.html",
    "portal/templates/portal/a1_generation_confirm.html",
    "scripts/a1_core.py",
    "scripts/a1_quality_gate.py",
    "scripts/a1_audit.py",
    "scripts/finalize_a1.py",
    "scripts/generate_provisional_a1.py",
    "portal/release1a/inbox.py",
    "portal/release1a/identity.py",
    "portal/release1a/a1_exports.py",
    "portal/release1a/a1_drafts.py",
    "portal/release1a/a1_generation_access.py",
    "portal/release1a/a1_generation_confirmation.py",
    "portal/release1a/migrations/0016_a1_draft_reservation.py",
    "portal/release1a/migrations/0017_a1_draft_generation.py",
    "portal/release1a/migrations/0018_a1_generation_confirmation.py",
    "portal/release1a/management/commands/a1_prepare_draft.py",
    "portal/release1a/migrations/0015_assignment_a1_facts.py",
    "portal/release1a/migrations/0014_identity_evaluation_and_draft_claim.py",
    "portal/release1a/management/commands/a1_process_inbox.py",
    "scripts/run_ocr_benchmark.py",
    "scripts/evaluate_a1_pdf_tools.py",
    "scripts/seed_release1a_dev.py",
    "scripts/release_verifier.py",
    "scripts/seed_verification_db.py",
    "scripts/repair_a1_template_checkboxes.py",
    "scripts/reset_synthetic_reviewer_password.py",
    "scripts/playwright_smoke.py",
    "scripts/smoke_synthetic_review_ui.mjs",
})
# Tracked source settings modules. Filenames legitimately embed pipeline words.
APPROVED_STAGED_SETTINGS_PATHS = frozenset({
    "portal/settings_browser_tests.py",
    "portal/settings_verification.py",
})
# Tracked source test files. Filenames legitimately embed pipeline words.
APPROVED_STAGED_TEST_PATHS = frozenset({
    "tests/document_web/test_a1_exports.py",
    "tests/document_web/test_a1_cohort_exports.py",
    "tests/document_web/test_a1_input_publication.py",
    "tests/test_a1_input_artifacts.py",
    "portal/release1a/management/commands/a1_export_inputs.py",
    "tests/document_web/test_a1_drafts.py",
    "tests/document_web/test_a1_generation_access.py",
    "tests/document_web/test_a1_generation_confirmation.py",
    "tests/document_web/test_a1_drafts_postgres.py",
    "tests/test_a1_application_draft.py",
    "tests/document_web/test_a1_exports_postgres.py",
    "tests/document_web/test_browser_journey.py",
    "tests/test_a1_cli_journey.py",
    "tests/test_a1_employee_delivery.py",
    "tests/test_playwright_smoke.py",
    "tests/test_release_verifier.py",
    "tests/test_ocr_benchmark_contract.py",
})
# Tracked synthetic fixture files. Synthetic personal identifiers under
# tests/fixtures/release_1a/orgonik_zivot_* are conspicuously fictional and
# belong to the explicit orgonik_zivot_pdfs cohort in the same directory.
APPROVED_STAGED_FIXTURE_PATHS = frozenset({
    "tests/fixtures/release_1a/workers_orgonik_zivot.json",
    "tests/fixtures/release_1a/assignments_orgonik_zivot.json",
    "tests/fixtures/release_1a/a1_inputs_orgonik_zivot.json",
    "tests/fixtures/release_1a/review_orgonik_zivot.csv",
})

DEFAULT_CATALOG = "planning/catalog.json"
DEFAULT_SCHEMA = "planning/catalog.schema.json"
DECISION_REGISTER = "docs/decisions/decision-register.md"
PLANS_INDEX = "plans/INDEX.md"


class EnvironmentalError(Exception):
    """Raised when the environment cannot support a definitive result."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def normalize_dash(text: str) -> str:
    return text.replace("\u2013", "-").replace("\u2014", "-").strip().lower()


def strip_link_target(target: str) -> str:
    """Return a filesystem path from a markdown link target (drop anchor/query)."""
    t = target.strip()
    if t.startswith(("http://", "https://", "mailto:", "#")):
        return ""
    t = t.split("#", 1)[0].split("?", 1)[0]
    if t.startswith("./"):
        t = t[2:]
    return t.strip()


def resolve_link(root: Path, link: str) -> Path | None:
    rel = strip_link_target(link)
    if not rel:
        return None
    return (root / rel).resolve()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_catalog(root: Path, catalog_path: str) -> dict:
    path = root / catalog_path
    if not path.is_file():
        raise EnvironmentalError("Catalog not found: " + str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON in catalog %s: %s" % (path, exc))


def load_schema(root: Path, schema_path: str):
    try:
        import jsonschema  # local import so missing lib is an env error
    except ImportError as exc:  # pragma: no cover - exercised via sys.modules
        raise EnvironmentalError("jsonschema is not available: " + str(exc))
    path = root / schema_path
    if not path.is_file():
        raise EnvironmentalError("Schema not found: " + str(path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON in schema %s: %s" % (path, exc))
    return jsonschema, data


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------
def parse_decision_register(root: Path) -> dict:
    reg = root / DECISION_REGISTER
    if not reg.is_file():
        return {}
    out = {}
    for line in reg.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("| DEC-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # parts[0] == '' ; parts[1] id ; parts[2] decision ; parts[3] state
        # parts[4] source ; parts[5] owner ; parts[6] approver
        # parts[7] date ; parts[8] evidence ; parts[9] notes ; parts[10] ''
        if len(parts) < 9:
            continue
        dec_id = parts[1]
        if not dec_id.startswith("DEC-"):
            continue
        out[dec_id] = {
            "state": parts[3],
            "owner": parts[5],
            "approver": parts[6],
            "date": parts[7],
            "evidence": parts[8],
        }
    return out


def parse_plan_header(path: Path) -> dict:
    result = {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        m = re.match(r"^\*\*(Status|Milestone)\*\*:\s*(.+?)\s*$", line)
        if m:
            result[m.group(1).lower()] = m.group(2).strip()
    return result


def parse_index_statuses(root: Path) -> dict:
    idx = root / PLANS_INDEX
    if not idx.is_file():
        return {}
    out = {}
    pat = re.compile(r"\[Plan ([A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)\b[^\]]*\]\(([^)]+)\)\s*\|\s*(\w+)")
    for line in idx.read_text(encoding="utf-8").splitlines():
        m = pat.search(line)
        if m:
            out[m.group(1)] = m.group(3)
    return out


def plan_file_for_item(root: Path, item: dict):
    item_id = item["id"].lower()
    for link in item.get("source_links", []):
        rel = strip_link_target(link)
        if not rel or "plans/" not in rel:
            continue
        p = (root / rel).resolve()
        if not p.is_file():
            continue
        stem = Path(rel).stem.lower()
        # Accept plans/<ID>.md and plans/PLAN-<ID>.md as the plan file for a
        # consolidated PLAN-* id, with a substring fallback for legacy names.
        if stem == item_id or stem == ("plan-" + item_id):
            return p
        if ("plan-" + item_id) in rel:
            return p
    return None


def iter_markdown_links(text: str):
    for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        yield m.group(1).strip()


def scan_skill_links(root: Path):
    """Return list of (skill_dir, skill_md, [(ref, exists)]) for every skill root.

    Covers both ``.agents/skills`` (authoritative A1 path) and ``.opencode/skills``
    (experimental research skill) so neither is excluded from validation.
    """
    results = []
    for skills_root in (root / ".agents" / "skills", root / ".opencode" / "skills"):
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            refs = []
            if skill_md.is_file():
                for target in iter_markdown_links(skill_md.read_text(encoding="utf-8", errors="ignore")):
                    rel = strip_link_target(target)
                    if not rel or rel.startswith(("http://", "https://", "mailto:")):
                        continue
                    resolved = (skill_md.parent / rel).resolve()
                    refs.append((rel, resolved.exists()))
            results.append((skill_dir.name, skill_md, refs))
    return results


def get_staged_paths(root: Path):
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise EnvironmentalError("git unavailable for staged-path check: " + str(exc))
    if proc.returncode != 0:
        raise EnvironmentalError("git diff --cached failed: " + proc.stderr.strip())
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# The eighteen named checks
# ---------------------------------------------------------------------------
def check_schema_validity(catalog, jsonschema, schema):
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except Exception as exc:  # invalid schema itself
        return False, "schema is invalid: " + str(exc)
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(catalog), key=lambda e: list(e.path))
    if errors:
        msgs = [("%s: %s" % ("/".join(str(p) for p in e.path) or "<root>", e.message))
                for e in errors[:8]]
        return False, "catalog failed schema: " + " | ".join(msgs)
    return True, "catalog conforms to schema"


def check_required_ids(catalog):
    actual = {i.get("id") for i in catalog.get("items", []) if isinstance(i, dict)}
    expected = set(REQUIRED_IDS)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        detail = ""
        if missing:
            detail += "missing: " + ",".join(missing) + " "
        if extra:
            detail += "unexpected: " + ",".join(extra)
        return False, detail.strip()
    return True, "all %d required IDs present" % len(expected)


def check_duplicate_ids(catalog):
    ids = [i.get("id") for i in catalog.get("items", []) if isinstance(i, dict)]
    seen = set()
    dups = []
    for i in ids:
        if i in seen and i not in dups:
            dups.append(i)
        seen.add(i)
    if dups:
        return False, "duplicate IDs: " + ",".join(dups)
    return True, "no duplicate IDs"


def check_controlled_vocabularies(catalog):
    problems = []
    for idx, item in enumerate(catalog.get("items", [])):
        iid = item.get("id", "[%d]" % idx)
        if item.get("kind") not in VALID_KINDS:
            problems.append("%s: invalid kind '%s'" % (iid, item.get("kind")))
        if item.get("status") not in VALID_STATUSES:
            problems.append("%s: invalid status '%s'" % (iid, item.get("status")))
        if item.get("decision_state") not in VALID_DECISION_STATES:
            problems.append("%s: invalid decision_state '%s'" % (iid, item.get("decision_state")))
        if item.get("evidence_state") not in VALID_EVIDENCE_STATES:
            problems.append("%s: invalid evidence_state '%s'" % (iid, item.get("evidence_state")))
        for d in item.get("dependencies", []):
            if not isinstance(d, dict):
                problems.append("%s: dependency is not an object" % iid)
                continue
            if d.get("gate") not in VALID_GATES:
                problems.append("%s: invalid dependency gate '%s'" % (iid, d.get("gate")))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "all controlled vocabularies valid"


def check_owners_approvers_gates_evidence(catalog):
    problems = []
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        if not item.get("owner"):
            problems.append("%s: missing owner" % iid)
        if not isinstance(item.get("quality_gates"), list):
            problems.append("%s: quality_gates must be a list" % iid)
        if not isinstance(item.get("evidence_state"), str):
            problems.append("%s: missing evidence_state" % iid)
        if item.get("status") == "accepted" and not item.get("approver"):
            problems.append("%s: status accepted requires approver" % iid)
        for fld in ("referenced_files", "referenced_commands"):
            if fld in item and not isinstance(item[fld], list):
                problems.append("%s: %s must be a list" % (iid, fld))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "owners/approvers/gates/evidence present"


def check_accepted_no_placeholder_evidence(catalog):
    problems = []
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        if item.get("status") == "accepted":
            ev_state = item.get("evidence_state")
            if ev_state == "none":
                problems.append("%s: accepted status requires evidence_state != 'none'" % iid)
            elif ev_state == "synthetic-tested":
                kind = item.get("kind")
                if kind in ("plan", "checkpoint"):
                    problems.append("%s: accepted %s with synthetic-tested evidence needs review before acceptance" % (iid, kind))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "accepted items have verified evidence state"


def check_dependency_existence(catalog):
    ids = {i.get("id") for i in catalog.get("items", []) if isinstance(i, dict)}
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        for d in item.get("dependencies", []):
            dep_id = d.get("id") if isinstance(d, dict) else d
            if dep_id not in ids:
                return False, "%s: dependency '%s' does not exist" % (iid, dep_id)
    return True, "all dependency targets exist"


def check_self_dependencies(catalog):
    for item in catalog.get("items", []):
        iid = item.get("id")
        for d in item.get("dependencies", []):
            dep_id = d.get("id") if isinstance(d, dict) else d
            if dep_id == iid:
                return False, "%s: depends on itself" % iid
    return True, "no self-dependencies"


def check_gate_aware_cycles(catalog):
    ids = {i.get("id") for i in catalog.get("items", []) if isinstance(i, dict)}
    adj = {i.get("id"): [] for i in catalog.get("items", [])}
    for item in catalog.get("items", []):
        iid = item.get("id")
        for d in item.get("dependencies", []):
            if not isinstance(d, dict):
                continue
            dep_id = d.get("id")
            gate = d.get("gate")
            if dep_id in ids and gate in BLOCKING_GATES:
                adj.setdefault(iid, []).append(dep_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}
    cycle_path = []

    def visit(node, stack):
        color[node] = GRAY
        stack.append(node)
        for nxt in adj.get(node, []):
            if color.get(nxt) == GRAY:
                idx = stack.index(nxt)
                cycle_path.extend(stack[idx:] + [nxt])
                return True
            if color.get(nxt) == WHITE and visit(nxt, stack):
                return True
        stack.pop()
        color[node] = BLACK
        return False

    for node in adj:
        if color[node] == WHITE:
            if visit(node, []):
                return False, "prohibited blocking-gate cycle: " + " -> ".join(cycle_path)
    return True, "no prohibited (blocking-gate) cycles"


def check_plan_header_index_coherence(catalog, root):
    index_status = parse_index_statuses(root)
    problems = []
    for item in catalog.get("items", []):
        if item.get("kind") not in ("plan", "checkpoint"):
            continue
        if item.get("status") in ("superseded", "historical"):
            continue
        pf = plan_file_for_item(root, item)
        if pf is None:
            continue
        header = parse_plan_header(pf)
        iid = item.get("id")
        # status coherence: catalog vs header vs index
        hstatus = header.get("status")
        if hstatus and item.get("status") != hstatus:
            problems.append("%s: catalog status '%s' != header '%s'" % (iid, item.get("status"), hstatus))
        istatus = index_status.get(iid)
        if istatus and item.get("status") != istatus:
            problems.append("%s: catalog status '%s' != index '%s'" % (iid, item.get("status"), istatus))
        # milestone coherence: catalog vs header
        hmil = header.get("milestone")
        if hmil and normalize_dash(hmil) != normalize_dash(item.get("milestone", "")):
            problems.append("%s: catalog milestone '%s' != header '%s'" % (iid, item.get("milestone"), hmil))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "plan header/index/catalog coherent"


def check_decision_register_coherence(catalog, root):
    reg = parse_decision_register(root)
    if not reg:
        return True, "decision register not found (not in scope)"
    problems = []
    none_tokens = {"", "-", "\u2014", "—", "n/a"}

    def norm(v):
        return (v or "").strip()

    for item in catalog.get("items", []):
        if item.get("kind") != "decision":
            continue
        iid = item.get("id")
        row = reg.get(iid)
        if row is None:
            problems.append("%s: absent from decision register" % iid)
            continue
        if norm(row["state"]) != norm(item.get("decision_state")):
            problems.append("%s: decision_state '%s' != register '%s'" % (iid, item.get("decision_state"), row["state"]))
        reg_date = norm(row["date"])
        cat_date = item.get("decision_date")
        if reg_date in none_tokens:
            if cat_date not in (None, "", "-"):
                problems.append("%s: register has no date but catalog date set" % iid)
        else:
            if norm(cat_date) != reg_date:
                problems.append("%s: decision_date '%s' != register '%s'" % (iid, cat_date, reg_date))
        reg_ev = norm(row["evidence"])
        cat_ev = norm(item.get("decision_evidence"))
        if reg_ev in none_tokens:
            if cat_ev not in none_tokens:
                problems.append("%s: register has no evidence but catalog evidence set" % iid)
        else:
            if cat_ev != reg_ev:
                problems.append("%s: decision_evidence mismatch" % iid)
    if problems:
        return False, "; ".join(problems[:8])
    return True, "decision register and catalog coherent"


def check_accepted_decision_approver_date_evidence(catalog):
    problems = []
    for item in catalog.get("items", []):
        if item.get("status") != "accepted":
            continue
        iid = item.get("id")
        if not item.get("approver"):
            problems.append("%s: accepted item missing approver" % iid)
        if item.get("kind") == "decision":
            if not item.get("decision_date"):
                problems.append("%s: accepted decision missing decision_date" % iid)
            if not item.get("decision_evidence"):
                problems.append("%s: accepted decision missing decision_evidence" % iid)
    if problems:
        return False, "; ".join(problems[:8])
    return True, "accepted decisions carry approver/date/evidence"


def check_source_link_existence(catalog, root):
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        links = item.get("source_links") or []
        if not links:
            return False, "%s: no source_links" % iid
        for link in links:
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = resolve_link(root, link)
            if resolved is None:
                continue
            if not resolved.exists():
                return False, "%s: source link not found: %s" % (iid, link)
    return True, "all source links resolve"


def check_markdown_links(catalog, root):
    md_files = set()
    for item in catalog.get("items", []):
        for link in item.get("source_links", []):
            rel = strip_link_target(link)
            if rel.endswith(".md"):
                resolved = resolve_link(root, link)
                if resolved is not None and resolved.exists():
                    md_files.add(resolved)
    problems = []
    for md in sorted(md_files):
        base = md.parent
        for target in iter_markdown_links(md.read_text(encoding="utf-8", errors="ignore")):
            rel = strip_link_target(target)
            if not rel or rel.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (base / rel).resolve()
            if not resolved.exists():
                problems.append("%s: broken link %s" % (md.name, target))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "markdown links valid"


def check_historical_policy(catalog):
    ids = {i.get("id") for i in catalog.get("items", []) if isinstance(i, dict)}
    for item in catalog.get("items", []):
        if item.get("status") in ("historical", "superseded"):
            iid = item.get("id")
            if item.get("executable") is not False:
                return False, "%s: %s requires executable=false" % (iid, item.get("status"))
            succ = item.get("successor")
            if not succ or succ not in ids:
                return False, "%s: %s requires an existing successor" % (iid, item.get("status"))
    return True, "historical/superseded items non-executable with successors"


def check_referenced_files_commands(catalog, root):
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        for rf in item.get("referenced_files", []) or []:
            if not (root / rf).resolve().exists():
                return False, "%s: referenced file missing: %s" % (iid, rf)
        for rc in item.get("referenced_commands", []) or []:
            if shutil.which(rc) is None:
                return False, "%s: referenced command not found: %s" % (iid, rc)
    return True, "referenced files/commands exist"


def check_decision_state_accepted(catalog):
    """Any item with decision_state 'accepted' carries approver/date/evidence.

    The rule is kind-independent: a plan or lane may not use decision_state
    'accepted' to bypass the metadata requirement that genuine accepted
    decisions must satisfy.
    """
    problems = []
    for item in catalog.get("items", []):
        if item.get("decision_state") != "accepted":
            continue
        iid = item.get("id")
        if not item.get("approver"):
            problems.append("%s: accepted decision_state missing approver" % iid)
        if not item.get("decision_date"):
            problems.append("%s: accepted decision_state missing decision_date" % iid)
        if not item.get("decision_evidence"):
            problems.append("%s: accepted decision_state missing decision_evidence" % iid)
    if problems:
        return False, "; ".join(problems[:8])
    return True, "accepted decision_state carries approver/date/evidence"


def check_active_plan_index_presence(catalog, root):
    """Every active plan is claimed in the planning INDEX."""
    idx = root / PLANS_INDEX
    if not idx.is_file():
        return True, "INDEX not found (not in scope)"
    text = idx.read_text(encoding="utf-8")
    problems = []
    for item in catalog.get("items", []):
        if item.get("kind") != "plan":
            continue
        if item.get("status") not in ("active", "awaiting-review", "accepted"):
            continue
        iid = item.get("id")
        # A catalog ID may deliberately disambiguate one plan from another
        # (PLAN-INFRA versus PLAN-INVOICE). In that case, the authoritative
        # source link in INDEX is an unambiguous claim even when the human
        # title is shortened.
        source_links = item.get("source_links", []) or []
        source_claimed = any(strip_link_target(link) in text for link in source_links)
        if not source_claimed and ("Plan %s" % iid) not in text and ("plan-%s" % iid.lower()) not in text.lower():
            problems.append("%s: active plan not claimed in INDEX" % iid)
    if problems:
        return False, "; ".join(problems[:8])
    return True, "active plans claimed in INDEX"


def check_specialist_gates(catalog):
    """specialist-gate dependencies target a plan or decision, never a lane/milestone."""
    ids = {i.get("id") for i in catalog.get("items", []) if isinstance(i, dict)}
    kinds = {i.get("id"): i.get("kind") for i in catalog.get("items", []) if isinstance(i, dict)}
    problems = []
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        for d in item.get("dependencies", []):
            if not isinstance(d, dict):
                continue
            if d.get("gate") != "specialist-gate":
                continue
            dep_id = d.get("id")
            if dep_id not in ids:
                continue  # existence checked elsewhere
            k = kinds.get(dep_id)
            if k in ("lane", "roadmap_milestone", "checkpoint"):
                problems.append("%s: specialist-gate dependency '%s' targets a %s" % (iid, dep_id, k))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "specialist-gate dependencies target plans/decisions"


def check_skill_metadata(root):
    results = scan_skill_links(root)
    if not results:
        return True, "no skills to verify"
    problems = []
    for name, skill_md, refs in results:
        if not skill_md.is_file():
            problems.append("skill %s: missing SKILL.md" % name)
        for rel, exists in refs:
            if not exists:
                problems.append("skill %s: missing referenced file %s" % (name, rel))
    if problems:
        return False, "; ".join(problems[:8])
    return True, "skill metadata and one-level references valid"


def check_forbidden_stale_and_prototype(catalog):
    problems = []
    for item in catalog.get("items", []):
        iid = item.get("id", "?")
        links = item.get("source_links", []) or []
        for link in links:
            low = link.lower()
            for frag in FORBIDDEN_STALE_FRAGMENTS:
                if frag in low:
                    problems.append("%s: forbidden stale path: %s" % (iid, frag))
            if "docs/prototypes/" in low and not any(
                (l.lower().startswith("docs/prototypes/") is False) and ("docs/prototypes/" not in l.lower())
                for l in links
            ):
                problems.append("%s: prototype item without authority source link" % iid)
    if problems:
        return False, "; ".join(problems[:8])
    return True, "no forbidden stale paths; prototype items carry authority links"


def check_staged_forbidden_and_pii(catalog, root):
    staged = get_staged_paths(root)
    matched_tokens = set()
    for path in staged:
        if (path.startswith(APPROVED_STAGED_PATH_PREFIXES)
                or path in APPROVED_STAGED_DOCUMENT_PATHS
                or path in APPROVED_STAGED_SKILL_PATHS
                or path in APPROVED_STAGED_SCRIPT_PATHS
                or path in APPROVED_STAGED_SETTINGS_PATHS
                or path in APPROVED_STAGED_TEST_PATHS
                or path in APPROVED_STAGED_FIXTURE_PATHS):
            continue
        low = path.lower()
        for tok in FORBIDDEN_PATH_TOKENS:
            if tok in low:
                matched_tokens.add(tok)
    if matched_tokens:
        return False, "staged paths match forbidden tokens: " + ",".join(sorted(matched_tokens))
    return True, "no forbidden/staged PII or secret paths"


def check_prototype_start_gate(catalog, root):
    by_id = {item.get("id"): item for item in catalog.get("items", [])}
    plan = by_id.get("PLAN-INFRA")
    if not plan:
        return False, "PLAN-INFRA missing"
    approvals_path = root / "planning/approvals.json"
    if not approvals_path.is_file():
        return False, "approval register missing"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    adr = next((record for record in approvals.get("records", []) if record.get("id") == "ADR-001"), None)
    if not adr:
        return False, "ADR-001 approval record missing"
    if plan.get("executable"):
        if adr.get("validation") != "passed" or adr.get("implementation_gate") != "open":
            return False, "PLAN-INFRA executable before ADR-001 validation gate opens"
        if by_id.get("PLAN-WORKERS", {}).get("decision_state") != "accepted":
            return False, "PLAN-INFRA executable before PLAN-WORKERS Release 1A slice acceptance"
    return True, "PLAN-INFRA preparation active; scaffold remains bound to machine-readable gates"


def check_approval_asset_and_provenance(catalog, root):
    approvals_path = root / "planning/approvals.json"
    asset_path = root / "docs/prototypes/roadmap-portal/approval-data.js"
    provenance_path = root / "docs/mock-data-provenance.md"
    if not approvals_path.is_file() or not asset_path.is_file() or not provenance_path.is_file():
        return False, "approval asset or provenance contract missing"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
    expected = "window.APPROVAL_REGISTER = " + json.dumps(approvals, ensure_ascii=False, indent=2, sort_keys=True) + ";\n"
    if asset_path.read_text(encoding="utf-8") != expected:
        return False, "approval asset is stale"
    provenance = provenance_path.read_text(encoding="utf-8")
    forbidden = "create a separate `tests/fixtures/production/` directory"
    if forbidden in provenance:
        return False, "provenance suggests tracked production fixtures"
    return True, "approval asset current; provenance prohibits tracked real-data fixtures"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_checks(catalog, root, jsonschema, schema):
    return [
        ("schema validity", lambda: check_schema_validity(catalog, jsonschema, schema)),
        ("exact required ID coverage", lambda: check_required_ids(catalog)),
        ("duplicate IDs", lambda: check_duplicate_ids(catalog)),
        ("controlled vocabularies", lambda: check_controlled_vocabularies(catalog)),
        ("owners/approvers/gates/evidence", lambda: check_owners_approvers_gates_evidence(catalog)),
        ("accepted no placeholder evidence", lambda: check_accepted_no_placeholder_evidence(catalog)),
        ("dependency existence", lambda: check_dependency_existence(catalog)),
        ("self-dependencies", lambda: check_self_dependencies(catalog)),
        ("gate-aware cycle rules", lambda: check_gate_aware_cycles(catalog)),
        ("plan header/index/catalog coherence", lambda: check_plan_header_index_coherence(catalog, root)),
        ("decision register/catalog coherence", lambda: check_decision_register_coherence(catalog, root)),
        ("accepted-decision approver/date/evidence", lambda: check_accepted_decision_approver_date_evidence(catalog)),
        ("accepted decision_state approver/date/evidence", lambda: check_decision_state_accepted(catalog)),
        ("actual source-link existence", lambda: check_source_link_existence(catalog, root)),
        ("Markdown relative-link validation", lambda: check_markdown_links(catalog, root)),
        ("historical/superseded policy", lambda: check_historical_policy(catalog)),
        ("referenced command/file existence", lambda: check_referenced_files_commands(catalog, root)),
        ("skill metadata and one-level references", lambda: check_skill_metadata(root)),
        ("active plans claimed in INDEX", lambda: check_active_plan_index_presence(catalog, root)),
        ("specialist-gate dependency targets", lambda: check_specialist_gates(catalog)),
        ("forbidden stale paths and prototype-source links", lambda: check_forbidden_stale_and_prototype(catalog)),
        ("prototype-start gate consistency", lambda: check_prototype_start_gate(catalog, root)),
        ("approval asset and fixture provenance", lambda: check_approval_asset_and_provenance(catalog, root)),
        ("staged forbidden-path and PII/secret indicators", lambda: check_staged_forbidden_and_pii(catalog, root)),
    ]


def build_next_actions(failed_checks):
    actions = []
    for name, detail in failed_checks:
        severity = "high" if ("schema" in name or "staged" in name or "PII" in name) else "medium"
        actions.append({
            "when": "before re-running ./venv/bin/python scripts/validate_planning.py",
            "command": "inspect the failing catalog item and authoritative source; fix the data or source, then re-run the validator",
            "purpose": "resolve check '%s': %s" % (name, detail),
            "severity": severity,
        })
    return actions


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic planning validator")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--root", default=".")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()

    try:
        catalog = load_catalog(root, args.catalog)
    except EnvironmentalError as exc:
        sys.stderr.write("ENVIRONMENTAL: %s\n" % exc)
        return 2
    except ValueError as exc:
        sys.stderr.write("INVALID CATALOG: %s\n" % exc)
        return 1

    try:
        jsonschema, schema = load_schema(root, args.schema)
    except EnvironmentalError as exc:
        sys.stderr.write("ENVIRONMENTAL: %s\n" % exc)
        return 2
    except ValueError as exc:
        sys.stderr.write("INVALID SCHEMA: %s\n" % exc)
        return 1

    checks = build_checks(catalog, root, jsonschema, schema)
    results = []
    failed = []
    for name, fn in checks:
        try:
            ok, detail = fn()
        except EnvironmentalError:
            raise
        except Exception as exc:  # a raised exception is a failure, never a pass
            ok, detail = False, "exception: %s" % exc
        results.append({"name": name, "passed": bool(ok), "detail": detail})
        if not ok:
            failed.append((name, detail))

    passed_n = sum(1 for r in results if r["passed"])
    failed_n = len(results) - passed_n
    next_actions = build_next_actions(failed)

    if args.json:
        payload = {
            "result": "pass" if failed_n == 0 else "fail",
            "root": str(root),
            "summary": {"checks": len(results), "passed": passed_n, "failed": failed_n},
            "checks": results,
            "next_actions": next_actions,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print("=== Planning Validator (%d checks) ===" % len(results))
        for r in results:
            mark = "PASS" if r["passed"] else "FAIL"
            print("[%s] %s — %s" % (mark, r["name"], r["detail"]))
        print("\nSummary: %d passed, %d failed" % (passed_n, failed_n))
        if next_actions:
            print("\nNext actions:")
            for a in next_actions:
                print("  - (%s) %s" % (a["severity"], a["purpose"]))
        else:
            print("\nNext actions: none required.")

    return 0 if failed_n == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except EnvironmentalError as exc:
        sys.stderr.write("ENVIRONMENTAL: %s\n" % exc)
        sys.exit(2)
