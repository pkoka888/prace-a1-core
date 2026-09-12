"""Forms for Release 1A M2 vertical slice — J1–J4 journeys."""
from __future__ import annotations

import datetime
import os

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Worker, Document, Assignment
from .services import MAX_UPLOAD_BYTES


class WorkerForm(forms.ModelForm):
    """J1: Worker create/edit form — Czech-first, HTMX-friendly."""

    class Meta:
        model = Worker
        fields = [
            "given_name",
            "family_name",
            "birth_date",
            "activity_profile",
            "state",
        ]
        widgets = {
            "given_name": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": _("Křestní jméno"),
            }),
            "family_name": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": _("Příjmení"),
            }),
            "birth_date": forms.DateInput(attrs={
                "class": "input-field",
                "type": "date",
            }, format="%Y-%m-%d"),
            "activity_profile": forms.Select(attrs={
                "class": "select-field",
            }),
            "state": forms.Select(attrs={
                "class": "select-field",
            }),
        }
        labels = {
            "given_name": _("Křestní jméno"),
            "family_name": _("Příjmení"),
            "birth_date": _("Datum narození"),
            "activity_profile": _("Profil činnosti"),
            "state": _("Stav"),
        }
        help_texts = {
            "activity_profile": _("employee = zaměstnanec, self_employed = OSVČ"),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Czech date format for birth_date
        self.fields["birth_date"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]
        if self.instance and self.instance.pk:
            self.fields["birth_date"].initial = self.instance.birth_date

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get("birth_date")
        if birth_date:
            today = datetime.date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            if age < 15 or age > 100:
                raise ValidationError(_("Věk musí být mezi 15 a 100 lety."))
        return birth_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.organization:
            instance.organization = self.organization
        if commit:
            instance.save()
        return instance


class DocumentUploadForm(forms.ModelForm):
    """J2: Document upload form — file validation, quarantine flow."""

    file = forms.FileField(
        label=_("Soubor"),
        widget=forms.ClearableFileInput(attrs={
            "class": "file-input",
            "accept": ".pdf,.png,.jpg,.jpeg,.tif,.tiff",
        }),
        help_text=_("Povolené formáty: PDF, PNG, JPG. Maximální velikost: %(size)s MB.") % {"size": MAX_UPLOAD_BYTES // (1024 * 1024)}
    )

    class Meta:
        model = Document
        fields = []

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.worker = kwargs.pop("worker", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            # Size check — must match services.MAX_UPLOAD_BYTES so the form and
            # the service reject at the same boundary.
            if file.size > MAX_UPLOAD_BYTES:
                raise ValidationError(
                    _("Soubor je příliš velký (max %(size)s MB).") % {"size": MAX_UPLOAD_BYTES // (1024 * 1024)}
                )

            # Content-Type check
            allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
            if file.content_type not in allowed_types:
                raise ValidationError(_("Nepovolený typ souboru. Povoleno: PDF, PNG, JPG, TIFF."))

            # Filename safety (defense in depth; the service also validates)
            filename = os.path.basename(file.name)
            if ".." in filename or filename.startswith("/") or "\\" in filename:
                raise ValidationError(_("Neplatný název souboru."))

        return file

    # NOTE: Document creation happens in services.upload_document (the single
    # authoritative path). This form only validates the upload; no save() override
    # is needed and the ModelForm default is intentionally never called.


class OcrConfirmationForm(forms.Form):
    """J2: OCR proposal confirmation — field-by-field review."""

    def __init__(self, *args, proposals=None, **kwargs):
        super().__init__(*args, **kwargs)
        if proposals:
            for proposal in proposals:
                field_name = f"confirm_{proposal.field_name}_{proposal.pk}"
                self.fields[field_name] = forms.BooleanField(
                    label=f"{proposal.field_name}: {proposal.proposed_value}",
                    required=False,
                    widget=forms.CheckboxInput(attrs={
                        "class": "checkbox-field",
                    }),
                )
                # Hidden field for the proposal value
                self.fields[f"value_{proposal.field_name}_{proposal.pk}"] = forms.CharField(
                    initial=proposal.proposed_value,
                    widget=forms.HiddenInput(),
                )


class AssignmentForm(forms.ModelForm):
    """J3: Assignment create/edit — overlap warning, A1 ambiguity check.

    Overlapping assignments are ALLOWED with a warning (DEC-005); only A1
    preparation is blocked when periods are ambiguous. The hidden ``version``
    field enables optimistic locking against stale concurrent edits.
    """

    # Hidden optimistic-lock field (not in Meta.fields so ModelForm ignores it
    # for model binding, but the value round-trips through clean())
    version = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Assignment
        fields = [
            "workplace_label",
            "activity_label",
            "start",
            "end",
            "state",
        ]
        widgets = {
            "workplace_label": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": _("Název pracoviště"),
            }),
            "activity_label": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": _("Popis činnosti"),
            }),
            "start": forms.DateInput(attrs={
                "class": "input-field",
                "type": "date",
            }, format="%Y-%m-%d"),
            "end": forms.DateInput(attrs={
                "class": "input-field",
                "type": "date",
            }, format="%Y-%m-%d"),
            "state": forms.Select(attrs={
                "class": "select-field",
            }),
        }
        labels = {
            "workplace_label": _("Pracoviště"),
            "activity_label": _("Činnost"),
            "start": _("Začátek"),
            "end": _("Konec"),
            "state": _("Stav"),
        }

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.worker = kwargs.pop("worker", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["start"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]
        self.fields["end"].input_formats = ["%Y-%m-%d", "%d.%m.%Y"]

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")

        if start and end:
            if start > end:
                raise ValidationError(_("Datum začátku nemůže být po datu konce."))

            # Detect overlap (excluding self if editing). Per DEC-005 this is a
            # WARNING, not an error: the assignment is still saved and the
            # template displays the warning. Only A1 preparation blocks later.
            if self.worker:
                from django.db.models import Q
                overlaps = Assignment.objects.filter(
                    worker=self.worker
                ).filter(
                    Q(start__lte=end) & Q(end__gte=start)
                )
                if self.instance.pk:
                    overlaps = overlaps.exclude(pk=self.instance.pk)
                self.overlap_warning = overlaps.exists()
            else:
                self.overlap_warning = False

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.organization:
            instance.organization = self.organization
        if self.worker:
            instance.worker = self.worker
        if commit:
            instance.save()
        return instance


class A1PrepareForm(forms.Form):
    """J4: A1 preparation trigger — readiness check, snapshot, generation."""

    confirm_prepare = forms.BooleanField(
        label=_("Potvrzuji připravenost k vygenerování A1 předlohy"),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "checkbox-field"}),
    )
    notes = forms.CharField(
        label=_("Poznámky"),
        required=False,
        widget=forms.Textarea(attrs={
            "class": "textarea-field",
            "rows": 3,
            "placeholder": _("Volitelné poznámky pro operátora..."),
        }),
    )


class A1ApprovalForm(forms.Form):
    """J4: A1 approval/denial — manual external status distinction."""

    DECISION_CHOICES = [
        ("approve", _("Schválit pro předání OSSZ")),
        ("deny", _("Zamítnout — vyžaduje opravu")),
    ]

    decision = forms.ChoiceField(
        label=_("Rozhodnutí"),
        choices=DECISION_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "radio-field"}),
    )
    external_status = forms.ChoiceField(
        label=_("Externí stav (manuální)"),
        choices=[
            ("not_submitted", _("Nepředáno")),
            ("submitted", _("Předáno OSSZ")),
            ("issued", _("Vydáno certifikát")),
            ("rejected", _("Zamítnuto OSSZ")),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "select-field"}),
        help_text=_("Pouze pro evidenci — neovlivňuje generování PDF."),
    )
    notes = forms.CharField(
        label=_("Poznámky k rozhodnutí"),
        required=False,
        widget=forms.Textarea(attrs={
            "class": "textarea-field",
            "rows": 3,
        }),
    )


class IntakeWizardForm(forms.Form):
    """Unified intake wizard - choose upload, paste, or manual entry."""

    INTAKE_CHOICES = [
        ("upload", _("Nahrát doklady (OP/ZP)")),
        ("paste", _("Vložit text")),
        ("manual", _("Vyplnit ručně")),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.pop("organization", None)
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    intake_type = forms.ChoiceField(
        label=_("Způsob přidání pracovníka"),
        choices=INTAKE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "radio-field"}),
    )
    purpose = forms.ChoiceField(
        label=_("Účel intake"),
        choices=[
            ("a1", _("Příprava A1")),
            ("assignment", _("Přiřazení")),
            ("payroll", _("Mzdové podklady")),
        ],
        widget=forms.Select(attrs={"class": "select-field"}),
    )


class MultiDocumentUploadForm(forms.Form):
    """Multi-document upload for OP/ZP intake - up to 4 sides, 10MB each."""

    file1 = forms.FileField(
        label=_("První soubor"),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "file-input",
            "accept": ".pdf,.png,.jpg,.jpeg,.tif,.tiff",
        }),
    )
    file2 = forms.FileField(
        label=_("Druhý soubor"),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "file-input",
            "accept": ".pdf,.png,.jpg,.jpeg,.tif,.tiff",
        }),
    )
    file3 = forms.FileField(
        label=_("Třetí soubor"),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "file-input",
            "accept": ".pdf,.png,.jpg,.jpeg,.tif,.tiff",
        }),
    )
    file4 = forms.FileField(
        label=_("Čtvrtý soubor"),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "class": "file-input",
            "accept": ".pdf,.png,.jpg,.jpeg,.tif,.tiff",
        }),
    )

    def __init__(self, *args, **kwargs):
        self.organization = kwargs.pop("organization", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        files = [cleaned_data.get(f"file{i}") for i in range(1, 5)]
        provided = [f for f in files if f]
        if not provided:
            raise ValidationError(_("Nahrajte alespoň jeden soubor."))
        for f in provided:
            if f.size > MAX_UPLOAD_BYTES:
                raise ValidationError(
                    _("Soubor %(name)s je příliš velký (max %(size)s MB).") %
                    {"name": f.name, "size": MAX_UPLOAD_BYTES // (1024 * 1024)}
                )
            if f.content_type not in ["application/pdf", "image/png", "image/jpeg", "image/tiff"]:
                raise ValidationError(_("Nepovolený typ souboru %(name)s. Povoleno: PDF, PNG, JPG, TIFF.") % {"name": f.name})
        return cleaned_data
