import uuid
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
                fields=["user", "organization", "role"], name="unique_org_role"
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
                name="unique_user_org_build",
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
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.NOT_STARTED
    )
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "section"], name="unique_session_section"
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
                fields=["session"], name="unique_acceptance_per_session"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError(
                "Release1aAcceptance is immutable; create a new record instead of updating existing."
            )
        return super().save(*args, **kwargs)


class TenantModel(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)

    class Meta:
        abstract = True


class Worker(TenantModel):
    legacy_employee_id = models.CharField(max_length=120, null=True, blank=True)
    legacy_key_provenance = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "legacy_employee_id"],
                condition=models.Q(legacy_employee_id__isnull=False),
                name="unique_org_worker_legacy_key",
            ),
            models.CheckConstraint(
                condition=models.Q(legacy_employee_id__isnull=True)
                | ~models.Q(legacy_employee_id=""),
                name="worker_legacy_key_not_empty",
            ),
        ]

    given_name = models.CharField(max_length=80)
    family_name = models.CharField(max_length=80)
    birth_date = models.DateField()
    activity_profile = models.CharField(
        max_length=32, choices=[("employee", "Zaměstnanec"), ("self_employed", "OSVČ")]
    )

    class State(models.TextChoices):
        DRAFT = "draft", "Rozpracováno"
        ACTIVE = "active", "Aktivní"
        ARCHIVED = "archived", "Archivováno"

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    version = models.PositiveIntegerField(default=1)


class Document(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT, null=True, blank=True)
    purpose = models.CharField(max_length=80, default="worker_intake")
    retention_review_at = models.DateTimeField(null=True, blank=True)
    opaque_key = models.CharField(max_length=100, unique=True)
    sha256 = models.CharField(max_length=64)
    content_type = models.CharField(max_length=80)

    class State(models.TextChoices):
        QUARANTINED = "quarantined", "V karanténě"
        PROPOSAL_READY = "proposal_ready", "Navrhováno"
        CONFIRMED = "confirmed", "Potvrzeno"
        REJECTED = "rejected", "Zamítnuto"
        SUPERSEDED = "superseded", "Nahrazeno"

    state = models.CharField(
        max_length=24, choices=State.choices, default=State.QUARANTINED
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "sha256"], name="unique_org_document_hash"
            )
        ]


class Assignment(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    workplace_label = models.CharField(max_length=160)
    activity_label = models.CharField(max_length=120)
    a1_facts_json = models.JSONField(default=dict, blank=True)
    start = models.DateField()
    end = models.DateField()

    # Article 12 situation facts. They are conditions of the posting claim
    # rather than fields on the A1 form, so they are nullable and absent
    # means "not captured", never "no". Decision D10 and D1b (2026-10-20).
    # prior_activity_start: Article 14(3) of Regulation 987/2009 requires the
    # self-employed to have already pursued the activity before moving.
    prior_activity_start = models.DateField(null=True, blank=True)
    # replaces_worker: Article 12(1) of Regulation 883/2004 excludes a worker
    # sent to replace another posted person. Nullable tri-state: null means
    # the question has not been answered.
    replaces_worker = models.BooleanField(null=True, blank=True)

    class State(models.TextChoices):
        PLANNED = "planned", "Plánováno"
        ACTIVE = "active", "Aktivní"
        COMPLETED = "completed", "Dokončeno"
        CANCELLED = "cancelled", "Zrušeno"

    state = models.CharField(
        max_length=20, choices=State.choices, default=State.PLANNED
    )
    version = models.PositiveIntegerField(default=1)


class A1Case(TenantModel):
    worker = models.ForeignKey(Worker, on_delete=models.PROTECT)
    source_hash = models.CharField(max_length=64)
    source_snapshot_json = models.JSONField(default=dict, blank=True)
    # Identity binding adopted once for pre-``a1-j4-identity-v1`` rows so
    # later confirmed-identity drift is detected like profile/assignment drift.
    bound_identity_sha256 = models.CharField(max_length=64, blank=True, default="")
    is_stale = models.BooleanField(default=False)

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

    artifact_reference = models.JSONField(default=dict, blank=True)
    artifact_dependencies = models.JSONField(default=dict, blank=True)
    prepared_artifact_hash = models.CharField(max_length=64, blank=True)
    receipt_build_id = models.CharField(max_length=64, blank=True)
    receipt_git_commit = models.CharField(max_length=40, blank=True)
    external_status = models.CharField(
        max_length=32,
        choices=ExternalStatus.choices,
        default=ExternalStatus.NOT_SUBMITTED,
    )
    notes = models.TextField(blank=True, default="")

    # J4 visual confirmation fields
    visual_confirmed = models.BooleanField(default=False, db_default=False)
    visual_confirmed_at = models.DateTimeField(blank=True, null=True)
    visual_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="visual_confirmations",
    )
    visual_confirmation_notes = models.TextField(blank=True, default="", db_default="")
    visual_confirmation_receipt = models.CharField(
        max_length=400, blank=True, default="", db_default=""
    )
    evidence_documents = models.JSONField(default=list, blank=True, db_default="[]")
    evidence_notes = models.JSONField(default=list, blank=True, db_default="[]")

    def save(self, *args, **kwargs):
        if self.pk:
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .values(
                    "source_hash",
                    "source_snapshot_json",
                    "artifact_reference",
                    "artifact_dependencies",
                    "prepared_artifact_hash",
                )
                .first()
            )
            if previous:
                for field in ("source_hash", "source_snapshot_json"):
                    if previous[field] != getattr(self, field):
                        raise ValueError("A1_SNAPSHOT_IMMUTABLE")
                if previous["artifact_reference"]:
                    for field in (
                        "artifact_reference",
                        "artifact_dependencies",
                        "prepared_artifact_hash",
                    ):
                        if previous[field] != getattr(self, field):
                            raise ValueError("A1_ARTIFACT_IMMUTABLE")
        return super().save(*args, **kwargs)


class A1DraftReservation(TenantModel):
    """Immutable machine draft identity; never an issued certificate or approval."""

    case = models.OneToOneField(
        A1Case, on_delete=models.PROTECT, related_name="draft_reservation"
    )
    document_id = models.CharField(max_length=64, unique=True)
    reference_date = models.DateField()
    package_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    snapshot = models.JSONField()
    snapshot_sha256 = models.CharField(max_length=64)
    dependencies = models.JSONField()

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("A1_DRAFT_RESERVATION_IMMUTABLE")
        return super().save(*args, **kwargs)


class A1DraftGeneration(TenantModel):
    """Immutable render inputs and write-once package for a stable draft identity."""

    reservation = models.ForeignKey(
        A1DraftReservation, on_delete=models.PROTECT, related_name="generations"
    )
    revision = models.PositiveIntegerField()
    fingerprint = models.CharField(max_length=64)
    package_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    snapshot = models.JSONField()
    snapshot_sha256 = models.CharField(max_length=64)
    dependencies = models.JSONField()
    artifact_reference = models.JSONField(default=dict, blank=True)
    artifact_dependencies = models.JSONField(default=dict, blank=True)
    prepared_artifact_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reservation", "revision"], name="unique_a1_draft_revision"
            ),
            models.UniqueConstraint(
                fields=["reservation", "fingerprint"],
                name="unique_a1_draft_fingerprint",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.organization_id != self.reservation.organization_id:
            raise ValueError("A1_DRAFT_GENERATION_ORGANIZATION_MISMATCH")
        immutable = (
            "organization_id",
            "reservation_id",
            "revision",
            "fingerprint",
            "package_key",
            "snapshot",
            "snapshot_sha256",
            "dependencies",
        )
        artifacts = (
            "artifact_reference",
            "artifact_dependencies",
            "prepared_artifact_hash",
        )
        if self.pk:
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .values(*immutable, *artifacts)
                .first()
            )
            if previous:
                if any(previous[field] != getattr(self, field) for field in immutable):
                    raise ValueError("A1_DRAFT_GENERATION_IMMUTABLE")
                if previous["artifact_reference"] and any(
                    previous[field] != getattr(self, field) for field in artifacts
                ):
                    raise ValueError("A1_DRAFT_GENERATION_ARTIFACT_IMMUTABLE")
        return super().save(*args, **kwargs)


class A1GenerationConfirmation(TenantModel):
    """Operator visual review of one exact package, never identity verification."""

    generation = models.OneToOneField(
        A1DraftGeneration, models.PROTECT, related_name="visual_confirmation"
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    source_hash = models.CharField(max_length=64)
    fingerprint = models.CharField(max_length=64)
    receipt_sha256 = models.CharField(max_length=64)
    pdf_sha256 = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("A1_GENERATION_CONFIRMATION_IMMUTABLE")
        if self.organization_id != self.generation.organization_id:
            raise ValueError("A1_GENERATION_CONFIRMATION_ORGANIZATION_MISMATCH")
        return super().save(*args, **kwargs)


class AuditEvent(TenantModel):
    actor_ref = models.CharField(max_length=80)
    event_type = models.CharField(max_length=80)
    object_ref = models.CharField(max_length=100)
    outcome = models.CharField(max_length=20)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuditEvent is append-only")
        return super().save(*args, **kwargs)


class AuthAuditEvent(models.Model):
    event_type = models.CharField(max_length=80)
    outcome = models.CharField(max_length=20)
    actor_ref = models.CharField(max_length=80, blank=True, default="")
    organization_id = models.IntegerField(null=True, blank=True)
    object_ref = models.CharField(max_length=100, blank=True, default="")
    reason_code = models.CharField(max_length=40, blank=True, default="")
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuthAuditEvent is append-only")
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

    ocr_runs = models.ManyToManyField(
        "OcrRun", related_name="intake_sessions", blank=True
    )
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
                fields=["document", "version_number"], name="unique_doc_version"
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
        CZ_PASSPORT = "cz_passport", "Cestovní pas"
        CZ_ID_FRONT = "cz_id_front", "OP přední strana"
        CZ_ID_BACK = "cz_id_back", "OP zadní strana"
        CZ_HEALTH_CARD_FRONT = "cz_health_card_front", "ZP přední strana"
        CZ_HEALTH_CARD_BACK = "cz_health_card_back", "ZP zadní strana"
        UNKNOWN = "unknown", "Neznámý"

    doc_type = models.CharField(
        max_length=24, choices=DocType.choices, default=DocType.UNKNOWN
    )
    doc_type_confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    side_confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    is_human_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class OcrRun(TenantModel):
    """An OCR processing run for a document version. Derivatives never replace originals."""

    output_key = models.CharField(max_length=160, blank=True, default="")
    output_sha256 = models.CharField(max_length=64, blank=True, default="")
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    attempt_token = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="unique_org_ocr_idempotency",
            )
        ]

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
    engine = models.CharField(
        max_length=24, choices=Engine.choices, default=Engine.LOCAL
    )
    engine_version = models.CharField(max_length=40, blank=True, default="")
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PENDING
    )
    idempotency_key = models.CharField(max_length=80, blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)
    failure_reason = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DocumentRegionAssociation(TenantModel):
    """Explicit human association; immutable and independent of upload context."""

    ocr_run = models.ForeignKey(OcrRun, models.PROTECT)
    region_id = models.CharField(max_length=36)
    document_type = models.CharField(max_length=24, blank=True, default="")
    issuer = models.CharField(max_length=8, blank=True, default="")
    worker = models.ForeignKey(Worker, models.PROTECT)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["ocr_run", "region_id"], name="unique_run_region_association"
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("DocumentRegionAssociation is immutable")
        return super().save(*args, **kwargs)


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
    document_region_id = models.CharField(max_length=36, blank=True, default="")
    field_name = models.CharField(max_length=80)
    raw_ocr_text = models.TextField(blank=True, default="")
    proposed_value = models.CharField(max_length=240)
    confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    doc_class_confidence = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_bounding_box = models.JSONField(null=True, blank=True)
    source_text_offset = models.PositiveIntegerField(null=True, blank=True)
    ocr_engine = models.CharField(max_length=24, blank=True, default="")
    ocr_model_version = models.CharField(max_length=40, blank=True, default="")
    validation_findings = models.JSONField(default=list)
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PROPOSED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("FieldProposal cannot be modified")
        return super().save(*args, **kwargs)


class FieldDecision(TenantModel):
    """Human decision on a field proposal."""

    field_proposal = models.ForeignKey(FieldProposal, models.CASCADE)
    decision = models.CharField(max_length=24)
    corrected_value = models.CharField(max_length=240, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.PROTECT, null=True, blank=True
    )
    decided_at = models.DateTimeField(auto_now_add=True)


class WorkerIdentityRevision(TenantModel):
    """Revision tracking for confirmed worker identity fields."""

    worker = models.ForeignKey(Worker, models.CASCADE)
    source_document = models.ForeignKey(Document, models.PROTECT, null=True, blank=True)
    source_version = models.ForeignKey(
        DocumentVersion, models.PROTECT, null=True, blank=True
    )
    revision_number = models.PositiveIntegerField(default=1)
    confirmed_fields = models.JSONField(default=dict)
    confirmed_at = models.DateTimeField(auto_now_add=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.PROTECT, null=True, blank=True
    )


class IdentityEvaluation(TenantModel):
    """Source-bound machine evidence; never a human identity confirmation."""

    evaluation_sha256 = models.CharField(max_length=64)
    evidence = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "evaluation_sha256"],
                name="unique_org_identity_evaluation",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("IdentityEvaluation is immutable")
        return super().save(*args, **kwargs)


class WorkerIdentityClaim(TenantModel):
    """Machine draft origin claim, distinct from a confirmed identifier.

    The service hashes the organization, identifier type, issuer and normalized
    identifier into identifier_sha256 before creating the claim.
    """

    identifier_sha256 = models.CharField(max_length=64)
    worker = models.ForeignKey(Worker, models.PROTECT)
    evaluation = models.ForeignKey(IdentityEvaluation, models.PROTECT)
    ocr_run = models.ForeignKey(OcrRun, models.PROTECT)
    region_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "identifier_sha256"],
                name="unique_org_identity_claim",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("WorkerIdentityClaim is immutable")
        return super().save(*args, **kwargs)


class IdentityResolution(TenantModel):
    """Bind evaluated evidence and worker revision to a human association.

    The association retains the confirming actor, time and document source.
    """

    evaluation = models.ForeignKey(IdentityEvaluation, models.PROTECT)
    association = models.OneToOneField(DocumentRegionAssociation, models.PROTECT)
    worker_version = models.PositiveIntegerField()
    reason = models.TextField(blank=True, default="")
    worker_revision = models.ForeignKey(
        WorkerIdentityRevision, models.PROTECT, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("IdentityResolution is immutable")
        return super().save(*args, **kwargs)


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
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.MEDIUM
    )
    state = models.CharField(
        max_length=16, choices=State.choices, default=State.PENDING
    )
    description = models.TextField(blank=True, default="")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.PROTECT, null=True, blank=True
    )
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
