"""Restore the documented historical document/J4 schema stage."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0009_document_region_association"),
    ]

    operations = [
        migrations.AddField(
            model_name="a1case",
            name="source_snapshot_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="a1case",
            name="is_stale",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="a1case",
            name="receipt_build_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="a1case",
            name="receipt_git_commit",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="a1case",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
