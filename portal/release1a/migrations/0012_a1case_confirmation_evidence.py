"""Add A1Case visual-confirmation and evidence-intake fields consumed by J4 views."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0011_a1case_artifact_evidence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name="a1case",
            name="visual_confirmed",
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.AddField(
            model_name="a1case",
            name="visual_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="a1case",
            name="visual_confirmed_by",
            field=models.ForeignKey(
                settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="a1case",
            name="visual_confirmation_notes",
            field=models.TextField(blank=True, db_default="", default=""),
        ),
        migrations.AddField(
            model_name="a1case",
            name="visual_confirmation_receipt",
            field=models.CharField(blank=True, db_default="", default="", max_length=400),
        ),
        migrations.AddField(
            model_name="a1case",
            name="evidence_documents",
            field=models.JSONField(blank=True, db_default="[]", default=list),
        ),
        migrations.AddField(
            model_name="a1case",
            name="evidence_notes",
            field=models.JSONField(blank=True, db_default="[]", default=list),
        ),
    ]
