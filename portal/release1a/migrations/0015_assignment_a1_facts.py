"""Add structured A1 assignment facts without changing existing records' facts."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0014_identity_evaluation_and_draft_claim"),
    ]

    operations = [
        migrations.AddField(
            model_name="assignment",
            name="a1_facts_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
