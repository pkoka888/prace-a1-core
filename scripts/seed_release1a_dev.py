#!/usr/bin/env python3
"""seed_release1a_dev.py — Seed (or verify) the synthetic Release 1A DB.

Reads: tests/fixtures/release_1a/*.json
Verifies: manifest.json fixture_hashes (SHA-256) before any read or write
Containment: protected-path guard blocks any a1/scans/ocr/evidence/secrets access

Settings modules accepted (one of):
  - portal.settings_synthetic_review        (legacy review shell)
  - portal.settings_supervised_synthetic    (consolidated plan §4.2 supervised env)
  - portal.settings_verification           (Release 1A verification harness)
All three set M2_SYNTHETIC_ONLY=True; the script refuses any other module.

Modes:
  --dry-run   verify manifest hashes + simulate seeding; no DB writes
  --apply     write via Django ORM (idempotent: update_or_create on natural keys)
  --verify    read approved fixtures, compare against current DB state, exit
              non-zero on any discrepancy. Never writes database rows.

Usage:
  DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review venv/bin/python \
      scripts/seed_release1a_dev.py --dry-run
  DJANGO_SETTINGS_MODULE=portal.settings_supervised_synthetic venv/bin/python \
      scripts/seed_release1a_dev.py --apply
  DJANGO_SETTINGS_MODULE=portal.settings_synthetic_review venv/bin/python \
      scripts/seed_release1a_dev.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

FIXTURE_DIR = REPO_ROOT / "tests/fixtures/release_1a"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"

ALLOWED_SETTINGS_MODULES = frozenset({
    "portal.settings_synthetic_review",
    "portal.settings_supervised_synthetic",
    "portal.settings_verification",
})

# Field mapping: legacy fixture vocabulary to the model's enum values.
ACTIVITY_FIXTURE_TO_MODEL = {
    "OSVČ": "self_employed",
    "osvc": "self_employed",
    "zaměstnanec": "employee",
    "zamestnanec": "employee",
}
STATE_FIXTURE_TO_MODEL = {
    "active": "active",
    "inactive": "archived",
    "draft": "draft",
}


class ProtectedPathAccessed(Exception):
    pass


class SettingsModuleRejected(Exception):
    pass


PROTECTED_PATH_TOKENS = (
    "a1/", "scans/", "evidence/", "ocr/", "data/",
    "employees/scans/", "output/", "runtime/portal/real",
    "secrets/.env", "secrets/synthetic_review.key",
)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _protected_path_guard(value) -> None:
    if isinstance(value, str):
        for tok in PROTECTED_PATH_TOKENS:
            if tok in value:
                raise ProtectedPathAccessed(f"attempted to access protected path: {value}")
    elif isinstance(value, list):
        for v in value:
            _protected_path_guard(v)
    elif isinstance(value, dict):
        for v in value.values():
            _protected_path_guard(v)


def _setup_django():
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if not settings_module:
        raise SettingsModuleRejected("DJANGO_SETTINGS_MODULE must be set.")
    if settings_module not in ALLOWED_SETTINGS_MODULES:
        raise SettingsModuleRejected(
            f"DJANGO_SETTINGS_MODULE {settings_module!r} is not a sanctioned synthetic-only module."
        )
    import django  # noqa: E402
    django.setup()
    from django.conf import settings  # noqa: E402
    if not getattr(settings, "M2_SYNTHETIC_ONLY", False):
        raise SettingsModuleRejected(
            f"{settings_module} does not set M2_SYNTHETIC_ONLY=True; refusing to seed."
        )
    return settings


def _verify_manifest() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text())
    fixture_files = manifest.get("fixture_files", [])
    stored_hashes = manifest.get("fixture_hashes", {})
    if not fixture_files:
        raise ValueError("manifest.json has no fixture_files")
    for fname in fixture_files:
        fpath = FIXTURE_DIR / fname
        if not fpath.exists():
            raise FileNotFoundError(f"fixture file missing: {fname}")
        actual = _hash_file(fpath)
        expected = stored_hashes.get(fname, "")
        if actual != expected:
            raise ValueError(
                f"{fname} hash mismatch (expected {expected[:16]}… got {actual[:16]}…)"
            )
    return manifest


def _load_json(fname: str):
    with (FIXTURE_DIR / fname).open(encoding="utf-8") as fh:
        return json.load(fh)


class Seeder:
    """Reads approved fixtures and either writes or compares against the DB.

    State is held in self.* dicts so that verify_seeded_db can reference the
    same natural keys that seed_all uses.
    """

    def __init__(self) -> None:
        self.orgs: dict[str, object] = {}
        self.workers: dict[str, object] = {}
        self.documents: dict[str, object] = {}

    def _build_indexes(self) -> None:
        """Load fixtures and build natural-key indexes for cross-record lookups.

        Populates self.orgs and self.workers so the verify path can resolve
        fixture references without needing the seed path's DB writes.
        """
        _protected_path_guard(_load_json("organizations.json"))
        _protected_path_guard(_load_json("users.json"))
        _protected_path_guard(_load_json("workers.json"))
        _protected_path_guard(_load_json("documents.json"))
        _protected_path_guard(_load_json("assignments.json"))
        _protected_path_guard(_load_json("a1_inputs.json"))

        self.fixture_orgs = _load_json("organizations.json")
        self.fixture_workers = _load_json("workers.json")
        self.fixture_assignments = _load_json("assignments.json")
        self.fixture_a1_inputs = _load_json("a1_inputs.json")
        # Populate lookup dicts from fixtures (verify path needs these without
        # requiring a prior seed).
        self.orgs = {row["id"]: row for row in self.fixture_orgs}
        self.workers = {row["id"]: row for row in self.fixture_workers}

    # ------------------------------------------------------------------
    # Apply path: write to DB.
    # ------------------------------------------------------------------

    def seed_all(self) -> None:
        from django.db import transaction  # noqa: E402
        _verify_manifest()
        with transaction.atomic():
            self._build_indexes()
            self._seed_organizations()
            self._seed_users()
            self._seed_workers()
            self._seed_documents()
            self._seed_assignments()
            self._seed_a1_inputs()
            self._seed_jobs()
            self._seed_reviewer_accounts()
            self._audit_seed()

    def _seed_organizations(self) -> None:
        from portal.release1a.models import Organization  # noqa: E402
        for row in self.fixture_orgs:
            obj, _ = Organization.objects.update_or_create(
                key=row["id"],
                defaults={"label": row["name"]},
            )
            self.orgs[row["id"]] = obj

    def _seed_users(self) -> None:
        from django.contrib.auth import get_user_model  # noqa: E402
        from portal.release1a.models import Membership  # noqa: E402
        User = get_user_model()
        for row in _load_json("users.json"):
            email = row["email"]
            obj, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "is_active": False,
                    "is_superuser": False,
                },
            )
            org_id = row.get("organization_id")
            if org_id and org_id in self.orgs:
                Membership.objects.update_or_create(
                    user=obj,
                    organization=self.orgs[org_id],
                    role=row.get("role", "operator"),
                    defaults={"active": True},
                )

    def _seed_workers(self) -> None:
        from portal.release1a.models import Worker  # noqa: E402
        for row in self.fixture_workers:
            org = self.orgs.get(row["organization_id"])
            if org is None:
                continue
            obj, _ = Worker.objects.update_or_create(
                organization=org,
                given_name=row["first_name"],
                family_name=row["last_name"],
                birth_date=row["birth_date"],
                defaults={
                    "activity_profile": ACTIVITY_FIXTURE_TO_MODEL.get(
                        row.get("employment_type", ""), row.get("employment_type", "employee")
                    ),
                    "state": STATE_FIXTURE_TO_MODEL.get(
                        row.get("status", ""), row.get("status", "draft")
                    ),
                },
            )
            self.workers[row["id"]] = obj

    def _seed_documents(self) -> None:
        from portal.release1a.models import Document  # noqa: E402
        for row in _load_json("documents.json"):
            org = self.orgs.get(row["organization_id"])
            worker = self.workers.get(row.get("worker_id", "")) if org else None
            if not org or worker is None:
                continue
            # Derive a stable sha256 even when storage_key is null: use the
            # canonical id or storage_key if present; else hash the id so
            # fixture rows that share (org, worker, empty sha) do not collide
            # on the unique (org, sha256) constraint.
            base = row.get("storage_key") or row.get("id") or ""
            sha256 = base[:64] if len(base) >= 32 else hashlib.sha256(base.encode()).hexdigest()
            Document.objects.update_or_create(
                organization=org,
                worker=worker,
                sha256=sha256,
                defaults={
                    "opaque_key": row.get("storage_key") or f"synthetic-{row['id']}",
                    "content_type": row.get("content_type", "application/pdf"),
                    "state": row.get("quarantine_status", row.get("state", "quarantined")),
                },
            )

    def _seed_assignments(self) -> None:
        from portal.release1a.models import Assignment  # noqa: E402
        for row in self.fixture_assignments:
            org = self.orgs.get(row["organization_id"])
            worker = self.workers.get(row["worker_id"]) if org else None
            if not org or worker is None:
                continue
            Assignment.objects.update_or_create(
                organization=org,
                worker=worker,
                start=row["start_date"],
                end=row["end_date"],
                workplace_label=row.get("workplace_label", row.get("workplace", "")),
                defaults={
                    "activity_label": row.get("activity_label", row.get("role", "")),
                    "state": row.get("status", "planned"),
                    "version": 1,
                },
            )

    def _seed_a1_inputs(self) -> None:
        from portal.release1a.models import A1Case  # noqa: E402
        for row in self.fixture_a1_inputs:
            org = self.orgs.get(row["organization_id"])
            worker = self.workers.get(row["worker_id"]) if org else None
            if not org or worker is None:
                continue
            A1Case.objects.update_or_create(
                organization=org,
                worker=worker,
                source_hash=row.get("source_hash", "synthetic"),
                defaults={
                    "readiness": row.get("readiness", "blocked"),
                    "prepared_artifact_hash": row.get("prepared_artifact_hash", ""),
                    "external_status": "not_submitted",
                },
            )

    def _seed_jobs(self) -> None:
        for row in _load_json("jobs.json"):
            # Jobs model not yet implemented; this is logged only.
            pass

    def _seed_reviewer_accounts(self) -> None:
        from django.contrib.auth import get_user_model  # noqa: E402
        from portal.release1a.models import Membership  # noqa: E402
        User = get_user_model()
        if not self.orgs:
            return
        first_org = next(iter(self.orgs.values()))
        for email, first_name, last_name in (
            ("jan-reviewer@example.invalid", "Jan", "Reviewer"),
            ("pavel-reviewer@example.invalid", "Pavel", "Reviewer"),
        ):
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": False,
                    "is_superuser": False,
                },
            )
            Membership.objects.update_or_create(
                user=user,
                organization=first_org,
                role="operator",
                defaults={"active": True},
            )

    def _audit_seed(self) -> None:
        from portal.release1a.models import AuditEvent  # noqa: E402
        if not self.orgs:
            return
        org = next(iter(self.orgs.values()))
        AuditEvent.objects.create(
            organization=org,
            actor_ref="seed:release1a_dev",
            event_type="seed.completed",
            object_ref="seed:release1a_dev",
            outcome="success",
        )

    # ------------------------------------------------------------------
    # Verify path: read-only comparison against current DB state.
    # ------------------------------------------------------------------

    def verify_seeded_db(self) -> int:
        """Compare approved fixtures against the current DB. Exit 0 if consistent, 1 if not.

        Reads each fixture, queries the DB for matching rows on natural keys,
        and reports mismatch counts without copying stored source values.
        """
        from portal.release1a.models import (  # noqa: E402
            A1Case, Assignment, Organization, Worker,
        )

        # SQLite otherwise creates a missing database even for a SELECT. Open
        # verification through SQLite's read-only URI instead; no empty DB or
        # journal may be created by a verification attempt.
        from django.db import connections
        from urllib.parse import quote
        connection = connections["default"]
        if connection.vendor == "sqlite":
            database = Path(connection.settings_dict["NAME"])
            if not database.is_file():
                print("Verification database is missing; migrate and seed the selected environment first.")
                return 1
            connection.close()
            connection.settings_dict["NAME"] = "file:" + quote(str(database), safe="/") + "?mode=ro"
            connection.settings_dict.setdefault("OPTIONS", {})["uri"] = True

        manifest = _verify_manifest()
        self._build_indexes()
        checks: list[dict] = []

        # 1. Organizations ------------------------------------------------------
        org_keys = {r["id"] for r in self.fixture_orgs}
        db_orgs = {o.key: o for o in Organization.objects.all()}
        org_extras: list[str] = []
        for row in self.fixture_orgs:
            db = db_orgs.get(row["id"])
            if db is None:
                org_extras.append(f"missing={row['id']}")
                continue
            if db.label != row["name"]:
                org_extras.append(
                    f"{row['id']}: label mismatch"
                )
        for org_key in db_orgs:
            if org_key not in org_keys:
                org_extras.append(f"extra_db={org_key}")
        checks.append(_check("organizations", org_extras,
                              fixture_count=len(self.fixture_orgs),
                              db_count=len(db_orgs)))

        # Compare multisets, not dictionaries: duplicate natural keys must remain
        # visible. Include mutable values so stale facts cannot pass by row count.
        from collections import Counter

        def worker_key(row):
            return (row["organization_id"], row["last_name"], row["first_name"], row["birth_date"])

        def db_worker_key(worker):
            return (worker.organization.key, worker.family_name, worker.given_name, str(worker.birth_date))

        def compare(label, expected, actual):
            expected, actual = Counter(expected), Counter(actual)
            missing = sum((expected - actual).values())
            extra = sum((actual - expected).values())
            discrepancies = []
            if missing:
                discrepancies.append(f"missing_or_changed={missing}")
            if extra:
                discrepancies.append(f"extra_or_changed={extra}")
            checks.append(_check(label, discrepancies,
                                 fixture_count=sum(expected.values()), db_count=sum(actual.values())))

        compare("workers", [
            (*worker_key(row), ACTIVITY_FIXTURE_TO_MODEL.get(row.get("employment_type", ""),
              row.get("employment_type", "employee")),
             STATE_FIXTURE_TO_MODEL.get(row.get("status", ""), row.get("status", "draft")))
            for row in self.fixture_workers
        ], [(*db_worker_key(row), row.activity_profile, row.state)
            for row in Worker.objects.select_related("organization").all()])

        compare("assignments", [
            (row["organization_id"], worker_key(self.workers[row["worker_id"]]),
             row["start_date"], row["end_date"], row.get("workplace_label", row.get("workplace", "")),
             row.get("activity_label", row.get("role", "")), row.get("status", "planned"), 1)
            for row in self.fixture_assignments
        ], [(row.organization.key, db_worker_key(row.worker), str(row.start), str(row.end),
             row.workplace_label, row.activity_label, row.state, row.version)
            for row in Assignment.objects.select_related("organization", "worker__organization").all()])

        # Fixture status/generation_hash do not prove preparation or submission.
        # Only the explicitly supported seed fields establish expected case state.
        compare("a1_cases", [
            (row["organization_id"], worker_key(self.workers[row["worker_id"]]),
             row.get("source_hash", "synthetic"), row.get("readiness", "blocked"),
             row.get("prepared_artifact_hash", ""), "not_submitted")
            for row in self.fixture_a1_inputs
        ], [(row.organization.key, db_worker_key(row.worker) if row.worker_id else None,
             row.source_hash, row.readiness, row.prepared_artifact_hash, row.external_status)
            for row in A1Case.objects.select_related("organization", "worker__organization").all()])

        # Render the report and decide ----------------------------------------
        all_ok = _render_report(manifest, checks)
        return 0 if all_ok else 1


def _check(label: str, extras: list[str], *, fixture_count: int, db_count: int) -> dict:
    return {
        "label": label,
        "ok": not extras,
        "fixture_count": fixture_count,
        "db_count": db_count,
        "extras": list(extras),
    }


def _render_report(manifest: dict, checks: list[dict]) -> bool:
    print(f"\nVerify report at {_now_iso()} (fixture_set={manifest.get('fixture_set', '')}):")
    all_ok = True
    for c in checks:
        status = "OK" if c["ok"] else "MISMATCH"
        print(f"  [{status}] {c['label']}: fixture={c['fixture_count']} db={c['db_count']}")
        if not c["ok"]:
            all_ok = False
            for ex in c["extras"]:
                print(f"      {ex}")
    print(f"\nSummary: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed (or verify) the synthetic Release 1A DB.")
    parser.add_argument("--dry-run", action="store_true",
                        help="verify manifest hashes + simulate; no DB writes")
    parser.add_argument("--apply", action="store_true",
                        help="write via Django ORM (idempotent update_or_create)")
    parser.add_argument("--verify", action="store_true",
                        help="compare fixtures against current DB; read-only; non-zero on mismatch")
    args = parser.parse_args()

    if not (args.apply or args.dry_run or args.verify):
        print("No action. Use --dry-run, --apply or --verify. Defaulting to --dry-run.")
        args.dry_run = True

    try:
        _setup_django()
    except SettingsModuleRejected as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2

    seeder = Seeder()
    if args.verify:
        try:
            return seeder.verify_seeded_db()
        except ProtectedPathAccessed as exc:
            print(f"CONTAINMENT VIOLATION: {exc}")
            print("ABORTED: verify attempted to access a protected path.")
            return 1

    print("Manifest verified, applying fixtures..." if not args.dry_run else
          "Manifest verified, simulating seeding (no writes)...")
    if args.dry_run:
        try:
            _verify_manifest()
            _protected_path_guard(_load_json("organizations.json"))
            _protected_path_guard(_load_json("workers.json"))
            _protected_path_guard(_load_json("assignments.json"))
            _protected_path_guard(_load_json("a1_inputs.json"))
            _protected_path_guard(_load_json("documents.json"))
            print("  Manifest + protected-path guard OK; no DB writes.")
            return 0
        except (ProtectedPathAccessed, ValueError, FileNotFoundError) as exc:
            print(f"ERROR: {exc}")
            return 1

    try:
        seeder.seed_all()
    except ProtectedPathAccessed as exc:
        print(f"CONTAINMENT VIOLATION: {exc}")
        print("ABORTED: seed script attempted to access a protected path.")
        return 1

    print("Seed complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
