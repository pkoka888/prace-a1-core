"""BO editing of pending assignment facts through the canonical versioned service."""

from copy import deepcopy
from django import forms
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from scripts.a1_core import A1_STATUS_LABELS, A1_STATUS_PROFILES

from .a1_exports import update_assignment_facts
from .identity import _authorize
from .models import Assignment
from .services import Forbidden, StaleWrite
from .views import require_org_membership

# Issuance dates, identifiers and signatories remain outside this pending-facts form.
FIELDS = {
    "employment": {
        "employer_id": "IČO / identifikátor zaměstnavatele nebo OSVČ",
        "employer_name": "Název zaměstnavatele nebo OSVČ",
        "street": "Ulice pracoviště",
        "house_number": "Číslo domu pracoviště",
        "city": "Obec pracoviště",
        "postal_code": "PSČ pracoviště",
        "country_code": "Kód země pracoviště",
    },
    "activity": {"name": "Činnost (5.1)", "address": "Země výkonu činnosti (5.2)"},
    "institution": {
        "resolved_ossz": "Příslušná OSSZ",
        "profile_key": "Profil instituce",
    },
}


def profile_choices(current):
    import json
    import os
    import re
    import stat
    from pathlib import Path
    from django.conf import settings
    from scripts.finalize_a1 import validate_profile

    root = Path(
        getattr(
            settings, "A1_DRAFT_PROFILE_ROOT", settings.BASE_DIR / "config/institutions"
        )
    )
    choices = [("", "Zatím neurčeno")]
    if root.is_absolute() and not any(p.is_symlink() for p in (root, *root.parents)):
        try:
            paths = sorted(root.glob("*.json"))
        except OSError:
            paths = []
        for path in paths:
            if not re.fullmatch("[a-z0-9-]+", path.stem):
                continue
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                with os.fdopen(fd, "rb") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        continue
                    data = json.loads(stream.read())
                if not isinstance(data, dict) or not isinstance(
                    data.get("institution"), dict
                ):
                    continue
                if not isinstance(data.get("verified_on"), str) or not isinstance(
                    data["institution"].get("name"), str
                ):
                    continue
                validate_profile(data, path.stem, provisional=True)
                choices.append((path.stem, data["institution"]["name"]))
            except (OSError, ValueError, KeyError, TypeError):
                continue
    if current and current not in {key for key, _ in choices}:
        choices.append((current, "Uložený profil není nyní dostupný"))
    return choices


class AssignmentFactsForm(forms.Form):
    version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    status_profile = forms.ChoiceField(
        required=False,
        label="Druh situace",
        choices=[
            ("", "Zatím neurčeno"),
            *(
                (profile, A1_STATUS_LABELS[profile])
                for profile in A1_STATUS_PROFILES
            ),
        ],
    )

    def __init__(self, *args, assignment, **kwargs):
        facts = assignment.a1_facts_json
        initial = {
            "version": assignment.version,
            "status_profile": facts.get("status_profile", ""),
        }
        initial.update(
            {
                f"{group}__{field}": facts.get(group, {}).get(field, "")
                for group, fields in FIELDS.items()
                for field in fields
            }
        )
        super().__init__(*args, initial=initial, **kwargs)
        for group, fields in FIELDS.items():
            for field, label in fields.items():
                self.fields[f"{group}__{field}"] = forms.CharField(
                    required=False, max_length=240, label=label
                )
        self.fields["institution__profile_key"] = forms.ChoiceField(
            required=False,
            label="Profil instituce",
            choices=profile_choices(initial["institution__profile_key"]),
        )

    def facts(self, current):
        facts = deepcopy(current)
        if self.cleaned_data["status_profile"]:
            facts["status_profile"] = self.cleaned_data["status_profile"]
        else:
            facts.pop("status_profile", None)
        for group, fields in FIELDS.items():
            block = facts.setdefault(group, {})
            for field in fields:
                value = self.cleaned_data[f"{group}__{field}"]
                if value:
                    block[field] = value
                else:
                    block.pop(field, None)
            if not block:
                facts.pop(group, None)
        return facts


@never_cache
@require_http_methods(["GET", "POST"])
@require_org_membership
def assignment_facts_edit(request, worker_pk, pk):
    try:
        _authorize(request.user, request.organization, "assignment:update")
    except Forbidden:
        return HttpResponseForbidden("ACCESS_DENIED")
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        organization=request.organization,
        worker_id=worker_pk,
        worker__organization=request.organization,
    )
    form = AssignmentFactsForm(
        request.POST if request.method == "POST" else None, assignment=assignment
    )
    status = 200
    if request.method == "POST":
        if any(len(request.POST.getlist(name)) != 1 for name in form.fields):
            return JsonResponse({"error": "COMPLETE_FACTS_FORM_REQUIRED"}, status=400)
        if form.is_valid():
            try:
                update_assignment_facts(
                    request.user,
                    request.organization,
                    assignment.pk,
                    form.facts(assignment.a1_facts_json),
                    expected_version=form.cleaned_data["version"],
                )
                return redirect("assignment_facts_edit", worker_pk=worker_pk, pk=pk)
            except StaleWrite:
                status = 409
                form.add_error(
                    None, "Podklady se změnily. Obnovte formulář před dalším uložením."
                )
            except (ValueError, OSError):
                form.add_error(
                    None, "Podklady nelze uložit. Zkontrolujte zadané hodnoty."
                )
    response = render(
        request,
        "portal/assignment_facts.html",
        {"form": form, "assignment": assignment},
    )
    response.status_code = status
    response["X-Content-Type-Options"] = "nosniff"
    return response
