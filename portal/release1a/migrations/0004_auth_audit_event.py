# AuthAuditEvent model — initial migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("release1a", "0003_release1a_review_sessions"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthAuditEvent",
            fields=[
                ("id", models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=80)),
                ("outcome", models.CharField(max_length=20)),
                ("actor_ref", models.CharField(blank=True, default="", max_length=80)),
                ("organization_id", models.IntegerField(null=True, blank=True)),
                ("object_ref", models.CharField(blank=True, default="", max_length=100)),
                ("reason_code", models.CharField(blank=True, default="", max_length=40)),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["id"]},
        ),
    ]
