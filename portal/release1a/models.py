from django.conf import settings
from django.db import models

class Organization(models.Model):
    key = models.SlugField(unique=True)
    label = models.CharField(max_length=120)

class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=32)
    active = models.BooleanField(default=True)
    mfa_verified = models.BooleanField(default=False)
    class Meta: constraints = [models.UniqueConstraint(fields=["user", "organization", "role"], name="unique_org_role")]

class TenantModel(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    class Meta: abstract = True

class Worker(TenantModel):
    given_name = models.CharField(max_length=80)
    family_name = models.CharField(max_length=80)
    birth_date = models.DateField()
    activity_profile = models.CharField(max_length=32, choices=[("employee", "Zaměstnanec"), ("self_employed", "OSVČ")])
    state = models.CharField(max_length=20, default="draft")
    version = models.PositiveIntegerField(default=1)

class Document(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    opaque_key = models.CharField(max_length=100, unique=True)
    sha256 = models.CharField(max_length=64)
    content_type = models.CharField(max_length=80)
    state = models.CharField(max_length=24, default="quarantined")
    class Meta: constraints = [models.UniqueConstraint(fields=["organization", "sha256"], name="unique_org_document_hash")]

class OcrProposal(TenantModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=80)
    proposed_value = models.CharField(max_length=240)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    confirmed = models.BooleanField(default=False)

class Assignment(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    workplace_label = models.CharField(max_length=160)
    activity_label = models.CharField(max_length=120)
    start = models.DateField(); end = models.DateField()
    state = models.CharField(max_length=20, default="planned")
    version = models.PositiveIntegerField(default=1)

class A1Case(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    source_hash = models.CharField(max_length=64)
    readiness = models.CharField(max_length=20)
    prepared_artifact_hash = models.CharField(max_length=64, blank=True)
    external_status = models.CharField(max_length=32, default="not_submitted")

class AuditEvent(TenantModel):
    actor_ref = models.CharField(max_length=80)
    event_type = models.CharField(max_length=80)
    object_ref = models.CharField(max_length=100)
    outcome = models.CharField(max_length=20)
    occurred_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["id"]
    def save(self, *args, **kwargs):
        if self.pk: raise ValueError("AuditEvent is append-only")
        return super().save(*args, **kwargs)

