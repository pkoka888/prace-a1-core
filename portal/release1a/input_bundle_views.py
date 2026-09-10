"""Case-scoped BO publication and manifest-pinned private downloads."""
import io
import re
import zipfile

from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe
from .a1_exports import publish_input_cohort
from .document_intake import audit
from .identity import _authorize
from .input_bundle_access import read_input_bundle
from .models import A1Case
from .services import Forbidden, StaleWrite
from .views import require_org_membership


def _failure(request, case_id, exc, event):
    audit(request.user, request.organization, event, f'a1:{case_id}', outcome='denied')
    if isinstance(exc, Forbidden):
        return HttpResponseForbidden('ACCESS_DENIED')
    status = 404 if isinstance(exc, ObjectDoesNotExist) else 409
    return JsonResponse({'error': 'INPUT_BUNDLE_UNAVAILABLE_OR_STALE'}, status=status)


@never_cache
@require_http_methods(['GET', 'POST'])
@require_org_membership
def input_bundle_publish(request, pk):
    try:
        _authorize(request.user, request.organization, 'a1:prepare')
    except Forbidden as exc:
        return _failure(request, pk, exc, 'a1.input_bundle_publish')
    case = get_object_or_404(A1Case, pk=pk, organization=request.organization,
                             worker__organization=request.organization)
    bundle = None
    if request.method == 'POST':
        tokens = request.POST.getlist('expected_source_hash')
        if len(tokens) != 1:
            return JsonResponse({'error': 'INPUT_SOURCE_REFERENCE_REQUIRED'}, status=400)
        try:
            bundle = publish_input_cohort(request.user, request.organization,
                [{'case_id': case.pk, 'expected_source_hash': tokens[0]}])
        except (Forbidden, ObjectDoesNotExist, StaleWrite, ValueError, OSError) as exc:
            return _failure(request, pk, exc, 'a1.input_bundle_publish')
    response = render(request, 'portal/input_bundle.html', {'case': case, 'bundle': bundle, 'download_case': case.pk})
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@never_cache
@require_safe
@require_org_membership
def input_bundle_download(request, pk, manifest_hash):
    try:
        payloads = read_input_bundle(request.user, request.organization, pk, manifest_hash)
    except (Forbidden, ObjectDoesNotExist, StaleWrite, ValueError, OSError) as exc:
        return _failure(request, pk, exc, 'a1.input_bundle_read')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100600 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    response = HttpResponse(output.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="a1-input-{manifest_hash}.zip"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@never_cache
@require_http_methods(['GET', 'POST'])
@require_org_membership
def input_cohort_publish(request):
    """Explicit current-case selections; one atomic canonical publication per POST."""
    try:
        _authorize(request.user, request.organization, 'a1:prepare')
    except Forbidden as exc:
        return _failure(request, 'cohort', exc, 'a1.input_bundle_publish')
    bundle, selected_case = None, None
    if request.method == 'POST':
        raw = request.POST.getlist('selection')
        if not 1 <= len(raw) <= 50 or any(
                not re.fullmatch(r'[1-9][0-9]{0,18}:[0-9a-f]{64}', value) for value in raw):
            return JsonResponse({'error': 'INPUT_SELECTION_REQUIRED_OR_INVALID'}, status=400)
        selections = [{'case_id': int(value.split(':')[0]),
                       'expected_source_hash': value.split(':')[1]} for value in raw]
        if (len({item['case_id'] for item in selections}) != len(selections)
                or any(item['case_id'] > 9223372036854775807 for item in selections)):
            return JsonResponse({'error': 'INPUT_SELECTION_REQUIRED_OR_INVALID'}, status=400)
        try:
            bundle = publish_input_cohort(request.user, request.organization, selections)
        except (Forbidden, ObjectDoesNotExist, StaleWrite, ValueError, OSError) as exc:
            return _failure(request, 'cohort', exc, 'a1.input_bundle_publish')
        selected_case = selections[0]['case_id']
    cases = A1Case.objects.filter(organization=request.organization,
        worker__organization=request.organization, is_stale=False,
        source_snapshot_json__schema_version='a1-input-1').select_related('worker').order_by('-pk')
    response = render(request, 'portal/input_bundle.html', {
        'cohort_mode': True, 'page_obj': Paginator(cases, 50).get_page(request.GET.get('page')),
        'bundle': bundle, 'download_case': selected_case,
    })
    response['X-Content-Type-Options'] = 'nosniff'
    return response
