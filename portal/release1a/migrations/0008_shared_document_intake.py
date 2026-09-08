"""Restore the documented historical document/J4 schema stage."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0007_add_state_textchoices"),
    ]

    operations = [
        migrations.AddField(
            model_name="intakesession",
            name="ocr_runs",
            field=models.ManyToManyField(
                blank=True, related_name="intake_sessions", to="release1a.ocrrun"
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="purpose",
            field=models.CharField(default="worker_intake", max_length=80),
        ),
        migrations.AddField(
            model_name="document",
            name="retention_review_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ocrrun",
            name="attempt_token",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="ocrrun",
            name="lease_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ocrrun",
            name="output_key",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="ocrrun",
            name="output_sha256",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AlterField(
            model_name="document",
            name="worker",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="release1a.worker"
            ),
        ),
        migrations.AlterField(
            model_name="documentclassification",
            name="doc_type",
            field=models.CharField(
                choices=[
                    ("cz_passport", "Cestovní pas"),
                    ("cz_id_front", "OP přední strana"),
                    ("cz_id_back", "OP zadní strana"),
                    ("cz_health_card_front", "ZP přední strana"),
                    ("cz_health_card_back", "ZP zadní strana"),
                    ("unknown", "Neznámý"),
                ],
                default="unknown",
                max_length=24,
            ),
        ),
        migrations.AddConstraint(
            model_name="ocrrun",
            constraint=models.UniqueConstraint(
                condition=models.Q(("idempotency_key", ""), _negated=True),
                fields=("organization", "idempotency_key"),
                name="unique_org_ocr_idempotency",
            ),
        ),
    ]
