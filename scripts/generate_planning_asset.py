#!/usr/bin/env python3
"""Generate a deterministic cockpit asset from the planning catalog.

Emits docs/prototypes/roadmap-portal/planning-data.js which assigns a global
variable so the prototype works under file:// without fetch/CORS. The asset is
the single derived source of status truth for the prototype.
"""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parent.parent


def derive_view(catalog: dict) -> dict:
    items = sorted(catalog.get("items", []), key=lambda i: i.get("id", ""))
    by_id = {i["id"]: i for i in items}

    def links(item):
        return [link for link in item.get("source_links", []) if link]

    plans = []
    decisions = []
    milestones = []
    lanes = []
    historical = []
    missing_gate = []
    for it in items:
        kind = it.get("kind")
        if kind == "plan" or kind == "checkpoint":
            plans.append(
                {
                    "id": it["id"],
                    "title": it.get("title"),
                    "status": it.get("status"),
                    "milestone": it.get("milestone"),
                    "owner": it.get("owner"),
                    "decision_state": it.get("decision_state"),
                    "sources": links(it),
                    "executable": it.get("executable"),
                }
            )
        elif kind == "decision":
            decisions.append(
                {
                    "id": it["id"],
                    "title": it.get("title"),
                    "state": it.get("decision_state"),
                    "status": it.get("status"),
                    "date": it.get("decision_date"),
                    "approver": it.get("approver"),
                }
            )
        elif kind == "roadmap_milestone":
            milestones.append(
                {"id": it["id"], "title": it.get("title"), "status": it.get("status")}
            )
        elif kind == "lane":
            lanes.append(
                {
                    "id": it["id"],
                    "title": it.get("title"),
                    "status": it.get("status"),
                    "deps": [
                        d.get("id")
                        for d in it.get("dependencies", [])
                        if isinstance(d, dict)
                    ],
                }
            )
        if it.get("status") in ("historical", "superseded"):
            historical.append(
                {
                    "id": it["id"],
                    "status": it.get("status"),
                    "successor": it.get("successor"),
                }
            )
        if (not it.get("quality_gates")) or it.get("evidence_state") in (None, "none"):
            missing_gate.append(it["id"])

    # Release 1A critical path = deps of the critical-path lane.
    release_1a = []
    for lane in lanes:
        if lane["id"] == "critical-path":
            release_1a = [by_id[d]["id"] for d in lane["deps"] if d in by_id]

    return {
        "generated_or_reviewed_at": catalog.get("generated_or_reviewed_at"),
        "schema_version": catalog.get("schema_version"),
        "milestones": milestones,
        "plans": plans,
        "decisions": decisions,
        "lanes": lanes,
        "release_1a_path": release_1a,
        "historical_or_superseded": historical,
        "missing_gate_items": missing_gate,
    }


def render_asset(catalog: dict) -> str:
    view = derive_view(catalog)
    body = json.dumps(view, ensure_ascii=False, indent=2, sort_keys=True)
    return "window.PLANNING_CATALOG = " + body + ";\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate the deterministic planning-cockpit asset"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that the checked asset matches the catalog without writing",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root (defaults to the generator's project root)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    catalog_path = root / "planning" / "catalog.json"
    out = root / "docs" / "prototypes" / "roadmap-portal" / "planning-data.js"
    if not catalog_path.is_file():
        sys.stderr.write("catalog not found: %s\n" % catalog_path)
        return 2
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    rendered = render_asset(catalog)
    if args.check:
        if not out.is_file():
            sys.stderr.write("planning asset not found: %s\n" % out)
            return 1
        if out.read_text(encoding="utf-8") != rendered:
            sys.stderr.write("planning asset is stale: %s\n" % out)
            return 1
        print("Planning asset is current:", out)
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print("Wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
