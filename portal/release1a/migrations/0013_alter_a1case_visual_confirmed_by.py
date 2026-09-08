"""Align the confirmation reverse relation with the existing application model."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release1a", "0012_a1case_confirmation_evidence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="a1case",
            name="visual_confirmed_by",
            field=models.ForeignKey(
                settings.AUTH_USER_MODEL,
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                null=True,
                related_name="visual_confirmations",
            ),
        ),
    ]
