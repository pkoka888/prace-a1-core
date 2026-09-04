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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization", "role"],
                name="unique_org_role"
            )
        ]


class Release1aReviewSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    build_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization", "build_id"],
                name="unique_user_org_build"
            )
        ]


class Release1aReview(models.Model):
    class Section(models.TextChoices):
        WORKER = "worker", "Pracovník"
        DOCUMENT_OCR = "document_ocr", "Dokument a kontrola OCR"
        ASSIGNMENT = "assignment", "Přiřazení"
        A1 = "a1", "Příprava a kontrola A1"

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Nezahájeno"
        IN_PROGRESS = "in_progress", "Rozpracováno"
        DONE = "done", "Dokončeno"
        NEEDS_CHANGE = "needs_change", "Vyžaduje opravu"

    session = models.ForeignKey(Release1aReviewSession, on_delete=models.CASCADE)
    section = models.CharField(max_length=24, choices=Section.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOT_STARTED)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "section"],
                name="unique_session_section"
            )
        ]
        ordering = ["section"]

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


class Release1aAcceptance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    session = models.ForeignKey(Release1aReviewSession, on_delete=models.PROTECT)
    accepted_at = models.DateTimeField(auto_now_add=True)
    git_commit_hash = models.CharField(max_length=40)
    git_clean = models.BooleanField(default=False)
    app_build_id = models.CharField(max_length=64)
    scope_text = models.TextField(default="")
    exclusions_text = models.TextField(default="")
    browser_user_agent = models.TextField(blank=True, default="")
    exceptions_json = models.TextField(default="[]")
    is_stale = models.BooleanField(default=False)

    class Meta:
        ordering = ["-accepted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["session"],
                name="unique_acceptance_per_session"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Release1aAcceptance is immutable; create a new record instead of updating existing.")
        return super().save(*args, **kwargs)

class TenantModel(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    class Meta: abstract = True

class Worker(TenantModel):
    given_name = models.CharField(max_length=80)
    family_name = models.CharField(max_length=80)
    birth_date = models.DateField()
    activity_profile = models.CharField(max_length=32, choices=[("employee", "Zaměstnanec"), ("self_employed", "OSVČ")])

    class State(models.TextChoices):
        DRAFT = "draft", "Rozpracováno"
        ACTIVE = "active", "Aktivní"
        ARCHIVED = "archived", "Archivováno"

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    version = models.PositiveIntegerField(default=1)

class Document(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    opaque_key = models.CharField(max_length=100, unique=True)
    sha256 = models.CharField(max_length=64)
    content_type = models.CharField(max_length=80)

    class State(models.TextChoices):
        QUARANTINED = "quarantined", "V karanténě"
        PROPOSAL_READY = "proposal_ready", "Navrhováno"
        CONFIRMED = "confirmed", "Potvrzeno"
        REJECTED = "rejected", "Zamítnuto"
        SUPERSEDED = "superseded", "Nahrazeno"

    state = models.CharField(max_length=24, choices=State.choices, default=State.QUARANTINED)
    class Meta: constraints = [models.UniqueConstraint(fields=["organization", "sha256"], name="unique_org_document_hash")]

class Assignment(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    workplace_label = models.CharField(max_length=160)
    activity_label = models.CharField(max_length=120)
    start = models.DateField(); end = models.DateField()

    class State(models.TextChoices):
        PLANNED = "planned", "Plánováno"
        ACTIVE = "active", "Aktivní"
        COMPLETED = "completed", "Dokončeno"
        CANCELLED = "cancelled", "Zrušeno"

    state = models.CharField(max_length=20, choices=State.choices, default=State.PLANNED)
    version = models.PositiveIntegerField(default=1)

class A1Case(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    source_hash = models.CharField(max_length=64)

    class Readiness(models.TextChoices):
        BLOCKED = "blocked", "Blokováno"
        READY = "ready", "Připraveno"

    readiness = models.CharField(max_length=20, choices=Readiness.choices)

    class ExternalStatus(models.TextChoices):
        NOT_SUBMITTED = "not_submitted", "Nepředáno"
        SUBMITTED = "submitted", "Předáno OSSZ"
        ISSUED = "issued", "Vydáno certifikát"
        REJECTED = "rejected", "Zamítnuto OSSZ"
        DENIED = "denied", "Zamítnuto"

    prepared_artifact_hash = models.CharField(max_length=64, blank=True)
    external_status = models.CharField(max_length=32, choices=ExternalStatus.choices, default=ExternalStatus.NOT_SUBMITTED)

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


class AuthAuditEvent(models.Model):
    event_type = models.CharField(max_length=80)
    outcome = models.CharField(max_length=20)
    actor_ref = models.CharField(max_length=80, blank=True, default="")
    organization_id = models.IntegerField(null=True, blank=True)
    object_ref = models.CharField(max_length=100, blank=True, default="")
    reason_code = models.CharField(max_length=40, blank=True, default="")
    occurred_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["id"]
    def save(self, *args, **kwargs):
        if self.pk: raise ValueError("AuthAuditEvent is append-only")
        return super().save(*args, **kwargs)


class IntakeSession(TenantModel):
    """Tracks a multi-step intake session for a worker."""

    class Purpose(models.TextChoices):
        A1 = "a1", "Příprava A1"
        ASSIGNMENT = "assignment", "Přiřazení"
        PAYROLL = "payroll", "Mzdové podklady"

    class State(models.TextChoices):
        DRAFT = "draft", "Rozpracováno"
        INTAKE_COMPLETE = "intake_complete", "Intake dokončen"
        MERGED = "merged", "Sloučeno"
        ARCHIVED = "archived", "Archivováno"

    worker = models.ForeignKey(Worker, models.PROTECT, null=True, blank=True)
    purpose = models.CharField(max_length=24, choices=Purpose.choices)
    state = models.CharField(max_length=24, choices=State.choices, default=State.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DocumentVersion(TenantModel):
    """Immutable version of a document - original bytes stored securely."""

    document = models.ForeignKey(Document, models.CASCADE)
    version_number = models.PositiveIntegerField()
    opaque_key = models.CharField(max_length=100)
    sha256 = models.CharField(max_length=64)
    content_type = models.CharField(max_length=80)
    byte_size = models.PositiveIntegerField()
    quarantine_result = models.CharField(max_length=24, blank=True, default="")
    malware_result = models.CharField(max_length=24, blank=True, default="")
    mime_result = models.CharField(max_length=24, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="unique_doc_version"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("DocumentVersion is immutable")
        return super().save(*args, **kwargs)


class DocumentClassification(TenantModel):
    """Classification result for a document page or side."""

    document = models.ForeignKey(Document, models.CASCADE)
    version = models.ForeignKey(DocumentVersion, models.CASCADE)
    page_index = models.PositiveIntegerField(default=0)
    side = models.CharField(max_length=16, blank=True, default="")

    class DocType(models.TextChoices):
        CZ_ID_FRONT = "cz_id_front", "OP přední strana"
        CZ_ID_BACK = "cz_id_back", "OP zadní strana"
        CZ_HEALTH_CARD_FRONT = "cz_health_card_front", "ZP přední strana"
        CZ_HEALTH_CARD_BACK = "cz_health_card_back", "ZP zadní strana"
        UNKNOWN = "unknown", "Neznámý"

    doc_type = models.CharField(max_length=24, choices=DocType.choices, default=DocType.UNKNOWN)
    doc_type_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    side_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    is_human_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class OcrRun(TenantModel):
    """An OCR processing run for a document version."""

    class Engine(models.TextChoices):
        LOCAL = "local", "Lokální OCR"
        RAPIDOCR = "rapidocr", "RapidOCR"

    class State(models.TextChoices):
        PENDING = "pending", "Čeká"
        RUNNING = "running", "Běží"
        COMPLETED = "completed", "Dokončeno"
        FAILED = "failed", "Selhalo"

    document = models.ForeignKey(Document, models.CASCADE)
    version = models.ForeignKey(DocumentVersion, models.CASCADE)
    engine = models.CharField(max_length=24, choices=Engine.choices, default=Engine.LOCAL)
    engine_version = models.CharField(max_length=40, blank=True, default="")
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)
    failure_reason = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FieldProposal(TenantModel):
    """OCR-proposed field value with full provenance."""

    class State(models.TextChoices):
        MISSING = "missing", "Chybí"
        PROPOSED = "proposed", "Navrženo"
        CONFIRMED = "confirmed", "Potvrzeno"
        CONFLICT = "conflict", "Konflikt"
        SUPERSEDED = "superseded", "Nahrazeno"

    document = models.ForeignKey(Document, models.CASCADE)
    version = models.ForeignKey(DocumentVersion, models.CASCADE)
    ocr_run = models.ForeignKey(OcrRun, models.CASCADE, null=True, blank=True)
    field_name = models.CharField(max_length=80)
    raw_ocr_text = models.TextField(blank=True, default="")
    proposed_value = models.CharField(max_length=240)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    doc_class_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_bounding_box = models.JSONField(null=True, blank=True)
    source_text_offset = models.PositiveIntegerField(null=True, blank=True)
    ocr_engine = models.CharField(max_length=24, blank=True, default="")
    ocr_model_version = models.CharField(max_length=40, blank=True, default="")
    validation_findings = models.JSONField(default=list)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PROPOSED)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk and self.state == self.State.CONFIRMED:
            raise ValueError("Confirmed FieldProposal cannot be modified")
        return super().save(*args, **kwargs)


class FieldDecision(TenantModel):
    """Human decision on a field proposal."""

    field_proposal = models.ForeignKey(FieldProposal, models.CASCADE)
    decision = models.CharField(max_length=24)
    corrected_value = models.CharField(max_length=240, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, null=True, blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)


class WorkerIdentityRevision(TenantModel):
    """Revision tracking for confirmed worker identity fields."""

    worker = models.ForeignKey(Worker, models.CASCADE)
    source_document = models.ForeignKey(Document, models.PROTECT, null=True, blank=True)
    source_version = models.ForeignKey(DocumentVersion, models.PROTECT, null=True, blank=True)
    revision_number = models.PositiveIntegerField(default=1)
    confirmed_fields = models.JSONField(default=dict)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, null=True, blank=True)


class ReviewTask(TenantModel):
    """Task for human review of proposals or conflicts."""

    class TaskType(models.TextChoices):
        OCR_REVIEW = "ocr_review", "Kontrola OCR"
        FIELD_REVIEW = "field_review", "Kontrola pole"
        CONFLICT_RESOLUTION = "conflict_resolution", "Řešení konfliktu"
        DOCUMENT_REVIEW = "document_review", "Kontrola dokumentu"

    class Priority(models.TextChoices):
        LOW = "low", "Nízká"
        MEDIUM = "medium", "Střední"
        HIGH = "high", "Vysoká"
        URGENT = "urgent", "Urgentní"

    class State(models.TextChoices):
        PENDING = "pending", "Čeká"
        IN_PROGRESS = "in_progress", "V řešení"
        COMPLETED = "completed", "Dokončeno"
        CANCELLED = "cancelled", "Zrušeno"

    worker = models.ForeignKey(Worker, models.CASCADE, null=True, blank=True)
    document = models.ForeignKey(Document, models.CASCADE, null=True, blank=True)
    task_type = models.CharField(max_length=24, choices=TaskType.choices)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    description = models.TextField(blank=True, default="")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class StatusEvent(TenantModel):
    """Audit trail for worker/document/assignment status changes."""

    class EventType(models.TextChoices):
        WORKER_CREATED = "worker.created", "Pracovník vytvořen"
        WORKER_UPDATED = "worker.updated", "Pracovník aktualizován"
        WORKER_ARCHIVED = "worker.archived", "Pracovník archivován"
        DOCUMENT_UPLOADED = "document.uploaded", "Dokument nahrán"
        DOCUMENT_QUARANTINE = "document.quarantine", "Dokument v karanténě"
        DOCUMENT_CONFIRMED = "document.confirmed", "Dokument potvrzen"
        OCR_PROPOSED = "ocr.proposed", "OCR navrženo"
        OCR_CONFIRMED = "ocr.confirmed", "OCR potvrzeno"
        ASSIGNMENT_CREATED = "assignment.created", "Přiřazení vytvořeno"
        ASSIGNMENT_UPDATED = "assignment.updated", "Přiřazení aktualizováno"
        A1_PREPARED = "a1.prepared", "A1 připraveno"
        A1_APPROVED = "a1.approved", "A1 schváleno"
        A1_DENIED = "a1.denied", "A1 zamítnuto"

    event_type = models.CharField(max_length=40, choices=EventType.choices)
    actor_ref = models.CharField(max_length=80)
    object_ref = models.CharField(max_length=100)
    outcome = models.CharField(max_length=20)
    occurred_at = models.DateTimeField(auto_now_add=True)
    metadata_json = models.TextField(default="{}")

    class Meta:
        ordering = ["-occurred_at"]
        verbose_name_plural = "Status events"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("StatusEvent is append-only")
        return super().save(*args, **kwargs)

