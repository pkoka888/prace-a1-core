"""Regression tests for rehearse_verify_persistence.py.

Tests the actual execution paths, not just settings existence:
- F2: core profile runs without A1/PDF env vars
- F3: document hash is compared against the expected value
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "rehearse_verify_persistence.py"


def _run(args, env):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=30,
    )


def _base_env(tmp_root, with_pdf=True):
    old_umask = os.umask(0o077)
    try:
        env = {
            "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
            "PRACE_RUNTIME_ROOT": str(tmp_root),
            "PRACE_SECRET_KEY": "test-secret-not-a-real-key",
            "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "PYTHONPATH": str(REPO_ROOT),
        }
        manifest = tmp_root / "build_manifest.json"
        manifest.write_text(
            json.dumps({"git_commit": "0" * 40, "app_build_id": "0" * 16, "generated_at": "2026-01-01T00:00:00Z"})
        )
        manifest.chmod(0o400)
        import hashlib
        sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
        env["PRACE_RELEASE_MANIFEST"] = str(manifest)
        env["PRACE_RELEASE_MANIFEST_SHA256"] = sha
        if with_pdf:
            env.update({
                "PDF_SHA256": "0" * 64,
                "REGEN_SHA256": "1" * 64,
            })
        return env
    finally:
        os.umask(old_umask)


def _migrated_runtime_env(tmp_root):
    """Build the supervised-synthetic env and run a real migrate once, so
    the verification queries run against a real schema (rows missing) and
    not against an empty database (which now correctly exits BLOCKED)."""
    env = _base_env(tmp_root, with_pdf=False)
    r = subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        cwd=str(REPO_ROOT), env={**os.environ, **env},
        capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, f"migrate failed:\n{r.stdout}\n{r.stderr}"
    return env


class TestCoreProfileNoPdfVars:
    """F2: core profile must run without A1/PDF env vars."""

    def test_core_profile_succeeds_without_pdf_vars(self):
        with tempfile.TemporaryDirectory(prefix="supervised-persistence-test-", dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            env.update({
                "ORG_PK": "1",
                "WORKER_PK": "99999",
                "DOCUMENT_PK": "99999",
                "ASSIGNMENT_PK": "99999",
                "DOCUMENT_SHA256": "0" * 64,
            })
            r = _run(["--profile", "core"], env)
            # Exit 1 is expected because rows don't exist; exit 2 would
            # mean the script blocked on missing env (the bug).
            assert r.returncode != 2, (
                f"core profile blocked on missing env (F2 not fixed):\n"
                f"stderr: {r.stderr}"
            )

    def test_optional_a1_profile_blocks_without_pdf_vars(self):
        with tempfile.TemporaryDirectory(prefix="supervised-persistence-test-", dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _base_env(tmp_root, with_pdf=False)
            env.update({
                "ORG_PK": "1",
                "WORKER_PK": "99999",
                "DOCUMENT_PK": "99999",
                "ASSIGNMENT_PK": "99999",
                "DOCUMENT_SHA256": "0" * 64,
            })
            r = _run(["--profile", "optional-a1"], env)
            # Exit 2 = PERSISTENCE_ACCEPTANCE_BLOCKED is expected for optional-a1 without PDF vars
            assert r.returncode == 2, (
                f"optional-a1 profile should block without PDF vars:\n"
                f"rc={r.returncode}\nstderr: {r.stderr}"
            )
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr


class TestDocumentHashVerification:
    """F3: document hash must be compared, not just retrieved."""

    def test_hash_mismatch_reported(self):
        """When the stated identifier rows do not exist, the core check
        reports a row/check failure (exit 1) — not a blocked exit 2."""
        with tempfile.TemporaryDirectory(prefix="supervised-persistence-test-", dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            env.update({
                "ORG_PK": "1",
                "WORKER_PK": "99999",
                "DOCUMENT_PK": "99999",
                "ASSIGNMENT_PK": "99999",
                "DOCUMENT_SHA256": "abcd" * 16,
            })
            r = _run(["--profile", "core"], env)
            assert r.returncode == 1, f"unexpected rc={r.returncode}: {r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" not in r.stderr

    def test_hash_function_accepts_expected_value(self):
        """The _document_worker_sha256 function must accept expected_sha256."""
        code = (
            "import sys\n"
            "sys.path.insert(0, " + repr(str(REPO_ROOT)) + ")\n"
            "from scripts.rehearse_verify_persistence import _document_worker_sha256\n"
            "import inspect\n"
            "sig = inspect.signature(_document_worker_sha256)\n"
            "params = list(sig.parameters.keys())\n"
            "print('params=' + ','.join(params))\n"
            "assert 'expected_sha256' in params, '_document_worker_sha256 must accept expected_sha256'\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert r.returncode == 0, f"F3 not fixed: {r.stderr}"


class TestSourceBytesVerification:
    """F3 refinement: the verifier must prove source-file bytes, not only
    the stored hash column. A correct sha256 column with corrupted source
    bytes must FAIL, and a corrupted column with correct bytes must FAIL
    with a distinct message."""

    SEED_CODE = (
        "import hashlib, datetime\n"
        "from django.core.files.base import ContentFile\n"
        "from portal.release1a.document_storage import document_storage\n"
        "from portal.release1a.models import Organization, Worker, Document, Assignment\n"
        "org, _ = Organization.objects.get_or_create(\n"
        "    key='persist-source-test-org', defaults={'label': 'Persistence source test'})\n"
        "worker = Worker.objects.create(organization=org, given_name='Jan', family_name='Vyzkus',\n"
        "    birth_date=datetime.date(1990, 1, 1), activity_profile='employee', state='active')\n"
        "content = b'SOURCE-DOCUMENT-BYTES-2026 42\\n'\n"
        "key = 'documents/0123456789abcdef0123456789abcdef.source'\n"
        "sha = hashlib.sha256(content).hexdigest()\n"
        "document_storage().save(key, ContentFile(content))\n"
        "document = Document.objects.create(organization=org, worker=worker,\n"
        "    purpose='worker_intake', opaque_key=key, sha256=sha,\n"
        "    content_type='text/plain', state='confirmed')\n"
        "assignment = Assignment.objects.create(organization=org, worker=worker,\n"
        "    workplace_label='Hamburg', activity_label='montáž',\n"
        "    start=datetime.date(2026, 9, 1), end=datetime.date(2027, 8, 31),\n"
        "    state='active')\n"
        "print('ORG=%d WORKER=%d DOC=%d ASSIGN=%d SHA=%s KEY=%s' % (\n"
        "    org.pk, worker.pk, document.pk, assignment.pk, sha, key))\n"
    )

    def _provision(self, tmp_root):
        env = _base_env(tmp_root, with_pdf=False)
        base = {
            "PATH": os.environ["PATH"],
            "HOME": os.environ.get("HOME", "/tmp"),
            "PYTHONPATH": str(REPO_ROOT),
            "DJANGO_SETTINGS_MODULE": "portal.settings_supervised_synthetic",
            "PRACE_RUNTIME_ROOT": str(tmp_root),
            "PRACE_SECRET_KEY": "test-secret-not-a-real-key",
            "PRACE_ALLOWED_HOSTS": "localhost,127.0.0.1",
        }
        base["PRACE_RELEASE_MANIFEST"] = env["PRACE_RELEASE_MANIFEST"]
        base["PRACE_RELEASE_MANIFEST_SHA256"] = env["PRACE_RELEASE_MANIFEST_SHA256"]
        r = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=str(REPO_ROOT), env={**os.environ, **base},
            capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, f"migrate failed:\n{r.stdout}\n{r.stderr}"
        seed = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c", self.SEED_CODE],
            cwd=str(REPO_ROOT), env={**os.environ, **base},
            capture_output=True, text=True, timeout=60)
        assert seed.returncode == 0, f"seed failed:\n{seed.stdout}\n{seed.stderr}"
        values = {}
        for token in seed.stdout.strip().split():
            key, _, value = token.partition("=")
            values[key] = value
        values["env"] = base
        return values

    def _verify(self, values, doc_sha):
        env = dict(values["env"])
        env.update({
            "ORG_PK": values["ORG"],
            "WORKER_PK": values["WORKER"],
            "DOCUMENT_PK": values["DOC"],
            "ASSIGNMENT_PK": values["ASSIGN"],
            "DOCUMENT_SHA256": doc_sha,
        })
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--profile", "core"],
            env={**os.environ, **env}, capture_output=True, text=True, timeout=60)

    def test_source_bytes_and_stored_hash_both_proven(self):
        """One provisioned journey proves all three acceptance paths:
        matching source bytes pass, corrupted source bytes fail despite a
        correct stored hash, and a wrong expected DB hash fails with the
        distinct db-mismatch message."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-source-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            values = self._provision(tmp_root)
            content = b"SOURCE-DOCUMENT-BYTES-2026 42\n"

            good = self._verify(values, values["SHA"])
            assert good.returncode == 0, (
                f"matching source bytes must pass:\n{good.stderr}")
            assert "db+source matched" in good.stdout

            corrupt = (tmp_root / "storage" / values["KEY"])
            corrupt.write_bytes(b"CORRUPTED-DIFFERENT-BYTES\n")
            bad_source = self._verify(values, values["SHA"])
            assert bad_source.returncode == 1
            assert "source bytes" in bad_source.stderr

            bugfix = (tmp_root / "storage" / values["KEY"])
            bugfix.write_bytes(content)
            wrong_hash = self._verify(values, "f" * 64)
            assert wrong_hash.returncode == 1
            assert "db hash mismatch" in wrong_hash.stderr


class TestConfirmedIdentityPersistence:
    """The verifier must load the exact confirmed identity fields from the
    canonical nested journey receipt shape (stages.identity_confirmed),
    compare them against the stored WorkerIdentityRevision (after the same
    normalization the persistence layer applied), and reject a mutated stored
    field with the exact expected vs actual strings."""

    STORED_FIELDS = {
        "family_name": "TESTOVA",
        "given_name": "ALFA",
        "birth_date": "1990-03-15",
        "residence_address": "TESTOVACI 12, 12345 TESTOV",
        "birth_place": "Praha",
        "nationality": "CZE",
        "sex": "F",
        "insurance_number": "INS000001",
        "street": "Testovaci",
        "house_number": "12",
        "city": "Testov",
        "postal_code": "12345",
        "country_code": "CZ",
    }

    # What the journey entered/recorded; nationality "CZ" must be normalized
    # to "CZE" by the verifier, exactly as the persistence layer did.
    JOURNEY_FIELDS = dict(STORED_FIELDS)
    JOURNEY_FIELDS["nationality"] = "CZ"

    def _seed_rows(self, tmp_root, env, activity_label="Montážní práce"):
        """Seed org/worker/document/assignment plus a confirmed identity
        revision with the exact stored fields, and return identifiers."""
        import json as _json
        seed_code = (
            "import io, hashlib, json\n"
            "from datetime import date\n"
            "from portal.release1a.models import (Organization, Worker,\n"
            "    Assignment, Document, WorkerIdentityRevision)\n"
            "from portal.release1a.document_storage import document_storage\n"
            "org, _ = Organization.objects.get_or_create(\n"
            "    pk=1, defaults={'key': 'synthetic-demo',\n"
            "                    'label': 'Synthetic demo org'})\n"
            "worker = Worker.objects.create(\n"
            "    organization=org, given_name='Alfa',\n"
            "    family_name='Testerova', birth_date=date(1990, 3, 15),\n"
            "    activity_profile='employee')\n"
            "payload = b'persistence-verification-source-bytes'\n"
            "digest = hashlib.sha256(payload).hexdigest()\n"
            "key = 'documents/' + ('a' * 32) + '/' + ('c' * 64) + '.source'\n"
            "document_storage().save(key, io.BytesIO(payload))\n"
            "document = Document.objects.create(\n"
            "    organization=org, worker=worker,\n"
            "    opaque_key=key, sha256=digest,\n"
            "    content_type='application/pdf')\n"
            "assignment = Assignment.objects.create(\n"
            "    organization=org, worker=worker, workplace_label='Brno',\n"
            "    activity_label=%r, start=date(2026, 1, 1),\n"
            "    end=date(2026, 2, 1))\n"
            "WorkerIdentityRevision.objects.create(\n"
            "    organization=org, worker=worker,\n"
            "    source_document=document,\n"
            "    revision_number=1,\n"
            "    confirmed_fields=json.loads(%r),\n"
            "    confirmed_at=__import__('django.utils.timezone')"
            ".utils.timezone.now())\n"
            "print(json.dumps({'worker_pk': worker.pk,\n"
            "    'document_pk': document.pk, 'assignment_pk': assignment.pk,\n"
            "    'sha256': digest}))\n"
            % (activity_label, _json.dumps(self.STORED_FIELDS, sort_keys=True))
        )
        r = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c", seed_code],
            cwd=str(REPO_ROOT), env={**os.environ, **env},
            capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"seed failed:\n{r.stderr}"
        return json.loads(r.stdout.strip().splitlines()[-1])

    def _journey_receipt(self, ids):
        """Canonical nested journey evidence with an identity_confirmed
        stage carrying the exact journey-entered identity values."""
        receipt = {
            "ok": True,
            "profile": "core",
            "organization_id": 1,
            "worker_pk": ids["worker_pk"],
            "document_pk": ids["document_pk"],
            "assignment_pk": ids["assignment_pk"],
            "source_document_sha256": ids["sha256"],
            "stages": {
                "identity_confirmed": {
                    "ok": True,
                    "stage": "identity_confirmed",
                    "worker_pk": ids["worker_pk"],
                    "confirmed_fields": dict(self.JOURNEY_FIELDS),
                },
            },
        }
        return receipt

    def _journey_env(self, tmp_root, env, ids):
        env = dict(env)
        env.update({
            "JOURNEY_EVIDENCE_PATH": str(tmp_root / "journey-evidence.json"),
            "ORG_PK": "1",
            "WORKER_PK": str(ids["worker_pk"]),
            "DOCUMENT_PK": str(ids["document_pk"]),
            "ASSIGNMENT_PK": str(ids["assignment_pk"]),
            "DOCUMENT_SHA256": ids["sha256"],
        })
        assert "CONFIRMED_IDENTITY_FIELDS" not in env
        assert "CONFIRMED_IDENTITY_FIELDS" not in os.environ
        return env

    def _write_receipt(self, tmp_root, ids, mutate=lambda receipt: receipt):
        receipt = mutate(self._journey_receipt(ids))
        path = tmp_root / "journey-evidence.json"
        path.write_text(json.dumps(receipt))
        os.chmod(str(path), 0o600)
        return path

    def _base_run(self, tmp_root, env, ids):
        env = self._journey_env(tmp_root, env, ids)
        self._write_receipt(tmp_root, ids)
        return _run(["--profile", "core"], env)

    def test_receipt_identity_values_pass(self):
        """The exact journey identity values must come from
        stages.identity_confirmed in the receipt and pass against the
        stored revision (with nationality normalized like the persist
        layer normalized it)."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)
            r = self._base_run(tmp_root, env, ids)
            assert r.returncode == 0, (
                f"rc={r.returncode}\n{r.stdout}\n{r.stderr}")
            assert "ok  identity_confirmed" in r.stdout
            outcome = json.loads(r.stdout.strip().splitlines()[-1])
            assert outcome["checks"]["identity_confirmed"]["ok"] is True

    def test_require_identity_full_field_pass(self):
        """--require-identity must pass when the receipt carries the complete
        canonical 13-field confirmed identity set and the stored values
        match: durable core acceptance demands the full identity comparison,
        and a complete valid run is the complement to the negative coverage
        cases below."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)
            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids)
            r = _run(["--profile", "core", "--require-identity"], env)
            assert r.returncode == 0, (
                f"rc={r.returncode}\n{r.stdout}\n{r.stderr}")
            assert "ok  identity_confirmed" in r.stdout
            outcome = json.loads(r.stdout.strip().splitlines()[-1])
            identity = outcome["checks"]["identity_confirmed"]
            assert identity["ok"] is True
            assert identity["confirmed_fields_count"] == 13

    def test_mutated_stored_identity_field_fails_with_exact_values(self):
        """Negative case: keep the receipt unchanged, mutate one stored
        confirmed field in the database, and require failure naming both the
        journey value and the drifted stored value."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)
            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids)
            mutated = dict(self.STORED_FIELDS)
            mutated["street"] = "TAMPERED"
            r = subprocess.run(
                [sys.executable, "manage.py", "shell", "-c",
                 "import json\n"
                 "from portal.release1a.models import WorkerIdentityRevision\n"
                 f"WorkerIdentityRevision.objects"
                 f".filter(worker_id={ids['worker_pk']})"
                 f".update(confirmed_fields=json.loads(%r))\n" % (
                     json.dumps(mutated, sort_keys=True))],
                cwd=str(REPO_ROOT), env={**os.environ, **env},
                capture_output=True, text=True, timeout=120)
            assert r.returncode == 0, f"mutation failed:\n{r.stderr}"
            r = _run(["--profile", "core"], env)
            assert r.returncode == 1, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "FAIL identity_confirmed" in r.stderr
            assert "street" in r.stderr
            assert "Testovaci" in r.stderr
            assert "TAMPERED" in r.stderr
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" not in r.stderr

    def test_malformed_identity_evidence_blocks(self):
        """A receipt claiming confirmed identity values without the field
        map must block (exit 2), never silently skip the comparison."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def drop_fields(receipt):
                receipt["stages"]["identity_confirmed"].pop("confirmed_fields")
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, drop_fields)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr
            assert "confirmed_fields" in r.stderr

    def test_absent_identity_evidence_skips_legacy(self):
        """A receipt whose stages lack an identity_confirmed key keeps the
        legacy behavior: the identity comparison is omitted (exit 0 when
        rows exist), distinguished from a present-but-malformed stage."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def drop_stage(receipt):
                receipt["stages"].pop("identity_confirmed", None)
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, drop_stage)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 0, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            outcome = json.loads(r.stdout.strip().splitlines()[-1])
            assert "identity_confirmed" not in outcome["checks"], (
                f"unexpected identity check in outcome: {outcome['checks']}"
            )

    def test_non_dict_identity_evidence_blocks(self):
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def non_dict(receipt):
                receipt["stages"]["identity_confirmed"] = "invalid"
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, non_dict)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr
            assert "not a JSON object" in r.stderr

    def test_worker_pk_mismatch_between_receipt_and_selection_blocks(self):
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def wrong_pk(receipt):
                receipt["stages"]["identity_confirmed"]["worker_pk"] = 99999
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, wrong_pk)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "does not match" in r.stderr

    def test_require_identity_blocks_on_absent_stage(self):
        """--require-identity must refuse a legacy receipt that omits the
        identity stage (exit 2): durable core acceptance can never be
        claimed without the confirmed-identity comparison."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def drop_stage(receipt):
                receipt["stages"].pop("identity_confirmed", None)
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, drop_stage)
            r = _run(["--profile", "core", "--require-identity"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr
            assert "confirmed identity evidence" in r.stderr

    def test_require_identity_enforces_full_field_coverage(self):
        """A receipt carrying only a subset of the canonical fields must be
        refused under --require-identity (exit 2) with the missing fields
        named, so a truncated or re-authored receipt cannot pass acceptance
        by omitting fields."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def truncated(receipt):
                receipt["stages"]["identity_confirmed"]["confirmed_fields"] = {
                    "family_name": "TESTOVA"}
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, truncated)
            r = _run(["--profile", "core", "--require-identity"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "missing expected fields" in r.stderr
            assert "birth_date" in r.stderr

    def test_empty_identity_field_map_blocks(self):
        """An empty confirmed_fields map must block (exit 2) rather than
        produce a vacuous zero-comparison pass."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def empty_fields(receipt):
                receipt["stages"]["identity_confirmed"]["confirmed_fields"] = {}
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, empty_fields)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "vacuous" in r.stderr or "confirmed_fields is empty" in r.stderr

    def test_non_string_identity_value_fails(self):
        """A confirmed identity value that is not a non-empty string must
        fail the check (never fall back to a raw comparison)."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def non_string(receipt):
                fields = dict(self.JOURNEY_FIELDS)
                fields["sex"] = None
                receipt["stages"]["identity_confirmed"]["confirmed_fields"] = fields
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, non_string)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 1, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "not a string" in r.stderr

    def test_normalization_findings_identity_value_fails(self):
        """A journey value that cannot be normalized cleanly must fail the
        check (exit 1), not fall back to a raw string comparison. An invalid
        birth_date is refused even though a stored raw match could exist."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env)

            def bad_date(receipt):
                fields = dict(self.JOURNEY_FIELDS)
                fields["birth_date"] = "1990-13-45"
                receipt["stages"]["identity_confirmed"]["confirmed_fields"] = fields
                return receipt

            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids, bad_date)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 1, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "failed normalization" in r.stderr
            assert "invalid_date" in r.stderr


class TestIdentityFieldSetConsistency:
    """The verifier's canonical EXPECTED_IDENTITY_FIELDS must stay identical
    to the browser journey's CONFIRMED_IDENTITY_FIELDS, otherwise coverage
    enforcement and the journey would silently diverge."""

    def test_expected_fields_match_browser_helper(self):
        import ast

        source = (REPO_ROOT / "tests" / "_rehearse_workflow_browser.py").read_text()
        tree = ast.parse(source)
        browser_fields = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and \
                            target.id == "CONFIRMED_IDENTITY_FIELDS":
                        browser_fields = ast.literal_eval(node.value)
        assert browser_fields is not None, (
            "CONFIRMED_IDENTITY_FIELDS not found in _rehearse_workflow_browser.py")

        verifier_code = (
            "import sys\n"
            "sys.path.insert(0, " + repr(str(REPO_ROOT)) + ")\n"
            "from scripts.rehearse_verify_persistence import "
            "EXPECTED_IDENTITY_FIELDS\n"
            "import json\n"
            "print(json.dumps(sorted(EXPECTED_IDENTITY_FIELDS)))\n"
        )
        r = subprocess.run(
            [sys.executable, "-c", verifier_code],
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True, text=True, timeout=15)
        assert r.returncode == 0, f"import failed: {r.stderr}"
        expected = json.loads(r.stdout.strip().splitlines()[-1])
        assert set(expected) == set(browser_fields), (
            f"verifier EXPECTED_IDENTITY_FIELDS diverged from the browser "
            f"helper:\nverifier={expected}\nbrowser={sorted(browser_fields)}"
        )


class TestBrowserProfileWiring:
    """F5: playwright_smoke must not strip PostgreSQL env vars."""

    def test_playwright_smoke_preserves_pg_env(self):
        source = (REPO_ROOT / "scripts/playwright_smoke.py").read_text()
        assert "DOCUMENT_TEST_PG_SOCKET" not in source, (
            "F5 not fixed: playwright_smoke.py still pops DOCUMENT_TEST_PG_SOCKET"
        )
        assert "DOCUMENT_TEST_PG_USER" not in source, (
            "F5 not fixed: playwright_smoke.py still pops DOCUMENT_TEST_PG_USER"
        )


class TestOperatorUrlWiring:
    """F6: PRACE_OPERATOR_URL must be consumed by the workflow caller."""

    def test_rehearse_script_uses_operator_url(self):
        source = (REPO_ROOT / "scripts/rehearse_synthetic_site.sh").read_text()
        assert "PRACE_OPERATOR_URL" in source, (
            "F6 not fixed: rehearse_synthetic_site.sh does not reference PRACE_OPERATOR_URL"
        )
        assert "base_url" in source, (
            "F6 not fixed: base_url variable not set from PRACE_OPERATOR_URL"
        )


class TestIsolatedPgWiring:
    """F7: browser test settings must accept complete PostgreSQL targets,
    must require PASSWORD on TCP, and must fail closed on a lone variable
    instead of silently selecting SQLite."""

    IMPORT = (
        "import os, sys\n"
        "os.environ['DJANGO_SETTINGS_MODULE'] = 'portal.settings_browser_tests'\n"
        "sys.path.insert(0, " + repr(str(REPO_ROOT)) + ")\n"
        "try:\n"
        "    from portal import settings_browser_tests as s\n"
        "except Exception as exc:\n"
        "    sys.stderr.write('IMPORT_ERROR: ' + repr(exc) + '\\n')\n"
        "    sys.exit(2)\n"
        "db = s.DATABASES['default']\n"
        "print('ENGINE=' + db['ENGINE'])\n"
        "print('NAME=' + db['NAME'])\n"
        "print('USER=' + str(db.get('USER', '')))\n"
        "print('PASSWORD=' + str('PASSWORD' in db))\n"
    )

    def _run(self, extra_env):
        runtime = REPO_ROOT / "runtime" / "portal"
        runtime.mkdir(parents=True, exist_ok=True)
        socket_dir = tempfile.mkdtemp(prefix="browser-pg-", dir=runtime)
        env = {
            **os.environ,
            "DOCUMENT_TEST_PG_SOCKET": socket_dir,
            "DOCUMENT_TEST_PG_NAME": "prace_browser_tests",
            "DOCUMENT_TEST_PG_USER": "browser_tester",
            "DOCUMENT_TEST_PG_PORT": "55439",
        }
        if "DOCUMENT_TEST_PG_HOST" in extra_env:
            env.pop("DOCUMENT_TEST_PG_SOCKET")
        env.update(extra_env)
        return subprocess.run([sys.executable, "-c", self.IMPORT],
                              cwd=str(REPO_ROOT), env=env,
                              capture_output=True, text=True, timeout=60)

    def test_browser_settings_accepts_socket_target_without_password(self):
        result = self._run({})
        assert result.returncode == 0, result.stderr
        assert "ENGINE=django.db.backends.postgresql" in result.stdout
        assert "NAME=prace_browser_tests" in result.stdout
        assert "USER=browser_tester" in result.stdout
        assert "PASSWORD=False" in result.stdout

    def test_browser_settings_requires_password_for_tcp_target(self):
        result = self._run({
            "DOCUMENT_TEST_PG_HOST": "127.0.0.1",
            "DOCUMENT_TEST_PG_PORT": "5432",
        })
        assert result.returncode != 0
        assert "DOCUMENT_TEST_PG_PASSWORD is required" in result.stderr

    def test_browser_settings_host_only_fails_closed(self):
        result = subprocess.run(
            [sys.executable, "-c", self.IMPORT], cwd=str(REPO_ROOT),
            env={
                **os.environ,
                "DOCUMENT_TEST_PG_HOST": "127.0.0.1",
                "DOCUMENT_TEST_PG_PORT": "5432",
            },
            capture_output=True, text=True, timeout=60)
        assert result.returncode != 0, (
            "host-only target must fail closed, not silently select SQLite")
        assert "partial test PostgreSQL target" in result.stderr


class TestCorrectedValuePersistence:
    """The verifier must load the corrected value from the canonical nested
    journey receipt shape (stages.assignment_corrected), compare it against
    the persisted assignment row, and reject a mutated stored value with the
    exact expected vs actual strings."""

    JOURNEY_LABEL = "Montážní práce — upraveno"

    def _seed_rows(self, tmp_root, env, activity_label):
        """Seed org/worker/document/assignment into the migrated runtime DB
        and return their identifiers plus the document digest."""
        seed_code = (
            "import io, hashlib, json\n"
            "from datetime import date\n"
            "from portal.release1a.models import (Organization, Worker,\n"
            "    Assignment, Document)\n"
            "from portal.release1a.document_storage import document_storage\n"
            "org, _ = Organization.objects.get_or_create(\n"
            "    pk=1, defaults={'key': 'synthetic-demo',\n"
            "                    'label': 'Synthetic demo org'})\n"
            "worker = Worker.objects.create(\n"
            "    organization=org, given_name='Synthetic',\n"
            "    family_name='Persistence', birth_date=date(1990, 1, 1),\n"
            "    activity_profile='employee')\n"
            "payload = b'persistence-verification-source-bytes'\n"
            "digest = hashlib.sha256(payload).hexdigest()\n"
            "key = 'documents/' + ('a' * 32) + '/' + ('b' * 64) + '.source'\n"
            "document_storage().save(key, io.BytesIO(payload))\n"
            "document = Document.objects.create(\n"
            "    organization=org, worker=worker,\n"
            "    opaque_key=key, sha256=digest,\n"
            "    content_type='application/pdf')\n"
            "assignment = Assignment.objects.create(\n"
            "    organization=org, worker=worker, workplace_label='Brno',\n"
            "    activity_label=%r, start=date(2026, 1, 1),\n"
            "    end=date(2026, 2, 1))\n"
            "print(json.dumps({'worker_pk': worker.pk,\n"
            "    'document_pk': document.pk, 'assignment_pk': assignment.pk,\n"
            "    'sha256': digest}))\n" % activity_label
        )
        r = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c", seed_code],
            cwd=str(REPO_ROOT), env={**os.environ, **env},
            capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"seed failed:\n{r.stderr}"
        return json.loads(r.stdout.strip().splitlines()[-1])

    def _journey_receipt(self, ids):
        """Canonical nested journey evidence, as produced by
        tests/_rehearse_workflow_browser.py (stages.assignment_corrected)."""
        return {
            "ok": True,
            "profile": "core",
            "organization_id": 1,
            "worker_pk": ids["worker_pk"],
            "document_pk": ids["document_pk"],
            "assignment_pk": ids["assignment_pk"],
            "source_document_sha256": ids["sha256"],
            "stages": {
                "assignment_corrected": {
                    "ok": True,
                    "stage": "assignment_corrected",
                    "assignment_pk": ids["assignment_pk"],
                    "corrected_activity": self.JOURNEY_LABEL,
                },
            },
        }

    def _write_receipt(self, tmp_root, ids):
        path = tmp_root / "journey-evidence.json"
        path.write_text(json.dumps(self._journey_receipt(ids)))
        os.chmod(str(path), 0o600)
        return path

    def _journey_env(self, tmp_root, env, ids):
        env = dict(env)
        env.update({
            "JOURNEY_EVIDENCE_PATH": str(tmp_root / "journey-evidence.json"),
            "ORG_PK": "1",
            "WORKER_PK": str(ids["worker_pk"]),
            "DOCUMENT_PK": str(ids["document_pk"]),
            "ASSIGNMENT_PK": str(ids["assignment_pk"]),
            "DOCUMENT_SHA256": ids["sha256"],
        })
        assert "CORRECTED_ACTIVITY_LABEL" not in env
        assert "CORRECTED_ACTIVITY_LABEL" not in os.environ
        return env

    def test_receipt_shape_loads_label_and_passes(self):
        """The label must come from stages.assignment_corrected in the
        receipt — never from an explicitly supplied env variable."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 0, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "ok  assignment_corrected_value" in r.stdout

    def test_mutated_stored_label_fails_with_exact_values(self):
        """Negative case: keep the receipt unchanged, mutate the stored
        assignment label in the database, and require failure naming both
        the journey value and the drifted stored value."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            env = self._journey_env(tmp_root, env, ids)
            self._write_receipt(tmp_root, ids)
            mutated = self.JOURNEY_LABEL + " (tampered)"
            r = subprocess.run(
                [sys.executable, "manage.py", "shell", "-c",
                 "from portal.release1a.models import Assignment\n"
                 f"Assignment.objects.filter(pk={ids['assignment_pk']})"
                 ".update(activity_label=%r)\n" % mutated],
                cwd=str(REPO_ROOT), env={**os.environ, **env},
                capture_output=True, text=True, timeout=120)
            assert r.returncode == 0, f"mutation failed:\n{r.stderr}"
            r = _run(["--profile", "core"], env)
            assert r.returncode == 1, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "FAIL assignment_corrected_value" in r.stderr
            assert self.JOURNEY_LABEL in r.stderr
            assert "(tampered)" in r.stderr
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" not in r.stderr

    def test_malformed_correction_evidence_blocks(self):
        """A receipt claiming a successful correction without the label must
        block (exit 2), never silently skip the comparison."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            env = self._journey_env(tmp_root, env, ids)
            receipt = self._journey_receipt(ids)
            receipt["stages"]["assignment_corrected"].pop("corrected_activity")
            (tmp_root / "journey-evidence.json").write_text(json.dumps(receipt))
            os.chmod(str(tmp_root / "journey-evidence.json"), 0o600)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr
            assert "corrected_activity" in r.stderr


    def test_absent_correction_evidence_skips_legacy(self):
        """A receipt whose stages lack an assignment_corrected key entirely keeps
        the legacy behavior: the corrected-value check is omitted and the verifier
        proceeds with the other checks (exit 0 when rows exist), never treated as
        malformed supplied evidence. A deliberately absent legacy stage is
        distinguished from a present-but-malformed one, which blocks (exit 2)."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            env = self._journey_env(tmp_root, env, ids)
            receipt = self._journey_receipt(ids)
            receipt["stages"].pop("assignment_corrected", None)  # absent, not malformed
            (tmp_root / "journey-evidence.json").write_text(json.dumps(receipt))
            os.chmod(str(tmp_root / "journey-evidence.json"), 0o600)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 0, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            outcome = json.loads(r.stdout.strip().splitlines()[-1])
            assert "assignment_corrected_value" not in outcome["checks"], (
                f"unexpected corrected-value check in outcome: {outcome['checks']}"
            )


    def test_non_dict_correction_evidence_blocks(self):
        """A receipt where the correction stage is present but is not a JSON
        object must block (exit 2) rather than silently skip."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            env = self._journey_env(tmp_root, env, ids)
            receipt = self._journey_receipt(ids)
            receipt["stages"]["assignment_corrected"] = "invalid"
            (tmp_root / "journey-evidence.json").write_text(json.dumps(receipt))
            os.chmod(str(tmp_root / "journey-evidence.json"), 0o600)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr
            assert "not a JSON object" in r.stderr

    def test_assignment_pk_mismatch_between_receipt_and_selection_blocks(self):
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            env = self._journey_env(tmp_root, env, ids)
            receipt = self._journey_receipt(ids)
            receipt["stages"]["assignment_corrected"]["assignment_pk"] = 99999
            (tmp_root / "journey-evidence.json").write_text(json.dumps(receipt))
            os.chmod(str(tmp_root / "journey-evidence.json"), 0o600)
            r = _run(["--profile", "core"], env)
            assert r.returncode == 2, f"rc={r.returncode}\n{r.stdout}\n{r.stderr}"
            assert "does not match" in r.stderr

    def test_receipt_permissions_are_restricted(self):
        """Journey evidence carries PII-bearing identifiers; the verifier must
        reject a receipt file readable by group or others (0664) and must
        accept an owner-only file (0600)."""
        with tempfile.TemporaryDirectory(
                prefix="supervised-persistence-test-",
                dir=str(REPO_ROOT / "runtime" / "portal")) as tmp:
            tmp_root = Path(tmp)
            os.chmod(str(tmp_root), 0o700)
            env = _migrated_runtime_env(tmp_root)
            ids = self._seed_rows(tmp_root, env, self.JOURNEY_LABEL)
            base_env = self._journey_env(tmp_root, env, ids)

            receipt = self._journey_receipt(ids)

            # 0664: group/other readable -> must block with exit 2.
            insecure = tmp_root / "insecure-receipt.json"
            insecure.write_text(json.dumps(receipt))
            insecure.chmod(0o664)
            bad_env = dict(base_env)
            bad_env["JOURNEY_EVIDENCE_PATH"] = str(insecure)
            r = _run(["--profile", "core"], bad_env)
            assert r.returncode == 2, (
                f"rc={r.returncode} (expected 2 for insecure permissions)\n"
                f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}")
            assert "insecure permissions" in r.stderr.lower() or \
                "PERSISTENCE_ACCEPTANCE_BLOCKED" in r.stderr, (
                f"expected a permissions block:\n{r.stderr}")

            # 0600: owner-only -> must not block on permissions (exit 2
            # would mean the permission check fired; a different non-zero
            # exit is fine because rows do not exist in this isolated DB).
            secure = tmp_root / "secure-receipt.json"
            secure.write_text(json.dumps(receipt))
            secure.chmod(0o600)
            good_env = dict(base_env)
            good_env["JOURNEY_EVIDENCE_PATH"] = str(secure)
            r = _run(["--profile", "core"], good_env)
            assert "insecure permissions" not in r.stderr.lower(), (
                f"0600 receipt should not trigger a permissions block:\n"
                f"{r.stderr}")
