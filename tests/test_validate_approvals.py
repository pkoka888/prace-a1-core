import json
from pathlib import Path

from planning.approval_register import (
    validate,
    check_gate,
    approvals_hash,
    ApprovalRegisterError,
)


ROOT = Path(__file__).resolve().parents[1]


def _copy_schema_and_catalog(tmp_path):
    (tmp_path / "planning").mkdir()
    (tmp_path / "docs/decisions").mkdir(parents=True)
    (tmp_path / "docs/operations").mkdir(parents=True)
    (tmp_path / "plans").mkdir(parents=True)
    (tmp_path / "planning/approvals.schema.json").write_text(
        (ROOT / "planning/approvals.schema.json").read_text()
    )
    (tmp_path / "planning/catalog.json").write_text(
        (ROOT / "planning/catalog.json").read_text()
    )
    for src in [
        "docs/decisions/ADR-001-jan-portal-architecture.md",
        "docs/decisions/ADR-002-release-1a-data-and-transactions.md",
        "docs/operations/release-1a-review-environment.md",
        "docs/release-1a/unblock-review-packet.md",
        "plans/PLAN-REAL-DATA.md",
        "plans/PLAN-WORKERS.md",
        "plans/INDEX.md",
    ]:
        src_path = ROOT / src
        if src_path.exists():
            dst = tmp_path / src
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src_path.read_text())


def test_live_approval_register_passes():
    result = validate(ROOT)
    assert result["result"] == "pass"
    assert result["records"] == 9
    assert result["errors"] == []


def test_open_gate_requires_passed_checks(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["implementation_gate"] = "open"
    data["records"][0]["checks"][0]["status"] = "pending"
    data["records"][0]["validation"] = "pending"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    assert any("cannot open" in item for item in validate(tmp_path)["errors"])


def test_deviation_requires_reason(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["choices"][0]["selected"] = "different"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    assert any("deviation lacks reason" in item for item in validate(tmp_path)["errors"])


# ---- Negative transition tests ----

def test_impl_gate_open_requires_human_approved(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["implementation_gate"] = "open"
    data["records"][0]["human_decision"] = "proposed"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    errors = validate(tmp_path)["errors"]
    assert any("human_decision is proposed" in e and "implementation_gate is open" in e for e in errors)


def test_activation_gate_open_requires_impl_gate_open(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["activation_gate"] = "open"
    data["records"][0]["implementation_gate"] = "blocked"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any(
        "activation_gate cannot open" in e or "activation_gate is open but implementation_gate is blocked" in e
        for e in errors
    )


def test_approved_record_requires_approver_approved_at_evidence(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["human_decision"] = "approved"
    data["records"][0]["approver"] = "pending — operator approval required"
    data["records"][0]["approved_at"] = None
    data["records"][0]["approval_evidence"] = None
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("approved record lacks approver/date/evidence" in e for e in errors)


def test_approved_human_with_pending_choice_rejected(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["human_decision"] = "approved"
    data["records"][0]["approver"] = "Test Approver"
    data["records"][0]["approved_at"] = "2026-09-06"
    data["records"][0]["approval_evidence"] = "synthetic test"
    data["records"][0]["choices"][0]["approval"] = "pending"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("approved but a choice is not approved" in e for e in errors)


def test_impl_gate_blocked_requires_reason(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["implementation_gate"] = "blocked"
    data["records"][0]["implementation_gate_reason"] = None
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("blocked but has no reason" in e for e in errors)


def test_missing_dependency_rejected(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["dependencies"].append({"id": "DOES-NOT-EXIST", "required_gate": "approved"})
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("missing dependency DOES-NOT-EXIST" in e for e in errors)


def test_duplicate_record_id_rejected(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"].append(json.loads(json.dumps(data["records"][0])))
    data["records"][-1]["id"] = data["records"][0]["id"]
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("duplicate approval record id" in e for e in errors)


def test_impl_gate_open_requires_all_checks_passed(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["implementation_gate"] = "open"
    data["records"][0]["human_decision"] = "approved"
    data["records"][0]["approver"] = "Test Approver"
    data["records"][0]["approved_at"] = "2026-09-06"
    data["records"][0]["approval_evidence"] = "synthetic test"
    data["records"][0]["checks"][0]["status"] = "failed"
    data["records"][0]["validation"] = "failed"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("implementation_gate is open but checks derive failed" in e for e in errors)


def test_check_gate_impl_blocked_when_checks_pending(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    eng = next(r for r in data["records"] if r["id"] == "ENG-001")
    eng["implementation_gate"] = "blocked"
    eng["implementation_gate_reason"] = "prerequisites not yet met"
    eng["human_decision"] = "approved"
    eng["approver"] = "Test Approver"
    eng["approved_at"] = "2026-09-06"
    eng["approval_evidence"] = "synthetic test"
    for c in eng["checks"]:
        c["status"] = "pending"
    eng["validation"] = "pending"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    is_open, reason = check_gate(tmp_path, "ENG-001")
    assert not is_open
    assert "blocked" in reason.lower() or "prerequisites" in reason.lower() or "not yet" in reason.lower()


def test_check_gate_returns_false_for_unknown_record(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    (tmp_path / "planning/approvals.json").write_text(json.dumps({"schema_version": "1.0", "updated_at": "2026-09-06T00:00:00Z", "records": []}))
    is_open, reason = check_gate(tmp_path, "ENG-001")
    assert not is_open
    assert "not found" in reason


def test_check_gate_requires_human_approved_even_with_open_gate(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["implementation_gate"] = "open"
    data["records"][0]["human_decision"] = "proposed"
    data["records"][0]["checks"][0]["status"] = "pending"
    data["records"][0]["validation"] = "pending"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    (tmp_path / "docs/decisions/ADR-001-jan-portal-architecture.md").write_text("synthetic")
    errors = validate(tmp_path)["errors"]
    assert any("implementation_gate is open but human_decision is proposed" in e for e in errors)


def test_dependency_cycle_detected(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    eng = next(r for r in data["records"] if r["id"] == "ENG-001")
    rev2 = next(r for r in data["records"] if r["id"] == "REV-002")
    rev2["dependencies"] = [{"id": "ENG-001", "required_gate": "approved"}]
    eng["dependencies"] = [{"id": "REV-002", "required_gate": "approved"}]
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("cycle" in e.lower() for e in errors)


def test_check_gate_enforces_dep_approved_state(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    eng = next(r for r in data["records"] if r["id"] == "ENG-001")
    rev2 = next(r for r in data["records"] if r["id"] == "REV-002")
    eng["implementation_gate"] = "open"
    eng["human_decision"] = "approved"
    eng["approver"] = "Test Approver"
    eng["approved_at"] = "2026-09-06"
    eng["approval_evidence"] = "synthetic"
    for c in eng["checks"]:
        c["status"] = "passed"
    eng["validation"] = "passed"
    rev2["implementation_gate"] = "blocked"
    rev2["implementation_gate_reason"] = "waiting for dependency"
    rev2["human_decision"] = "proposed"
    rev2["dependencies"] = [{"id": "ENG-001", "required_gate": "approved"}]
    for c in rev2["checks"]:
        c["status"] = "passed"
    rev2["validation"] = "passed"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    is_open, reason = check_gate(tmp_path, "REV-002")
    assert not is_open
    assert "blocked" in reason.lower() or "waiting" in reason.lower()


def test_check_gate_enforces_dep_validated_state(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    eng = next(r for r in data["records"] if r["id"] == "ENG-001")
    rev2 = next(r for r in data["records"] if r["id"] == "REV-002")
    eng["implementation_gate"] = "open"
    eng["human_decision"] = "approved"
    eng["approver"] = "Test Approver"
    eng["approved_at"] = "2026-09-06"
    eng["approval_evidence"] = "synthetic"
    for c in eng["checks"]:
        c["status"] = "passed"
    eng["validation"] = "passed"
    rev2["implementation_gate"] = "blocked"
    rev2["implementation_gate_reason"] = "waiting for dependency"
    rev2["human_decision"] = "approved"
    rev2["approver"] = "Test Approver"
    rev2["approved_at"] = "2026-09-06"
    rev2["approval_evidence"] = "synthetic"
    rev2["dependencies"] = [{"id": "ENG-001", "required_gate": "validated"}]
    for c in rev2["checks"]:
        c["status"] = "pending"
    rev2["validation"] = "pending"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    is_open, reason = check_gate(tmp_path, "REV-002")
    assert not is_open
    assert "blocked" in reason.lower() or "waiting" in reason.lower()


def test_check_gate_requires_correct_approver_not_placeholder(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    eng = next(r for r in data["records"] if r["id"] == "ENG-001")
    eng["human_decision"] = "approved"
    eng["approver"] = "pending — engineering gate only"
    eng["approved_at"] = "2026-09-06"
    eng["approval_evidence"] = "synthetic"
    for c in eng["checks"]:
        c["status"] = "passed"
    eng["validation"] = "passed"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("placeholder" in e.lower() for e in errors)


def test_validate_returns_errors_for_wrong_approvals_hash(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    result = validate(tmp_path, expected_approvals_hash="wronghash")
    assert result["result"] == "fail"
    assert any("hash" in e.lower() for e in result["errors"])


def test_validate_rejects_missing_source_file(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["source"] = "this/file/does/not/exist.md"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    errors = validate(tmp_path)["errors"]
    assert any("source does not exist" in e for e in errors)


def test_check_gate_closed_on_register_validation_failure(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    data["records"][0]["source"] = "this/file/does/not/exist.md"
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    is_open, reason = check_gate(tmp_path, "ENG-001")
    assert not is_open
    assert "validation failed" in reason.lower()


def _synthetic_git_register(tmp_path):
    """A disposable repository proves root binding without touching project Git."""
    import subprocess
    _copy_schema_and_catalog(tmp_path)
    (tmp_path / 'planning/approvals.json').write_text((ROOT / 'planning/approvals.json').read_text())
    (tmp_path / 'src/document_core').mkdir(parents=True)
    (tmp_path / 'src/document_core/synthetic.py').write_text('SYNTHETIC = True\n')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args],text=True,stderr=subprocess.DEVNULL).strip()
    git('init')
    paths = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*')
                   if p.is_file() and '.git' not in p.parts)
    git('add','--',*paths)
    git('-c','user.name=Synthetic Test','-c','user.email=synthetic@example.invalid',
        '-c','commit.gpgsign=false','commit','-m','Synthetic fixture')
    return git


def test_clean_receipt_matches_exact_root_commit_and_approval_hash(tmp_path):
    git = _synthetic_git_register(tmp_path)
    # Caller cwd is the dirty project; only the supplied synthetic root matters.
    result = validate(tmp_path,require_clean=True,expected_commit=git('rev-parse','HEAD'),
                      expected_approvals_hash=approvals_hash(tmp_path))
    assert result['errors']==[]


def test_dirty_tracked_document_core_blocks_receipt(tmp_path):
    _synthetic_git_register(tmp_path)
    (tmp_path/'src/document_core/synthetic.py').write_text('SYNTHETIC = False\n')
    assert any('scope is dirty' in e for e in validate(tmp_path,require_clean=True)['errors'])


def test_untracked_runtime_dependency_blocks_receipt(tmp_path):
    _synthetic_git_register(tmp_path)
    (tmp_path/'src/document_core/new.py').write_text('SYNTHETIC = True\n')
    assert any('untracked=True' in e for e in validate(tmp_path,require_clean=True)['errors'])


def test_wrong_commit_and_approval_hash_are_independent_blockers(tmp_path):
    _synthetic_git_register(tmp_path)
    result=validate(tmp_path,require_clean=True,expected_commit='0'*40,expected_approvals_hash='0'*64)
    assert any('expected commit' in e for e in result['errors'])
    assert any('approvals hash' in e for e in result['errors'])


def test_missing_git_repository_is_fail_closed(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    (tmp_path/'planning/approvals.json').write_text((ROOT/'planning/approvals.json').read_text())
    result=validate(tmp_path,require_clean=True,expected_commit='0'*40)
    assert any('could not check git status' in e for e in result['errors'])
    assert any('could not read HEAD' in e for e in result['errors'])


def test_untracked_a1_audit_and_path_helpers_block_review(tmp_path):
    _synthetic_git_register(tmp_path)
    scripts=tmp_path/'scripts';scripts.mkdir(exist_ok=True)
    for name in ('a1_audit.py','a1_paths.py'):
        path=scripts/name;path.write_text('# synthetic dependency\n')
        assert any('untracked=True' in e for e in validate(tmp_path,require_clean=True)['errors'])
        path.unlink()


def test_catalog_state_and_date_checks_survive_cli_consolidation(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    (tmp_path / "planning/approvals.json").write_text((ROOT / "planning/approvals.json").read_text())
    catalog_path = tmp_path / "planning/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    choice = json.loads((ROOT / "planning/approvals.json").read_text())["records"][0]["choices"][0]
    item = next(i for i in catalog["items"] if i["id"] == choice["id"])
    item["decision_state"] = "rejected"
    catalog_path.write_text(json.dumps(catalog))
    assert any("catalog state" in e for e in validate(tmp_path)["errors"])
    item["decision_state"] = "accepted"
    item["decision_date"] = "1900-01-01"
    catalog_path.write_text(json.dumps(catalog))
    assert any("date conflicts" in e for e in validate(tmp_path)["errors"])


def test_gate_uses_only_the_validated_register_snapshot(tmp_path, monkeypatch):
    import planning.approval_register as module
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    calls = []
    def changing_register(root):
        calls.append(root)
        if len(calls) > 1:
            raise AssertionError("gate reloaded unvalidated bytes")
        return data
    monkeypatch.setattr(module, "load_register", changing_register)
    assert check_gate(tmp_path, "ENG-001")[0] is False
    assert len(calls) == 1


def test_invalid_json_shapes_fail_closed(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    for value in (None, [], {"records": None}, {"records": 5}):
        (tmp_path / "planning/approvals.json").write_text(json.dumps(value))
        assert validate(tmp_path)["result"] == "fail"
        assert check_gate(tmp_path, "ENG-001")[0] is False


def test_nested_directory_cannot_borrow_parent_git_identity(tmp_path):
    git = _synthetic_git_register(tmp_path)
    nested = tmp_path / "nested"
    nested.mkdir()
    _copy_schema_and_catalog(nested)
    (nested / "planning/approvals.json").write_text((ROOT / "planning/approvals.json").read_text())
    result = validate(nested, expected_commit=git("rev-parse", "HEAD"))
    assert any("not the Git repository root" in e for e in result["errors"])


def test_cli_json_error_is_valid_json(tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT / "scripts/validate_approvals.py"),
                             "--root", str(tmp_path / 'missing"root'), "--json"],
                            text=True, capture_output=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)["result"] == "fail"


def test_open_target_rejects_each_unmet_dependency_state(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    target = next(r for r in data["records"] if r["id"] == "REV-001")
    for required in ("approved", "validated", "implementation-open", "activation-open"):
        target["dependencies"] = [{"id": "ENG-001", "required_gate": required}]
        (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
        assert validate(tmp_path)["result"] == "pass"
        opened, reason = check_gate(tmp_path, "REV-001")
        assert not opened and "dependency ENG-001 not satisfied" in reason
    target["dependencies"] = [{"id": "ADR-002", "required_gate": "implementation-open"}]
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    assert check_gate(tmp_path, "REV-001")[0]


def test_open_dependency_cannot_hide_its_blocked_prerequisite(tmp_path):
    _copy_schema_and_catalog(tmp_path)
    data = json.loads((ROOT / "planning/approvals.json").read_text())
    by_id = {r["id"]: r for r in data["records"]}
    by_id["ENG-001"]["dependencies"] = []
    by_id["ADR-002"]["dependencies"] = [{"id": "ENG-001", "required_gate": "implementation-open"}]
    by_id["REV-001"]["dependencies"] = [{"id": "ADR-002", "required_gate": "implementation-open"}]
    (tmp_path / "planning/approvals.json").write_text(json.dumps(data))
    assert validate(tmp_path)["result"] == "pass"
    opened, reason = check_gate(tmp_path, "REV-001")
    assert not opened and "dependency ENG-001 not satisfied" in reason
