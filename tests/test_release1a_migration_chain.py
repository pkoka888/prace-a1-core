"""Historical migration acceptance without service settings or a persistent DB."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def test_document_and_j4_historical_states_and_model_parity():
    # A separate interpreter isolates Django from other tests' app registries.
    program = textwrap.dedent('''
        import django
        from django.conf import settings
        from portal import settings as defaults

        config = {key: getattr(defaults, key) for key in dir(defaults) if key.isupper()}
        config["DATABASES"] = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
        settings.configure(**config)
        django.setup()

        from django.apps import apps
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.state import ProjectState

        def advance(name):
            target = [("release1a", name)]
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            return executor.loader.project_state(target).apps

        historical = advance("0007_add_state_textchoices")
        org = historical.get_model("release1a", "Organization").objects.create(
            key="migration-synthetic", label="Synthetic migration fixture")
        worker = historical.get_model("release1a", "Worker").objects.create(
            organization_id=org.pk, given_name="Synthetic", family_name="Fixture",
            birth_date="1990-01-01")
        document = historical.get_model("release1a", "Document").objects.create(
            organization_id=org.pk, worker_id=worker.pk, opaque_key="synthetic-original",
            sha256="a" * 64, content_type="image/png")

        historical = advance("0009_document_region_association")
        Document = historical.get_model("release1a", "Document")
        preserved = Document.objects.get(pk=document.pk)
        assert preserved.worker_id == worker.pk
        assert preserved.opaque_key == "synthetic-original"
        assert preserved.purpose == "worker_intake"
        unassigned = Document.objects.create(organization_id=org.pk, worker=None,
            opaque_key="synthetic-unassigned", sha256="b" * 64, content_type="image/png")
        assert unassigned.worker_id is None

        historical = advance("0010_a1case_j4_minimum")
        case = historical.get_model("release1a", "A1Case").objects.create(
            organization_id=org.pk, worker_id=worker.pk, source_hash="c" * 64,
            source_snapshot_json={"synthetic": True}, readiness="blocked")
        historical = advance("0011_a1case_artifact_evidence")
        preserved = historical.get_model("release1a", "A1Case").objects.get(pk=case.pk)
        assert preserved.source_snapshot_json == {"synthetic": True}
        assert preserved.artifact_reference == {}
        assert preserved.artifact_dependencies == {}

        historical = advance("0013_alter_a1case_visual_confirmed_by")
        Case = historical.get_model("release1a", "A1Case")
        preserved = Case.objects.get(pk=case.pk)
        assert preserved.source_snapshot_json == {"synthetic": True}
        assert preserved.visual_confirmed is False
        assert preserved.visual_confirmed_by_id is None
        assert Case._meta.get_field("visual_confirmed_by").remote_field.related_name == "visual_confirmations"

        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        assert not executor.loader.detect_conflicts()
        changes = MigrationAutodetector(executor.loader.project_state(),
            ProjectState.from_apps(apps)).changes(graph=executor.loader.graph)
        assert not changes.get("release1a"), changes.get("release1a")
        connection.close()
    ''')
    env = dict(os.environ)
    env.pop("DJANGO_SETTINGS_MODULE", None)
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=Path(__file__).resolve().parents[1], env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
