"""Restore the documented historical document/J4 schema stage."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0010_a1case_j4_minimum"),
    ]

    operations = [
        migrations.AddField(
            model_name="a1case",
            name="artifact_reference",
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name="a1case",
            name="artifact_dependencies",
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
