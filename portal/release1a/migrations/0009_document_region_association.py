"""Restore the documented historical document/J4 schema stage."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0008_shared_document_intake"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="fieldproposal",
            name="document_region_id",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
        migrations.CreateModel(
            name="DocumentRegionAssociation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("region_id", models.CharField(max_length=36)),
                ("document_type", models.CharField(blank=True, default="", max_length=24)),
                ("issuer", models.CharField(blank=True, default="", max_length=8)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "decided_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ocr_run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="release1a.ocrrun"
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="release1a.organization"
                    ),
                ),
                (
                    "worker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="release1a.worker"
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("ocr_run", "region_id"),
                        name="unique_run_region_association",
                    )
                ],
            },
        ),
    ]
