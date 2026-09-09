"""Persist machine evaluations, draft claims and source-bound human resolutions."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0013_alter_a1case_visual_confirmed_by"),
    ]

    operations = [
        migrations.CreateModel(
            name="IdentityEvaluation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evaluation_sha256", models.CharField(max_length=64)),
                ("evidence", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.organization")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("organization", "evaluation_sha256"), name="unique_org_identity_evaluation")],
            },
        ),
        migrations.CreateModel(
            name="WorkerIdentityClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier_sha256", models.CharField(max_length=64)),
                ("region_id", models.CharField(max_length=36)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.organization")),
                ("worker", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.worker")),
                ("evaluation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.identityevaluation")),
                ("ocr_run", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.ocrrun")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("organization", "identifier_sha256"), name="unique_org_identity_claim")],
            },
        ),
        migrations.CreateModel(
            name="IdentityResolution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("worker_version", models.PositiveIntegerField()),
                ("reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.organization")),
                ("evaluation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="release1a.identityevaluation")),
                ("association", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to="release1a.documentregionassociation")),
                ("worker_revision", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="release1a.workeridentityrevision")),
            ],
        ),
    ]
