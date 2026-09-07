#!/usr/bin/env python3
"""Read-only validator for collector-execution-1.2 proposal artifacts.

Exit 2 is the successful validation outcome because v1.2 deliberately carries
collector proposals only.  Exit 1 means invalid; exit 2 also covers a missing
local dependency, distinguished by the structured status.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.run_collector_proposals_v12 import (
        OUTPUT_SCHEMA_REF,
        ROOT,
        InvalidProposal,
        MissingDependency,
        check_binding,
        contained,
        read_json,
        semantic_sha256,
        validate_and_build,
        validate_schema,
    )
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from run_collector_proposals_v12 import (  # type: ignore[no-redef]
        OUTPUT_SCHEMA_REF,
        ROOT,
        InvalidProposal,
        MissingDependency,
        check_binding,
        contained,
        read_json,
        semantic_sha256,
        validate_and_build,
        validate_schema,
    )


def validate_execution(root: Path, execution: dict) -> None:
    validate_schema(execution, read_json(contained(root, OUTPUT_SCHEMA_REF)), "execution")
    check_binding(root, execution["contract_schema"], OUTPUT_SCHEMA_REF)
    proposal = {
        "format_version": "collector-proposal-input-1.1",
        "run_id": execution["run_id"],
        "execution_instance_id": execution["execution_instance_id"],
        "query_pack": execution["query_pack"],
        "protocol": execution["protocol"],
        "normalization_rules": execution["normalization_rules"],
        "capture_manifests": execution["capture_manifests"],
        "collector": execution["collector"],
        "inspections": [
            {key: value for key, value in row.items() if key != "observations"} |
            {"observations": [{key: value for key, value in observation.items() if key != "authority_classification"} for observation in row["observations"]]}
            for row in execution["inspections"]
        ],
    }
    rebuilt, _ = validate_and_build(root, proposal)
    if semantic_sha256(rebuilt) != semantic_sha256(execution):
        raise InvalidProposal("execution differs from deterministic reconstruction")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        execution = read_json(contained(root, args.input))
        validate_execution(root, execution)
        result = {"status": "valid-provisional", "authority_classification": "collector_proposed", "exit_code": 2}
        print(json.dumps(result) if args.json else "UNPROVEN — valid collector proposal; operator review remains required")
        return 2
    except InvalidProposal as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}) if args.json else f"FAIL — {exc}")
        return 1
    except (MissingDependency, OSError) as exc:
        print(json.dumps({"status": "unavailable", "error": str(exc)}) if args.json else f"UNPROVEN — {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
