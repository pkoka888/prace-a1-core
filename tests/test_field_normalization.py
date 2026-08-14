from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/validate_field_normalization.py"
RULES = "research/query-packs/field-normalization-1.0.json"
SCHEMA = "research/query-packs/field-normalization-1.0.schema.json"
PACK = "research/query-packs/plan-ac-core-1.1.json"
PROPOSAL_SCHEMA = "research/query-packs/field-normalization-proposal-1.0.schema.json"


def project(tmp_path: Path) -> Path:
    for relative in (SCRIPT, RULES, SCHEMA, PACK, PROPOSAL_SCHEMA):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / SCRIPT), "--root", str(root), "--json", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def mutate(root: Path, change) -> None:
    path = root / RULES
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    semantic = dict(value)
    semantic.pop("ruleset_hash", None)
    value["ruleset_hash"] = hashlib.sha256(
        json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_canonical_rules_validate_deterministically_and_read_only(tmp_path: Path) -> None:
    root = project(tmp_path)
    before = {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
              for path in (RULES, SCHEMA, PACK)}
    first = run(root)
    second = run(root)
    assert first.returncode == second.returncode == 0, first.stderr
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload["result"] == "pass"
    assert payload["authority"] == "proposal-only-operator-review-required"
    assert payload["query_pack_hash"] == "69ea1e988271dafaaea0ea84cc75e6eac8ad7c884ec4f66212ce57a3a68a3819"
    assert payload["operator_review_required"] is True
    assert payload["ruleset_hash"] == "7505ac4b1007b654bd2fbf9595383f766be3fabc292600b984e7264ea4460672"
    assert {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
            for path in (RULES, SCHEMA, PACK)} == before


def load_module(root: Path):
    spec = importlib.util.spec_from_file_location("field_normalization", root / SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_proposals_are_typed_scoped_and_non_authoritative(tmp_path: Path) -> None:
    root = project(tmp_path)
    module = load_module(root)
    rules = json.loads((root / RULES).read_text(encoding="utf-8"))
    evidence = {
        "evidence_id": "synthetic-public-evidence-1",
        "source_url": "https://example.com/public-fixture",
        "locator": "line:1",
        "context": "Synthetic public context for deterministic normalization.",
    }
    fixtures = [
        ("oss_invoice", "oss-docling", "license_spdx", " MIT ", "MIT"),
        ("czech_invoice_software", "vendor-idoklad", "public_api", " Veřejné API ", True),
        ("oss_invoice", "oss-doctr", "invoice_extraction_level",
         "GENERIC DOCUMENT STRUCTURE", "generic_document_structure"),
        ("czech_invoice_software", "vendor-wflow", "pricing", "Kč", "CZK"),
        ("czech_invoice_software", "vendor-fakturoid", "accounting_system_ids",
         "Fakturoid.cz", "fakturoid"),
        ("czech_invoice_software", "vendor-raya", "export_format_ids", "XML", "xml"),
    ]
    for lane, entity, field, raw, expected in fixtures:
        proposals = module.proposal_for(
            rules, lane=lane, entity_id=entity, field_id=field, raw_value=raw,
            evidence=evidence,
            pricing_context=(
                {"vat_status": "included", "billing_period": "monthly", "unit": "invoice"}
                if field == "pricing" else None
            ),
        )
        assert len(proposals) == 1
        assert proposals[0]["proposed_value"] == expected
        assert proposals[0]["status"] == "awaiting_operator_review"
        assert proposals[0]["authority"] == "proposal-only-non-authoritative"
        assert proposals[0]["operator_review_required"] is True
        assert proposals[0]["raw_value_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
        assert proposals[0]["evidence_locator"]["context_sha256"] == hashlib.sha256(
            evidence["context"].encode()
        ).hexdigest()
        import jsonschema
        schema = json.loads((root / PROPOSAL_SCHEMA).read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(proposals[0])
    assert module.proposal_for(
        rules, lane="czech_invoice_software", entity_id="vendor-idoklad",
        field_id="accounting_system_ids", raw_value="Fakturoid.cz", evidence=evidence,
    ) == []


def test_isolated_currency_is_not_an_actionable_proposal(tmp_path: Path) -> None:
    root = project(tmp_path)
    module = load_module(root)
    rules = json.loads((root / RULES).read_text(encoding="utf-8"))
    evidence = {
        "evidence_id": "currency-only",
        "source_url": "https://example.com/currency",
        "locator": "line:2",
        "context": "Kč",
    }
    assert module.proposal_for(
        rules, lane="czech_invoice_software", entity_id="vendor-wflow",
        field_id="pricing", raw_value="Kč", evidence=evidence,
    ) == []
    assert module.proposal_for(
        rules, lane="czech_invoice_software", entity_id="vendor-wflow",
        field_id="pricing", raw_value="Kč", evidence=evidence,
        pricing_context={"vat_status": "included", "billing_period": "monthly", "unit": "invoice"},
    )[0]["proposed_value"] == "CZK"


def test_overlap_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    def change(doc):
        doc["rules"][2]["input"]["values"].append("public api")
    mutate(root, change)
    result = run(root)
    assert result.returncode == 1
    assert "ambiguous/overlapping" in json.loads(result.stderr)["message"]


def test_unscoped_entity_and_field_are_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["rules"][0]["scope"]["entity_ids"].__setitem__(0, "vendor-fakturoid"))
    result = run(root)
    assert result.returncode == 1
    assert "unscoped entity" in json.loads(result.stderr)["message"]

    root = project(tmp_path / "field")
    mutate(root, lambda doc: doc["rules"][0]["scope"].__setitem__("field_id", "invented_field"))
    result = run(root)
    assert result.returncode == 1
    assert "unscoped field" in json.loads(result.stderr)["message"]


def test_invented_controlled_output_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["rules"][3]["output"].__setitem__("value", "magic_invoice_ai"))
    result = run(root)
    assert result.returncode == 1
    assert "outside the bound controlled vocabulary" in json.loads(result.stderr)["message"]


def test_unsafe_regex_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["rules"][-1]["input"].__setitem__("patterns", ["^(.*)+$"]))
    result = run(root)
    assert result.returncode == 1
    assert "unsafe or non-enumerable regex" in json.loads(result.stderr)["message"]


def test_pricing_requires_vat_billing_period_and_unit(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["rules"][7]["required_pricing_context"].pop("vat_status"))
    result = run(root)
    assert result.returncode == 1
    message = json.loads(result.stderr)["message"]
    assert "vat_status" in message or "VAT status" in message


def test_fake_spdx_identifier_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    def change(doc):
        doc["spdx_allowlist"]["identifiers"].append("Definitely-Fake-9.9")
        doc["rules"][0]["input"]["values"].append("Definitely-Fake-9.9")
    mutate(root, change)
    result = run(root)
    assert result.returncode == 1
    # A syntactically plausible token is still outside the frozen validator-owned subset.
    assert "SPDX" in json.loads(result.stderr)["message"]


def test_mixed_profiles_reject_mit_casefold_ambiguity(tmp_path: Path) -> None:
    root = project(tmp_path)
    def change(doc):
        duplicate = json.loads(json.dumps(doc["rules"][0]))
        duplicate["id"] = "spdx-casefold-ambiguous"
        duplicate["input"] = {
            "normalization_profile": "text_casefold",
            "match_mode": "exact_value",
            "values": ["mit"],
        }
        doc["rules"].append(duplicate)
    mutate(root, change)
    result = run(root)
    assert result.returncode == 1
    assert "mixed normalization profiles" in json.loads(result.stderr)["message"]


def test_sparse_coverage_partition_must_be_exact(tmp_path: Path) -> None:
    root = project(tmp_path)
    mutate(root, lambda doc: doc["coverage"]["uncovered_fields"]["oss_invoice"].remove("github_stars"))
    result = run(root)
    assert result.returncode == 1
    assert "coverage partition" in json.loads(result.stderr)["message"]


def test_query_pack_byte_and_semantic_binding_are_enforced(tmp_path: Path) -> None:
    root = project(tmp_path)
    pack_path = root / PACK
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    pack["source_policy_version"] = "tampered"
    pack_path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = run(root)
    assert result.returncode == 1
    assert "byte hash binding mismatch" in json.loads(result.stderr)["message"]


def test_missing_local_dependency_is_unproven(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / PACK).unlink()
    result = run(root)
    assert result.returncode == 2
    assert json.loads(result.stderr)["result"] == "unproven"


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    root = project(tmp_path)
    result = run(root, "--input", "../rules.json")
    assert result.returncode == 1
    assert "escapes --root" in json.loads(result.stderr)["message"]
