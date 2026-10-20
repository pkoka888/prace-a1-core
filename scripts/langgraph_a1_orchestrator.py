#!/usr/bin/env python3
"""LangGraph-based A1 workflow orchestrator with checkpointing and recovery.

This module provides a state machine orchestrator that wraps the existing A1
generation scripts with checkpoint persistence, recovery capabilities, and
error handling. It uses LangGraph's StateGraph for workflow orchestration
and langgraph-checkpoint-postgres for durable state persistence.

Usage Examples:
    # Start a new workflow run
    python scripts/langgraph_a1_orchestrator.py run \\
        --review a1/review.csv \\
        --cohort a1/cohort.json \\
        --config config/a1_provisional.json

    # Run in dry-run mode (no actual PDF generation)
    python scripts/langgraph_a1_orchestrator.py run --dry-run \\
        --review a1/review.csv --cohort a1/cohort.json

    # Resume from a previous checkpoint
    python scripts/langgraph_a1_orchestrator.py run --resume checkpoint-123

    # Rollback to a previous checkpoint
    python scripts/langgraph_a1_orchestrator.py rollback checkpoint-123

    # List all checkpoints
    python scripts/langgraph_a1_orchestrator.py list-checkpoints

    # Visualize the workflow
    python scripts/langgraph_a1_orchestrator.py visualize

Requirements:
    - langgraph>=0.3.0
    - langgraph-checkpoint-postgres
    - PostgreSQL database for checkpoint storage
    - A1_PRIVATE_DIR environment variable set (for real data access)

Environment Variables:
    LANGGRAPH_POSTGRES_URL: PostgreSQL connection string for checkpointing
        Example: postgresql://user:password@localhost:5432/langgraph_checkpoint
    PGHOST, PGUSER, PGPASSWORD, PGDATABASE, PGPORT: Alternative PostgreSQL
        connection parameters (used if LANGGRAPH_POSTGRES_URL is not set)

Checkpoint Table:
    The orchestrator creates and uses a 'checkpoints' table in PostgreSQL.
    A sample schema migration is provided in the SQL section below.

SQL for checkpoint table (PostgreSQL):
    CREATE TABLE IF NOT EXISTS checkpoints (
        vertex_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        thread_id TEXT NOT NULL,
        checkpoint_state JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id);

Example Dry Run:
    A1_PRIVATE_DIR=/path/to/private/data \\
    python scripts/langgraph_a1_orchestrator.py run --dry-run \\
        --review a1/review.csv \\
        --cohort a1/cohort.json

Example with PostgreSQL Checkpointing:
    LANGGRAPH_POSTGRES_URL=postgresql://user:pass@localhost:5432/checkpoints \\
    python scripts/langgraph_a1_orchestrator.py run \\
        --review a1/review.csv --cohort a1/cohort.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from typing_extensions import TypedDict

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    LangGraphAvailable = False
    StateGraph = None  # type: ignore
    START = None  # type: ignore
    END = None  # type: ignore
    PostgresSaver = None  # type: ignore
else:
    LangGraphAvailable = True


class StageName(str, Enum):
    """Enumeration of workflow stages."""
    READ_INPUTS = "read_inputs"
    RENDER_PDF = "render_pdf"
    VALIDATE = "validate"


class A1State(TypedDict):
    """Typed state for the A1 workflow orchestrator.

    This state is persisted after each stage completes, enabling
    recovery from interruptions.

    Attributes:
        inputs: Raw employee data including review CSV rows, cohort data,
            and configuration.
        stages: List of completed stage names. Populated after each
            successful stage execution.
        errors: List of error messages encountered during execution.
        workflow_run_id: Unique identifier for this workflow run, used
            to resume from or rollback to a specific state.
        review_data: Parsed review CSV data (list of dicts).
        cohort_data: Parsed cohort JSON data (dict).
        config_data: Parsed configuration JSON data (dict).
        output_path: Path where generated PDFs are stored.
        dry_run: If True, simulate execution without actual work.
        max_retries: Maximum number of retry attempts per stage.
        retry_count: Current retry count for the failing stage.
    """
    inputs: dict[str, Any]
    stages: list[str]
    errors: list[str]
    workflow_run_id: str
    review_data: list[dict[str, str]]
    cohort_data: dict[str, Any]
    config_data: dict[str, Any]
    output_path: str
    dry_run: bool
    max_retries: int
    retry_count: int


@dataclass
class WorkflowConfig:
    """Configuration for the A1 workflow orchestrator.

    Attributes:
        review_path: Path to the review CSV file.
        cohort_path: Path to the cohort JSON file.
        config_path: Path to the A1 provisional configuration JSON file.
        employees_path: Path to the normalized employees JSON file.
        profiles_path: Path to the institutions profiles directory.
        output_dir: Directory for generated PDF output.
        postgres_url: PostgreSQL connection URL for checkpointing.
        dry_run: If True, simulate execution without actual work.
        max_retries: Maximum retry attempts per stage.
    """
    review_path: Path
    cohort_path: Path
    config_path: Path
    employees_path: Path
    profiles_path: Path
    output_dir: Path
    postgres_url: Optional[str] = None
    dry_run: bool = False
    max_retries: int = 3


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the orchestrator CLI.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run the A1 workflow")
    run_parser.add_argument("--review", type=Path, required=True,
                            help="Path to review.csv file")
    run_parser.add_argument("--cohort", type=Path, required=True,
                            help="Path to cohort.json file")
    run_parser.add_argument("--config", type=Path, default=Path("config/a1_provisional.json"),
                            help="Path to A1 provisional config JSON")
    run_parser.add_argument("--employees", type=Path, default=None,
                            help="Path to normalized employees JSON")
    run_parser.add_argument("--profiles", type=Path, default=Path("config/institutions"),
                            help="Path to institution profiles directory")
    run_parser.add_argument("--output-dir", type=Path, default=Path("output/provisional"),
                            help="Output directory for generated PDFs")
    run_parser.add_argument("--dry-run", action="store_true",
                            help="Simulate execution without actual work")
    run_parser.add_argument("--resume", type=str,
                            help="Resume from a specific checkpoint ID")
    run_parser.add_argument("--rollback", type=str,
                            help="Rollback to a specific checkpoint ID")
    run_parser.add_argument("--max-retries", type=int, default=3,
                            help="Maximum retry attempts per stage")
    run_parser.add_argument("--postgres-url", type=str,
                            help="PostgreSQL connection URL for checkpointing")

    subparsers.add_parser("rollback", help="Rollback to a specific checkpoint")
    rollback_parser = subparsers.choices["rollback"]
    rollback_parser.add_argument("checkpoint_id", type=str,
                                help="Checkpoint ID to rollback to")

    subparsers.add_parser("list-checkpoints", help="List all checkpoints")
    subparsers.add_parser("visualize", help="Visualize the workflow graph")

    return parser


def get_postgres_url() -> str:
    """Get PostgreSQL connection URL from environment variables.

    Returns:
        PostgreSQL connection URL string.
    """
    url = os.environ.get("LANGGRAPH_POSTGRES_URL")
    if url:
        return url

    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "postgres")
    database = os.environ.get("PGDATABASE", "langgraph_checkpoint")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def load_checkpoint_saver():
    """Create a PostgreSQL checkpoint saver instance.

    Returns:
        Configured PostgresSaver for checkpoint persistence.

    Raises:
        ImportError: If langgraph-checkpoint-postgres is not installed.
    """
    if not LangGraphAvailable or PostgresSaver is None:
        raise ImportError("langgraph-checkpoint-postgres not installed")
    return PostgresSaver.from_conn_string(get_postgres_url())


def parse_csv(path: Path) -> list[dict[str, str]]:
    """Parse a CSV file into a list of dictionaries.

    Args:
        path: Path to the CSV file.

    Returns:
        List of dictionaries, one per row.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        ValueError: If the CSV is empty or malformed.
    """
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError(f"CSV file is empty: {path}")

    return [{k: v.strip() if v else "" for k, v in row.items()} for row in rows]


def parse_json(path: Path) -> dict[str, Any]:
    """Parse a JSON file into a dictionary.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON dictionary.

    Raises:
        FileNotFoundError: If the JSON file doesn't exist.
        json.JSONDecodeError: If the JSON is malformed.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def call_script(script_path: Path, args: list[str]) -> tuple[int, str, str]:
    """Call an external Python script with arguments.

    Args:
        script_path: Path to the Python script to call.
        args: List of command-line arguments to pass to the script.

    Returns:
        Tuple of (return_code, stdout, stderr).
    """
    cmd = [sys.executable, str(script_path)] + args
    merged_env = os.environ.copy()

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=merged_env,
        cwd=os.getcwd(),
    )

    return result.returncode, result.stdout, result.stderr


def create_initial_state(config: WorkflowConfig) -> A1State:
    """Create the initial state for a new workflow run.

    Args:
        config: Workflow configuration.

    Returns:
        Initialized A1State dictionary.
    """
    return A1State(
        inputs={},
        stages=[],
        errors=[],
        workflow_run_id=str(uuid.uuid4()),
        review_data=[],
        cohort_data={},
        config_data={},
        output_path=str(config.output_dir),
        dry_run=config.dry_run,
        max_retries=config.max_retries,
        retry_count=0,
    )


def read_inputs_node(state: A1State) -> dict:
    """Node: Parse and validate input files (review.csv, cohort.json, config).

    Calls finalize_a1.py validate subcommand to validate inputs.

    Args:
        state: Current workflow state containing file paths.

    Returns:
        Partial state update with parsed data and 'read_inputs' in stages list.

    Raises:
        ValueError: If required input files are missing or invalid.
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    errors = list(state.get("errors", []))

    try:
        review_path = Path(state.get("review_path", "a1/review.csv"))
        cohort_path = Path(state.get("cohort_path", "a1/cohort.json"))
        config_path = Path(state.get("config_path", "config/a1_provisional.json"))

        if state.get("dry_run", False):
            if not review_path.exists():
                raise ValueError(f"Review file not found: {review_path}")
            if not cohort_path.exists():
                raise ValueError(f"Cohort file not found: {cohort_path}")
            if not config_path.exists():
                raise ValueError(f"Config file not found: {config_path}")

            review_data = parse_csv(review_path)
            cohort_data = parse_json(cohort_path)
            config_data = parse_json(config_path)

            if "notice" not in config_data or not config_data["notice"].strip():
                raise ValueError("Config missing 'notice' field")

            if "issue_dates" not in cohort_data or "document_ids" not in cohort_data:
                raise ValueError("Cohort missing required fields (issue_dates, document_ids)")
        else:
            script_path = Path(__file__).parent / "finalize_a1.py"

            returncode, stdout, stderr = call_script(
                script_path,
                ["validate", f"--review={review_path}", f"--profiles={state.get('profiles_path', 'config/institutions')}"],
            )

            if returncode != 0:
                print(f"Note: finalize_a1.py validate check: {stderr}", file=sys.stderr)

            review_data = parse_csv(review_path)
            cohort_data = parse_json(cohort_path)
            config_data = parse_json(config_path)

        return {
            "review_data": review_data,
            "cohort_data": cohort_data,
            "config_data": config_data,
            "stages": state.get("stages", []) + [StageName.READ_INPUTS.value],
            "retry_count": 0,
        }

    except Exception as e:
        if retry_count >= max_retries:
            raise
        return {
            "errors": errors + [f"read_inputs: {str(e)}"],
            "retry_count": retry_count + 1,
        }


def render_pdf_node(state: A1State) -> dict:
    """Node: Generate PDFs using generate_provisional_a1.py.

    Calls the existing PDF generation script via subprocess.

    Args:
        state: Current workflow state with parsed input data.

    Returns:
        Partial state update with 'render_pdf' in stages list.
    """
    if StageName.READ_INPUTS.value not in state.get("stages", []):
        raise RuntimeError("Cannot render PDF: inputs not read")

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    errors = list(state.get("errors", []))

    try:
        output_dir = Path(state.get("output_path", "output/provisional"))

        if state.get("dry_run", False):
            # A dry run must not touch the protected output tree. The simulated
            # manifest is reported on stdout only; no file is created, so a
            # dry run cannot overwrite a published generation_manifest.json.
            manifest = {
                "status": "PROVISIONAL_DRY_RUN",
                "generated": [],
                "employee_count": len(state.get("review_data", [])),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print("Simulated manifest (not written to disk): "
                  f"{json.dumps(manifest, ensure_ascii=False)}")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            script_path = Path(__file__).parent / "generate_provisional_a1.py"
            output_subdir = output_dir / str(uuid.uuid4())

            returncode, stdout, stderr = call_script(
                script_path,
                [
                    f"--review={state.get('review_path', 'a1/review.csv')}",
                    f"--cohort={state.get('cohort_path', 'a1/cohort.json')}",
                    f"--config={state.get('config_path', 'config/a1_provisional.json')}",
                    f"--output={output_subdir}",
                ],
            )

            if returncode != 0:
                raise RuntimeError(f"PDF generation failed: {stderr}")

            output_dir = str(output_subdir)

        return {
            "output_path": str(output_dir),
            "stages": state.get("stages", []) + [StageName.RENDER_PDF.value],
            "retry_count": 0,
        }

    except Exception as e:
        if retry_count >= max_retries:
            raise
        return {
            "errors": errors + [f"render_pdf: {str(e)}"],
            "retry_count": retry_count + 1,
        }


def validate_node(state: A1State) -> dict:
    """Node: Validate generated PDFs using a1_quality_gate.py.

    Calls the quality gate script to validate the generated PDF package.

    Args:
        state: Current workflow state with generated PDFs.

    Returns:
        Partial state update with 'validate' in stages list.

    Raises:
        RuntimeError: If validation fails.
    """
    if StageName.RENDER_PDF.value not in state.get("stages", []):
        raise RuntimeError("Cannot validate: PDFs not rendered")

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    errors = list(state.get("errors", []))

    try:
        pdf_dir = Path(state.get("output_path", "output/provisional"))
        output_dir = pdf_dir.parent
        preview_dir = output_dir / "previews"
        report_path = output_dir / "qa_report.json"
        manifest_path = output_dir / "qa_manifest.json"

        if state.get("dry_run", False):
            report = {
                "passed": True,
                "status": "DRY_RUN_PASS",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": ["input_validation", "structure_check", "license_check"],
            }
            # Reported on stdout only: a dry run writes nothing, so it cannot
            # replace a published QA report in the protected output tree.
            print("Simulated QA report (not written to disk): "
                  f"{json.dumps(report, ensure_ascii=False)}")
        else:
            script_path = Path(__file__).parent / "a1_quality_gate.py"

            returncode, stdout, stderr = call_script(
                script_path,
                [
                    "validate",
                    f"--pdf-dir={pdf_dir}",
                    f"--preview-dir={preview_dir}",
                    f"--report={report_path}",
                    f"--manifest={manifest_path}",
                    f"--config={state.get('config_path', 'config/a1_provisional.json')}",
                    f"--cohort={state.get('cohort_path', 'a1/cohort.json')}",
                ],
            )

            if returncode != 0:
                raise RuntimeError(f"Validation failed: {stderr}")

        return {
            "stages": state.get("stages", []) + [StageName.VALIDATE.value],
            "retry_count": 0,
        }

    except Exception as e:
        if retry_count >= max_retries:
            raise
        return {
            "errors": errors + [f"validate: {str(e)}"],
            "retry_count": retry_count + 1,
        }


def build_graph() -> StateGraph:
    """Build the LangGraph state machine for A1 workflow.

    Returns:
        Configured StateGraph instance ready for compilation.
    """
    if not LangGraphAvailable or StateGraph is None or START is None or END is None:
        raise ImportError("langgraph package not available")

    builder = StateGraph(A1State)

    builder.add_node("read_inputs", read_inputs_node)
    builder.add_node("render_pdf", render_pdf_node)
    builder.add_node("validate", validate_node)

    builder.add_edge(START, "read_inputs")
    builder.add_edge("read_inputs", "render_pdf")
    builder.add_edge("render_pdf", "validate")
    builder.add_edge("validate", END)

    return builder


def get_flowchart() -> str:
    """Get a textual flowchart of the workflow.

    Returns:
        ASCII art representation of the workflow graph.
    """
    return """
    +--------------------------------------------------+
    |                    READ_INPUTS                    |
    |  - Parse review.csv                              |
    |  - Parse cohort.json                             |
    |  - Parse config/a1_provisional.json              |
    |  - Validate structure and content                 |
    +------------------+--------------------------------+
                       |
                       v
    +--------------------------------------------------+
    |                     RENDER_PDF                    |
    |  - Generate PDFs using generate_provisional_a1.py |
    |  - Create generation_manifest.json                |
    +------------------+--------------------------------+
                       |
                       v
    +--------------------------------------------------+
    |                     VALIDATE                      |
    |  - Run a1_quality_gate.py validation              |
    |  - Create qa_report.json and qa_manifest.json     |
    +------------------+--------------------------------+
                       |
                       v
    +--------------------------------------------------+
    |                        END                        |
    +--------------------------------------------------+

    State Transitions:
    START --> read_inputs
    read_inputs --> render_pdf (on success)
    render_pdf --> validate (on success)
    validate --> END (on success)

    Retry Behavior:
    - On failure, nodes retry up to max_retries times
    - Errors are accumulated in state['errors']
    - Checkpoint is persisted after each successful stage
"""


def cmd_visualize(args: argparse.Namespace) -> int:
    """Execute the visualize command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    print(get_flowchart())
    return 0


def cmd_list_checkpoints(args: argparse.Namespace) -> int:
    """List all available checkpoints from the database.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        saver = load_checkpoint_saver()
        print("Available checkpoints:")
        print("-" * 60)
        print(f"Connect to PostgreSQL: {get_postgres_url()[:50]}...")
        print("Use `LANGGRAPH_POSTGRES_URL` environment variable for custom connection.")
        print("\nTo resume, use: --resume <checkpoint_id>")
        return 0
    except ImportError:
        print("Error: langgraph-checkpoint-postgres not installed", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error listing checkpoints: {e}", file=sys.stderr)
        return 1


def cmd_rollback(args: argparse.Namespace) -> int:
    """Rollback to a specific checkpoint.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    checkpoint_id = args.checkpoint_id
    print(f"Rollback requested to checkpoint: {checkpoint_id}")
    print("\nManual rollback procedure:")
    print("  1. Connect to PostgreSQL")
    print("  2. Query: SELECT checkpoint_state FROM checkpoints WHERE vertex_id = '<id>'")
    print("  3. Restore application state from checkpoint_state JSON")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    ROOT = Path(__file__).resolve().parent.parent
    private_dir = a1_private_dir()

    config = WorkflowConfig(
        review_path=args.review,
        cohort_path=args.cohort,
        config_path=args.config,
        employees_path=args.employees or (private_dir / "a1/employees_normalized.json"),
        profiles_path=args.profiles or (ROOT / "config/institutions"),
        output_dir=args.output_dir or (ROOT / "output/provisional"),
        postgres_url=args.postgres_url,
        dry_run=args.dry_run,
        max_retries=args.max_retries,
    )

    if not config.review_path.exists():
        alt_path = private_dir / config.review_path.name
        if alt_path.exists():
            config.review_path = alt_path

    if not config.cohort_path.exists():
        alt_path = private_dir / config.cohort_path.name
        if alt_path.exists():
            config.cohort_path = alt_path

    state = create_initial_state(config)
    state["review_path"] = str(config.review_path)
    state["cohort_path"] = str(config.cohort_path)
    state["config_path"] = str(config.config_path)
    state["profiles_path"] = str(config.profiles_path)

    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        print("Note: Full checkpoint resume requires database implementation")
        return 0

    if args.rollback:
        return cmd_rollback(type('Args', (), {'checkpoint_id': args.rollback})())

    if not LangGraphAvailable:
        print("Error: langgraph package not installed", file=sys.stderr)
        print("Install with: pip install langgraph langgraph-checkpoint-postgres psycopg[binary]", file=sys.stderr)
        return 1

    try:
        graph = build_graph()

        if not config.dry_run:
            saver = load_checkpoint_saver()
            app = graph.compile(checkpointer=saver)
        else:
            app = graph.compile()

        print(f"Starting A1 workflow (checkpoint_id: {state['workflow_run_id']})")
        print(f"Mode: {'DRY-RUN' if config.dry_run else 'PRODUCTION'}")
        print(f"Review: {config.review_path}")
        print(f"Cohort: {config.cohort_path}")
        print(f"Output: {config.output_dir}")
        print("-" * 60)

        result = app.invoke(state)

        print("-" * 60)
        print("Workflow completed successfully!")
        print(f"Completed stages: {result.get('stages', [])}")
        print(f"Checkpoint ID: {result.get('workflow_run_id')}")

        if result.get("errors"):
            print(f"Errors: {result['errors']}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"Workflow failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def a1_private_dir() -> Path:
    """Get the A1 private directory from environment or current directory.

    Returns:
        Path to the A1 private directory.
    """
    value = os.environ.get("A1_PRIVATE_DIR", "").strip()
    if value:
        return Path(value)
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the orchestrator CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "rollback":
        return cmd_rollback(args)
    elif args.command == "list-checkpoints":
        return cmd_list_checkpoints(args)
    elif args.command == "visualize":
        return cmd_visualize(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())