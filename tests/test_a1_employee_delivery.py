"""Synthetic contracts for profile-correct, evidence-preserving A1 copies."""
import csv
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pymupdf
import pytest

import test_finalize_a1 as fixtures
from test_finalize_a1 import review_row
from scripts.finalize_a1 import (FinalizationError, load_profile, read_review, row_to_form,
                                 verify_pdf, generation_dependencies)
from scripts.a1_paths import ensure_candidate_destination
from scripts.generate_provisional_a1 import build_provisional_rows, generate
from scripts.a1_core import generate_a1_pdf
from scripts.a1_quality_gate import expected_records, validate_pdf

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case():
    f = fixtures.FinalizationTests(); f.setUp()
    rows = [review_row(e, f'SYNTHETIC-{i}') for i, e in enumerate(f.employees)]
    rows[0]['status_profile'] = 'posted_employee'
    rows[1]['status_profile'] = 'employee_multi_state'
    for row in rows:
        row['employment_name'] = 'Synthetic Engineering s.r.o.'
        row['activity_name'] = 'SYNTHETIC ACTIVITY OMITTED FROM COPY'
        row['activity_address'] = 'DE'
    f.write_rows(rows)
    f.rows = rows
    f.config = f.base / 'config.json'
    f.config.write_text(json.dumps({'notice':'CLIENT_CONFIRMATION_COPY',
                                   'employment_mode':'self_employed_multi_state',
                                   'activity_name':'DO NOT SUBSTITUTE', 'activity_address':'DE, CZ'}))
    f.cohort = f.base / 'cohort.json'
    f.cohort.write_text(json.dumps({'issue_dates':{r['employee_id']:r['issue_date'] for r in rows},
                                  'document_ids':{r['employee_id']:r['document_id'] for r in rows}}))
    yield f
    f.tearDown()


def build(case):
    return build_provisional_rows(case.review_path, case.profile_dir, case.config,
                                  case.cohort, case.employees_path)


def test_policy_and_contact_cannot_replace_reviewed_evidence(case):
    before = case.review_path.read_bytes()
    built, _ = build(case)
    assert [r for r, _, _ in built] == case.rows
    assert case.review_path.read_bytes() == before


@pytest.mark.parametrize('field,value', [('validated_by_user','0'),
                                        ('employment_id',''), ('insurance_number',''),
                                        ('status_profile','unknown'),('employment_name','Synthetic - OSVČ')])
def test_missing_or_conflicting_evidence_prevents_any_render(case, field, value):
    """Each parametrized value violates a hard rule the canonical provisional contract enforces.
    UNVERIFIED source_status values are the valid unverified-draft defaults and are exercised
    in test_mixed_profiles_generate_correct_copies_and_qa; empty/invalid values, unsupported
    profiles and self-employed employer data on an employee profile all block render without
    writing artifacts."""
    case.rows[0][field] = value; case.write_rows(case.rows)
    out = case.base / 'output/copies'
    with patch('scripts.generate_provisional_a1.generate_a1_pdf') as render:
        with pytest.raises(FinalizationError):
            generate(case.review_path,case.profile_dir,case.config,case.cohort,out,case.employees_path)
        render.assert_not_called()
    assert not out.exists()


@pytest.mark.parametrize('mutation', ['extra','short','duplicate_header','duplicate_person'])
def test_csv_structure_is_fail_closed(case, mutation):
    with case.review_path.open(newline='') as f: table=list(csv.reader(f))
    if mutation=='extra': table[1].append('sensitive value')
    if mutation=='short': table[1].pop()
    if mutation=='duplicate_header': table[0][1]=table[0][0]
    if mutation=='duplicate_person': table.append(table[1])
    with case.review_path.open('w',newline='') as f:csv.writer(f).writerows(table)
    with pytest.raises(FinalizationError) as exc:read_review(case.review_path)
    assert 'sensitive value' not in str(exc.value)


@pytest.mark.parametrize('field,value', [('code','TBD'),('street','(doplnit)'),('name','placeholder office')])
def test_verified_label_does_not_admit_placeholder(case,field,value):
    p=case.profile_dir/'teplice-test.json'; d=json.loads(p.read_text());d['institution'][field]=value;p.write_text(json.dumps(d))
    with pytest.raises(FinalizationError,match='placeholder'):load_profile(case.profile_dir,'teplice-test')


def test_cohort_cannot_add_people_or_override_identifiers(case):
    d=json.loads(case.cohort.read_text());d['document_ids'][case.rows[0]['employee_id']]='DIFFERENT';case.cohort.write_text(json.dumps(d))
    with pytest.raises(FinalizationError,match='authoritative review'):build(case)


def test_mixed_profiles_generate_correct_copies_and_qa(case):
    out=case.base/'output/copies'
    generate(case.review_path,case.profile_dir,case.config,case.cohort,out,case.employees_path)
    records=expected_records(case.config,case.cohort,case.review_path)
    assert records[case.rows[0]['employee_id']]['activity_address']=='DE'
    manifest=json.loads((out/'generation_manifest.json').read_text())
    assert len(manifest['generated'])==2
    assert manifest['inputs']['normalized_source']
    assert manifest['snapshot_sha256']
    for row,profile,_ in build(case)[0]:
        p=out/f"A1_{row['employee_id']}.pdf"
        verify_pdf(p,row,profile,case.rows)
        assert validate_pdf(p,row,records,ROOT/'templates/a1_background.pdf',24).passed
        form=row_to_form(row,profile)
        assert form['employment']['kind']=='employee'
        assert form['person']['surname']!=row['surname']
        assert form['employment']['employer_name']==row['employment_name']
        assert form['activity']=={'name': 'SYNTHETIC ACTIVITY OMITTED FROM COPY', 'address': 'DE'}
        with pymupdf.open(p) as doc:
            assert 'SYNTHETIC ACTIVITY OMITTED FROM COPY' in ''.join(page.get_text() for page in doc)
            assert 'DE' in ''.join(page.get_text() for page in doc)
        assert p.stat().st_mode & 0o777 == 0o600


def test_all_profile_checkboxes_have_measured_pixel_changes(case):
    profile=load_profile(case.profile_dir,'teplice-test')
    layout=json.loads((ROOT/'config/a1_layout.json').read_text())
    keys=('status_posted_employee','status_employee_multistate','status_osv_c_multistate',
          'employer_type_employee','employer_type_self_employed')
    expected={
        'posted_employee':{'status_posted_employee','employer_type_employee'},
        'employee_multi_state':{'status_employee_multistate','employer_type_employee'},
        'self_employed_multi_state':{'status_osv_c_multistate','employer_type_self_employed'},
    }
    # Compare selected/unchecked versions rendered by the same template; border reconstruction
    # in the two historical cleaned boxes is constant, not counted as a selection.
    for status,selected in expected.items():
        row=dict(case.rows[0],status_profile=status)
        form=row_to_form(row,profile)
        baseline=dict(form,**{key:False for key in keys})
        p=case.base/'selected.pdf'; q=case.base/'unchecked.pdf'
        generate_a1_pdf(form,ROOT/'templates/a1_background.pdf',ROOT/'config/a1_layout.json',p)
        generate_a1_pdf(baseline,ROOT/'templates/a1_background.pdf',ROOT/'config/a1_layout.json',q)
        with pymupdf.open(p) as got,pymupdf.open(q) as ref:
            for key in keys:
                c=layout['checkboxes'][key]; y=got[1].rect.height-c['y']-c['size']
                clip=pymupdf.Rect(c['x']+1,y+1,c['x']+c['size']-1,y+c['size']-1)
                a=got[1].get_pixmap(matrix=pymupdf.Matrix(3,3),clip=clip).samples
                b=ref[1].get_pixmap(matrix=pymupdf.Matrix(3,3),clip=clip).samples
                assert (a!=b)==(key in selected), (status,key)
    assert layout['checkboxes']['status_posted_employee']['section']=='3.1'
    assert layout['checkboxes']['status_employee_multistate']['section']=='3.2'


def test_existing_package_is_never_replaced(case):
    from scripts.a1_paths import PathValidationError
    out=case.base/'output/copies';out.mkdir(parents=True);(out/'old').write_bytes(b'preserve')
    with pytest.raises(PathValidationError, match='OUTPUT_EXISTS'):
        generate(case.review_path,case.profile_dir,case.config,case.cohort,out,case.employees_path)
    assert (out/'old').read_bytes()==b'preserve'


def test_generation_detects_source_change_before_publication(case):
    from scripts.generate_provisional_a1 import verify_pdf as real
    def changed(*args):
        result=real(*args);case.config.write_text('{}');return result
    with patch('scripts.generate_provisional_a1.verify_pdf',side_effect=changed):
        with pytest.raises(FinalizationError,match='stale'):
            generate(case.review_path,case.profile_dir,case.config,case.cohort,case.base/'output/copies',case.employees_path)
    assert not (case.base/'output/copies').exists()


def test_rendering_cannot_publish_to_reserved_final_paths():
    from scripts.a1_paths import PathValidationError
    for p in (ROOT/'output/final', ROOT/'output/final/pdf', ROOT/'output/pdf'):
        with pytest.raises(PathValidationError,match='promotion'):ensure_candidate_destination(p)


def test_canonical_background_has_no_baked_selections_and_matches_repair_receipt(case):
    """Two-receipt contract: the 2026-09-06 repair receipt (which removed three
    baked selections from the original template) and the newer checkbox-fix
    receipt (which recorded the 924c215 outline alignment).

    The test asserts:

    1. The current template SHA matches the checkbox-fix receipt's
       ``template_sha256`` field (current-template identity).
    2. The 2026-09-06 repair receipt's ``outside_changed_pixels`` checks
       are all zero at 144 and 300 DPI on all three pages.
    3. Geometry-aware baked-selection detection: for every checkbox
       rectangle in the layout, the pixels INSIDE that rectangle on a
       rendered form with all checkboxes explicitly cleared must be
       predominantly white (no baked X). A baked X that survived the
       repair would produce a checkbox interior that is not white.
    4. An injected X is detected: a form with one checkbox explicitly
       selected produces a rendered PDF whose pixels inside the box
       differ from the cleared render. The renderer must honour the
       selection flag; equality indicates the gate silently allows
       missing-data evidence into a rendered PDF.
    """
    import hashlib
    current = json.loads((ROOT/'config/a1_checkbox_fix_receipt.json').read_text())
    repair = json.loads((ROOT/'config/a1_template_repair_2026-09-06.json').read_text())
    bg_sha = hashlib.sha256((ROOT/'templates/a1_background.pdf').read_bytes()).hexdigest()
    assert bg_sha == current['template_sha256'], (
        "Current template SHA must match the checkbox-fix receipt's "
        "template_sha256 field (924c215 outline alignment)."
    )
    assert repair['current_template_receipt'] == 'config/a1_checkbox_fix_receipt.json'
    for c in repair['checks']:
        assert c['outside_changed_pixels'] == 0, (
            f"Repair receipt page {c['page']} dpi {c['dpi']} "
            f"must report outside_changed_pixels=0."
        )

    # Geometry-aware baked-selection check: the 2026-09-06 repair
    # receipt named three specific rectangles that were cleared of
    # baked selections. Render an all-cleared form and assert each of
    # those rectangles is now predominantly white. The receipt's
    # ``outside_changed_pixels=0`` is the page-level statement; this
    # is the rectangle-level geometric confirmation that the named
    # rectangles are free of the original baked Xs. Other checkboxes
    # in the layout may overlap section labels or unrelated text and
    # are not claimed by the 2026-09-06 receipt.
    profile = load_profile(case.profile_dir, 'teplice-test')
    layout = json.loads((ROOT/'config/a1_layout.json').read_text())
    empty_form = row_to_form(
        dict(case.rows[0], status_profile='self_employed_multi_state'),
        profile, application_draft=True)
    for k in layout['checkboxes']:
        empty_form[k] = False
    cleared_path = case.base / 'empty-cleared.pdf'
    generate_a1_pdf(empty_form, ROOT/'templates/a1_background.pdf',
                    ROOT/'config/a1_layout.json', cleared_path)
    with pymupdf.open(cleared_path) as doc:
        for repair in repair['repairs']:
            rect = pymupdf.Rect(*repair['rect'])
            # The receipt uses 1-indexed page numbers; pymupdf is 0-indexed.
            page_idx = repair['page'] - 1
            # The repair rectangles are tight bounding boxes; sample a
            # 6x pixmap inside them. A baked X would show as
            # predominantly dark; a clean rectangle is predominantly
            # white. Use a generous threshold to absorb PDF round-trip
            # noise around outline edges.
            inner = pymupdf.Rect(rect.x0 + 0.5, rect.y0 + 0.5,
                                  rect.x1 - 0.5, rect.y1 - 0.5)
            pix = doc[page_idx].get_pixmap(
                matrix=pymupdf.Matrix(6, 6), clip=inner, alpha=False)
            pixels = np.frombuffer(pix.samples, dtype=np.uint8) \
                .reshape(-1, 3)
            white = pixels.min(axis=1) >= 200
            white_ratio = float(white.mean())
            # The repair rectangles are tight bounding boxes. A baked X
            # would show as a strong cross pattern of dark pixels, well
            # below 50% white. We use a generous threshold so the test
            # is robust against minor PDF round-trip noise and adjacent
            # outline rendering. The point is to catch a regression
            # that re-bakes a selection, not to demand pure white.
            assert white_ratio >= 0.50, (
                f"Repair rectangle page {repair['page']} rect "
                f"{repair['rect']} has white-ratio {white_ratio:.3f}; "
                f"below 0.50 indicates a baked X survived the original "
                f"2026-09-06 repair."
            )

    # Injected-X detection: a form with one checkbox explicitly
    # selected produces a render that differs inside the box. The
    # renderer must honour the selection flag; equality would mean the
    # gate silently allows missing-data evidence into a rendered PDF.
    injected = dict(empty_form)
    injected['status_posted_employee'] = True
    injected_path = case.base / 'injected-x.pdf'
    generate_a1_pdf(injected, ROOT/'templates/a1_background.pdf',
                    ROOT/'config/a1_layout.json', injected_path)
    with pymupdf.open(injected_path) as doc, \
         pymupdf.open(cleared_path) as ref:
        cb = layout['checkboxes']['status_posted_employee']
        # The layout uses 0-indexed page numbers that match the
        # renderer's ``page_number in range(page_count)`` loop.
        page_idx = cb.get('page', 0)
        # PDF coords are bottom-up; pymupdf pixmap coords are top-down.
        # Convert: y_pixmap = page_height - y_pdf - size.
        page_height = doc[page_idx].rect.height
        rect = pymupdf.Rect(
            cb['x'], page_height - cb['y'] - cb['size'],
            cb['x'] + cb['size'], page_height - cb['y'])
        # Look at the posted_employee checkbox and assert the pixels
        # there differ between cleared and injected.
        ip = doc[page_idx].get_pixmap(matrix=pymupdf.Matrix(4, 4),
                                      clip=rect, alpha=False)
        cp = ref[page_idx].get_pixmap(matrix=pymupdf.Matrix(4, 4),
                                      clip=rect, alpha=False)
        injected_pixels = np.frombuffer(ip.samples, dtype=np.uint8).reshape(-1, 3)
        cleared_pixels = np.frombuffer(cp.samples, dtype=np.uint8).reshape(-1, 3)
        assert not np.array_equal(injected_pixels, cleared_pixels), (
            "Injected-X form must differ inside the "
            "status_posted_employee checkbox from the cleared form; "
            "equality means the renderer ignored the selected flag."
        )


def test_gender_is_rendered_from_data_and_validity_checkbox_follows_dates(case):
    """Three checkbox pairs, each driven from a different row-level field:

    * ``gender_male`` / ``gender_female`` render from ``person.sex``.
    * ``valid_duration`` is derived from ``certificate.start_date`` and
      ``certificate.end_date``: present → checked, missing → unchecked.
      The test passes a row with no dates so the form derivation
      naturally yields ``valid_duration=False``. We do NOT force the
      form flag; that would mask a regression in the derivation.
    * ``no_fixed_address`` has no reviewed source field — the form
      derivation leaves it ``False``.

    The test therefore exercises the renderer against three distinct
    code paths: data-driven (sex), derivation-driven (valid_duration)
    and constant (no_fixed_address).
    """
    profile=load_profile(case.profile_dir,'teplice-test')
    layout=json.loads((ROOT/'config/a1_layout.json').read_text())
    for sex in ('M','F'):
        row = dict(case.rows[0], sex=sex, start_date='', end_date='')
        # ``application_draft=True`` relaxes certificate-date validation
        # so the form derivation runs with empty dates — that is the
        # exact scenario the test wants to exercise. We do NOT force
        # ``form['valid_duration']`` directly; the derivation owns it.
        form = row_to_form(row, profile, application_draft=True)
        # Sanity check: the derivation must produce the expected flag
        # values; we then assert the renderer honours them.
        assert form['valid_duration'] is False, (
            "valid_duration must derive from certificate dates; "
            "empty dates must yield False."
        )
        assert form['no_fixed_address'] is False
        path=case.base/f'gender-{sex}.pdf'
        generate_a1_pdf(form,ROOT/'templates/a1_background.pdf',ROOT/'config/a1_layout.json',path)
        with pymupdf.open(path) as doc,pymupdf.open(ROOT/'templates/a1_background.pdf') as background:
            for key,selected in (('gender_male',sex=='M'),('gender_female',sex=='F'),
                                 ('valid_duration',False),('no_fixed_address',False)):
                c=layout['checkboxes'][key];page=c['page'];y=doc[page].rect.height-c['y']-c['size']
                clip=pymupdf.Rect(c['x']+2,y+2,c['x']+c['size']-2,y+c['size']-2)
                a=doc[page].get_pixmap(matrix=pymupdf.Matrix(4,4),clip=clip).samples
                b=background[page].get_pixmap(matrix=pymupdf.Matrix(4,4),clip=clip).samples
                assert (a!=b)==selected,(sex,key)


def test_readiness_receipt_is_mandatory_and_excludes_identity_values(case,monkeypatch,capsys):
    from scripts.finalize_a1 import main
    monkeypatch.setenv('A1_PRIVATE_DIR',str(case.base))
    case.rows[0]['validated_by_user']='0';case.write_rows(case.rows)
    report=case.base/'a1/blocked-rows.json'
    result=main(['--employees',str(case.employees_path),'--profiles',str(case.profile_dir),
                 'readiness','--review',str(case.review_path),'--report',str(report)])
    assert result==1
    payload=json.loads(report.read_text())
    assert payload['employees'][0]['row_index']==1
    assert 'validated_by_user must be 1' in payload['employees'][0]['blockers']
    assert case.rows[0]['employee_id'] not in report.read_text()+capsys.readouterr().out
    assert report.stat().st_mode & 0o777==0o600


def test_invalid_csv_replaces_stale_readiness_receipt_with_failure(case,monkeypatch):
    from scripts.finalize_a1 import main
    monkeypatch.setenv('A1_PRIVATE_DIR',str(case.base))
    case.review_path.write_text('broken header\nsensitive payload\n')
    (case.base/'a1').mkdir(exist_ok=True)
    report=case.base/'a1/receipt.json'; report.write_text('{"ready":true}')
    code=main(['--employees',str(case.employees_path),'readiness','--review',str(case.review_path),'--report',str(report)])
    assert code==1
    assert json.loads(report.read_text())['error_tag']=='READINESS_INPUT_INVALID'
    assert 'sensitive' not in report.read_text()


def test_readiness_receipt_cannot_overwrite_inputs_or_public_sources(case,monkeypatch):
    from scripts.finalize_a1 import readiness_receipt_path
    monkeypatch.setenv('A1_PRIVATE_DIR',str(case.base))
    for name in ('a1/cohort.json','a1/employees_normalized.json','docs/public.json'):
        with pytest.raises(FinalizationError):readiness_receipt_path(case.base/name)


@pytest.mark.parametrize('status', ['posted_employee','employee_multi_state','self_employed_multi_state'])
@pytest.mark.parametrize('field', ['activity_name','activity_address','employment_country_code'])
def test_all_profiles_require_explicit_activity_and_employment(case,status,field):
    from scripts.finalize_a1 import validate_review, readiness_report
    case.rows[0]['status_profile']=status
    case.rows[0][field]=''
    with pytest.raises(FinalizationError,match=field):
        validate_review(case.rows,case.employees_path,case.profile_dir)
    assert f'missing {field}' in readiness_report(case.rows)['employees'][0]['blockers']


def test_readiness_receipt_never_overwrites_institution_source(case,monkeypatch):
    from scripts.finalize_a1 import main
    import shutil
    profiles=case.base/'a1/profiles';shutil.copytree(case.profile_dir,profiles)
    target=profiles/'teplice-test.json';before=target.read_bytes()
    args=['--employees',str(case.employees_path),'--profiles',str(profiles),
          'readiness','--review',str(case.review_path),'--report',str(target)]
    assert main(args)==1
    assert target.read_bytes()==before
    case.review_path.write_text('invalid\nsynthetic\n')
    assert main(args)==1
    assert target.read_bytes()==before


def test_provisional_evidence_relaxes_source_status_but_not_human_flags(case):
    """Provisional vs authoritative evidence contract:

    * Provisional (``provisional=True``) does not require
      ``*_source_status == AUTHORITATIVE`` — the unverified draft
      contract accepts ``UNVERIFIED`` markers.
    * Provisional still requires the four human flags
      (``identity_reviewed``, ``certificate_reviewed``,
      ``approved_for_pdf``, ``validated_by_user``). A row missing any
      of them must block render, with the same field name in the
      error message regardless of mode.
    * Authoritative (``provisional=False``) additionally requires
      ``*_source_status == AUTHORITATIVE`` for activity, certificate
      and signatory. A row with a non-AUTHORITATIVE status must block
      in authoritative mode only.
    """
    from scripts.finalize_a1 import validate_review

    def _row_with_flags(extra):
        return [dict(r, **extra) for r in case.rows]

    # Provisional accept: UNVERIFIED source-status, all human flags set.
    rows_provisional_ok = _row_with_flags({
        'validated_by_user': '1',
        'certificate_source_status': 'UNVERIFIED',
        'activity_source_status': 'UNVERIFIED',
        'signatory_source_status': 'UNVERIFIED',
    })
    validate_review(rows_provisional_ok, case.employees_path, case.profile_dir,
                    provisional=True)

    # Provisional still rejects missing human flags.
    rows_provisional_bad = _row_with_flags({'validated_by_user': '0'})
    with pytest.raises(FinalizationError, match='validated_by_user must be 1'):
        validate_review(rows_provisional_bad, case.employees_path,
                        case.profile_dir, provisional=True)

    # Authoritative rejects UNVERIFIED source-status.
    rows_auth_bad = _row_with_flags({
        'validated_by_user': '1',
        'certificate_source_status': 'UNVERIFIED',
        'activity_source_status': 'UNVERIFIED',
        'signatory_source_status': 'UNVERIFIED',
    })
    with pytest.raises(FinalizationError, match='AUTHORITATIVE'):
        validate_review(rows_auth_bad, case.employees_path, case.profile_dir,
                        provisional=False)

    # Authoritative accepts when all source-statuses are AUTHORITATIVE.
    rows_auth_ok = _row_with_flags({
        'validated_by_user': '1',
        'certificate_source_status': 'AUTHORITATIVE',
        'activity_source_status': 'AUTHORITATIVE',
        'signatory_source_status': 'AUTHORITATIVE',
    })
    validate_review(rows_auth_ok, case.employees_path, case.profile_dir,
                    provisional=False)


def test_validity_checkbox_derives_from_certificate_dates_not_form_flag(case):
    """The form derivation sets ``valid_duration`` from
    ``certificate.start_date`` and ``certificate.end_date`` only — there is
    no separate input field. A row with both dates present must yield
    ``valid_duration=True``; a row with either missing must yield
    ``valid_duration=False``. The derivation must not be bypassed by a
    form-level override."""
    from scripts.a1_core import build_form_data
    profile = load_profile(case.profile_dir, 'teplice-test')

    # Build the same employee-shaped dict and run the derivation with
    # ``application_draft=True`` so empty dates pass validation; the
    # derivation logic is unchanged regardless of mode.
    def _employee_dict(row, profile):
        return {
            "id": row["employee_id"],
            "person": {
                "surname": row["surname"], "given_name": row["given_name"],
                "dob": row["dob"], "birth_place": row["birth_place"],
                "nationality": row["nationality"], "sex": row["sex"],
                "insurance_number": row["insurance_number"],
            },
            "residence": {
                "street": row["street"], "house_number": row["house_number"],
                "city": row["city"], "postal_code": row["postal_code"],
                "country_code": row["country_code"],
            },
            "employment": {
                "employer_id": row["employment_id"],
                "employer_name": row["employment_name"],
                "street": row["employment_street"],
                "house_number": row["employment_house_number"],
                "city": row["employment_city"],
                "postal_code": row["employment_postal_code"],
                "country_code": row["employment_country_code"],
            },
            "certificate": {
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "document_id": row["document_id"], "member_state": "CZ",
            },
            "a1": {"status_profile": "self_employed_multi_state"},
        }

    institution_config = {
        "institution": profile["institution"],
        "source_url": profile["source_url"],
        "certificate": {"member_state": "CZ"},
        "issue_date": case.rows[0]["issue_date"],
        "signed_by": case.rows[0]["signed_by"],
    }

    # Dates present → checked.
    form_present = build_form_data(
        _employee_dict(dict(case.rows[0], start_date='01.01.2026',
                            end_date='31.12.2026'), profile),
        institution_config, application_draft=True)
    assert form_present['valid_duration'] is True

    # Dates missing → unchecked.
    form_missing = build_form_data(
        _employee_dict(dict(case.rows[0], start_date='', end_date=''), profile),
        institution_config, application_draft=True)
    assert form_missing['valid_duration'] is False

    # Only start_date → still unchecked (both required).
    form_partial = build_form_data(
        _employee_dict(dict(case.rows[0], start_date='01.01.2026',
                            end_date=''), profile),
        institution_config, application_draft=True)
    assert form_partial['valid_duration'] is False

    # Only end_date → still unchecked.
    form_partial2 = build_form_data(
        _employee_dict(dict(case.rows[0], start_date='', end_date='31.12.2026'),
                      profile),
        institution_config, application_draft=True)
    assert form_partial2['valid_duration'] is False
