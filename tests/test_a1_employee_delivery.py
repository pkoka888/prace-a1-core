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


@pytest.mark.parametrize('field,value', [('validated_by_user','0'), ('certificate_source_status','UNVERIFIED'),
                                        ('employment_id',''), ('insurance_number',''),
                                        ('status_profile','unknown'),('employment_name','Synthetic - OSVČ')])
def test_missing_or_conflicting_evidence_prevents_any_render(case, field, value):
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


def test_canonical_background_has_no_baked_selections_and_matches_repair_receipt():
    import hashlib
    receipt=json.loads((ROOT/'config/a1_template_repair_2026-09-06.json').read_text())
    assert hashlib.sha256((ROOT/'templates/a1_background.pdf').read_bytes()).hexdigest()==receipt['output_sha256']
    assert all(c['outside_changed_pixels']==0 for c in receipt['checks'])
    with pymupdf.open(ROOT/'templates/a1_background.pdf') as doc:
        for n,rect in ((0,(456,382,462,387)),(0,(83,656,87,660)),(2,(79,421,83,425))):
            pix=doc[n].get_pixmap(matrix=pymupdf.Matrix(4,4),clip=pymupdf.Rect(rect))
            assert np.frombuffer(pix.samples,dtype=np.uint8).min()>150


def test_gender_is_rendered_from_data_and_no_fixed_address_is_unselected(case):
    profile=load_profile(case.profile_dir,'teplice-test')
    layout=json.loads((ROOT/'config/a1_layout.json').read_text())
    for sex in ('M','F'):
        row=dict(case.rows[0],sex=sex)
        form=row_to_form(row,profile)
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
