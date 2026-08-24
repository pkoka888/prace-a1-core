#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.free_model_eval.core import EXIT_FAILURE, EXIT_OK, EXIT_UNPROVEN, EvalFailure, EvalUnproven, canonical_bytes, load_json
from src.free_model_eval.engine import preflight, run_one, run_af2_one, validate_af2_run, validate_run, verify_fixtures


def write_json(path: Path, value: dict) -> None:
    path = path if path.is_absolute() else ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded synthetic free-model evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify-fixtures", "preflight"):
        item = sub.add_parser(name); item.add_argument("--policy", required=True); item.add_argument("--output")
    run = sub.add_parser("run"); run.add_argument("--policy", required=True); run.add_argument("--models", nargs="+", required=True); run.add_argument("--repetitions", type=int, required=True); run.add_argument("--output", required=True)
    val = sub.add_parser("validate"); val.add_argument("--policy", required=True); val.add_argument("--run-dir", required=True)
    report = sub.add_parser("report"); report.add_argument("--run-dir", required=True); report.add_argument("--template", required=True); report.add_argument("--output", required=True)
    af2 = sub.add_parser("run-af2"); af2.add_argument("--policy", required=True); af2.add_argument("--models", nargs="+", required=True); af2.add_argument("--output", required=True)
    af2v = sub.add_parser("validate-af2"); af2v.add_argument("--policy", required=True); af2v.add_argument("--run-dir", required=True)
    af21 = sub.add_parser("run-af21"); af21.add_argument("--policy", required=True); af21.add_argument("--models", nargs="+", required=True); af21.add_argument("--output", required=True)
    af21v = sub.add_parser("validate-af21"); af21v.add_argument("--policy", required=True); af21v.add_argument("--run-dir", required=True)
    args = parser.parse_args(); policy = load_json(ROOT / args.policy) if hasattr(args, "policy") else None
    try:
        if args.command == "verify-fixtures": result, status = verify_fixtures(ROOT, policy), EXIT_OK
        elif args.command == "preflight": result, status = preflight(ROOT, policy)
        elif args.command in {"run-af2","run-af21"}:
            if not policy.get("af2_trace_only"): raise EvalFailure("AF2 trace-only policy required")
            if args.models != policy["free_models"]: raise EvalFailure("AF2 model list/order must exactly match policy")
            run_root=(ROOT/args.output).resolve()
            if args.command=="run-af2":
                expected=(ROOT/policy["runtime_root"] / "af2/latest").resolve()
                if run_root != expected: raise EvalFailure("AF2 output must be exact policy af2/latest path")
            else:
                parent=(ROOT/policy["runtime_root"] / "af2.1/runs").resolve()
                if run_root.parent != parent or not re.fullmatch(r"af21-[a-z0-9_-]+",run_root.name):
                    raise EvalFailure("AF2.1 output must be a named direct child of runtime/free-model-eval/af2.1/runs")
            if run_root.exists() and any(run_root.iterdir()): raise EvalFailure("AF2 output run directory must be empty")
            run_root.mkdir(parents=True,exist_ok=True)
            pf,pf_status=preflight(ROOT,policy); write_json(Path(args.output)/"preflight.json",pf)
            if pf_status: return pf_status
            smokes={}; receipts=[]
            def execute(runner_name, model, repetition):
                receipt=status=None
                for attempt in range(1,policy["transient_retry_count"]+2):
                    receipt,status=run_af2_one(ROOT,policy,pf,runner_name,model,repetition,run_root,attempt=attempt)
                    receipts.append(receipt)
                    if status!=EXIT_UNPROVEN or attempt>policy["transient_retry_count"]:
                        break
                    time.sleep(policy["transient_retry_backoff_seconds"])
                return receipt,status
            for model in policy["free_models"]:
                receipt,status=execute("opencode",model,1); smokes[model]=receipt["disposition"]
            passing=[model for model in policy["free_models"] if smokes[model]=="candidate"]
            if not passing:
                result={"status":"blocked-by-smoke","receipt_count":len(receipts),"smoke":smokes}
                print(json.dumps(result,ensure_ascii=False,indent=2)); return EXIT_FAILURE if "rejected" in smokes.values() else EXIT_UNPROVEN
            for model in passing:
                for repetition in (2,3):
                    receipt,_=execute("opencode",model,repetition)
                    if receipt["disposition"]!="candidate": break
            luna=policy["codex_control"].removeprefix("codex/")
            for repetition in (1,2,3):
                receipt,_=execute("codex",luna,repetition)
                if receipt["disposition"]!="candidate": break
            result,status=validate_af2_run(ROOT,run_root)
        elif args.command in {"validate-af2","validate-af21"}:
            if args.command=="validate-af21":
                resolved=(ROOT/args.run_dir).resolve(); parent=(ROOT/policy["runtime_root"] / "af2.1/runs").resolve()
                if resolved.parent != parent: raise EvalFailure("AF2.1 run directory outside immutable run root")
            result,status=validate_af2_run(ROOT,(ROOT/args.run_dir).resolve())
        elif args.command == "run":
            if args.repetitions != policy["repetitions"]: raise EvalFailure("repetition count must match policy")
            expected = policy["free_models"] + [policy["codex_control"]]
            if args.models != expected: raise EvalFailure("model list/order must exactly match policy")
            run_root = (ROOT / args.output).resolve(); runtime = (ROOT / policy["runtime_root"]).resolve()
            if run_root != runtime / "latest": raise EvalFailure("output must be exact policy runtime latest path")
            if run_root.exists() and any(run_root.iterdir()): raise EvalFailure("output run directory must be empty")
            run_root.mkdir(parents=True, exist_ok=True)
            pf, pf_status = preflight(ROOT, policy); write_json(Path(args.output) / "preflight.json", pf)
            if pf_status: return pf_status
            receipts=[]; statuses=[]
            # Both free models must pass one trace smoke before any matrix work.
            smoke = {}
            for requested in policy["free_models"]:
                receipt, status = run_one(ROOT, policy, pf, "trace", "opencode", requested, 1, run_root)
                receipts.append(receipt); statuses.append(status); smoke[requested] = receipt["disposition"]
            if any(value != "candidate" for value in smoke.values()):
                result={"status":"blocked-by-smoke","receipt_count":len(receipts),"smoke":smoke}
                print(json.dumps(result,ensure_ascii=False,indent=2)); return EXIT_FAILURE if "rejected" in smoke.values() else EXIT_UNPROVEN
            for requested in args.models:
                runner = "codex" if requested.startswith("codex/") else "opencode"; model = requested.split("/",1)[1] if runner == "codex" else requested
                for task in policy["tasks"]:
                    start = 2 if runner == "opencode" and task == "trace" else 1
                    for repetition in range(start, args.repetitions + 1):
                        receipt, status = run_one(ROOT, policy, pf, task, runner, model, repetition, run_root); receipts.append(receipt); statuses.append(status)
                        if status != EXIT_OK: break
            result={"status":"complete","receipt_count":len(receipts),"candidate_count":sum(r["disposition"]=="candidate" for r in receipts)}
            status=EXIT_OK if statuses and all(x==EXIT_OK for x in statuses) else (EXIT_FAILURE if EXIT_FAILURE in statuses else EXIT_UNPROVEN)
        elif args.command == "validate": result, status = validate_run(ROOT, (ROOT / args.run_dir).resolve())
        else:
            run_dir=(ROOT/args.run_dir).resolve(); summary,status=validate_run(ROOT,run_dir)
            template=(ROOT/args.template).read_text(encoding="utf-8")
            rendered=template.replace("{{ run_id }}",run_dir.name).replace("{{ reviewed_at }}","pending Codex review").replace("{{ preflight }}",json.dumps(load_json(run_dir/"preflight.json"),ensure_ascii=False,indent=2)).replace("{{ results }}",json.dumps(summary,ensure_ascii=False,indent=2)).replace("{{ dispositions }}","Provisional; inspect every receipt.")
            output=(ROOT/args.output).resolve(); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(rendered,encoding="utf-8"); result={"status":"written","output":str(output)}
        if getattr(args,"output",None) and args.command in {"verify-fixtures","preflight"}: write_json(Path(args.output),result)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return status
    except EvalFailure as exc: print(json.dumps({"status":"failed","errors":[str(exc)]})); return EXIT_FAILURE
    except EvalUnproven as exc: print(json.dumps({"status":"unproven","errors":[str(exc)]})); return EXIT_UNPROVEN


if __name__ == "__main__": raise SystemExit(main())
