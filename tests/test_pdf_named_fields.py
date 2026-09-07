"""Synthetic contracts for named placeholders and personal-name display casing."""
from io import BytesIO

import pymupdf
import pytest
from pypdf import PdfReader

from scripts.a1_core import FONT_CANDIDATES, render_overlay
from scripts.pdf_named_fields import (
    display_value,
    placeholder_template,
    replace_placeholders,
)


@pytest.fixture
def experiment():
    font = str(next(p for p in FONT_CANDIDATES if p.exists()))
    with pymupdf.open() as document:
        for _ in range(3):
            page = document.new_page(width=595.2, height=841.92)
            page.insert_text((40, 60), 'STATIC LABEL', fontsize=9)
            page.draw_rect((35, 40, 250, 120), color=(0, .4, 0))
        blank = document.tobytes()
    fields = [
        {'name': 'surname', 'source': 'person.surname', 'page': 0,
         'origin': [130, 60], 'size': 9, 'max_width': 150},
        *[{'name': 'certificate_id', 'source': 'certificate.document_id', 'page': page,
           'origin': [130, 95], 'size': 9, 'max_width': 150} for page in range(3)],
    ]
    return blank, fields, font


@pytest.mark.parametrize(('raw', 'expected'), [
    ('NOVÁKOVÁ', 'Nováková'), ('aLeNa', 'Alena'),
    ('ČERNÁ-NOVÁKOVÁ', 'Černá-Nováková'), ('  ANNA   MARIE  ', 'Anna Marie'),
    ('S\u030cIMA', 'Šima'), ('', ''), ('DE', 'De'),
])
def test_personal_names_are_display_cased(raw, expected):
    assert display_value('person.surname', raw) == expected
    assert display_value('person.given_name', raw) == expected
    assert display_value('person.maiden_name', raw) == expected


def test_codes_are_not_name_formatted():
    assert display_value('residence.country_code', 'CZ') == 'CZ'
    assert display_value('certificate.document_id', 'TEST-ABC') == 'TEST-ABC'


def test_replace_repeated_id_unicode_and_preserve_static_artwork(experiment):
    blank, fields, font = experiment
    template = placeholder_template(blank, fields, font)
    values = {'person.surname': 'NOVÁKOVÁ', 'certificate.document_id': 'SYNTHETIC-ID'}
    result = replace_placeholders(template, fields, values, font)
    assert values['person.surname'] == 'NOVÁKOVÁ'
    with pymupdf.open(stream=result, filetype='pdf') as document:
        assert len(document) == 3
        assert 'Nováková' in document[0].get_text()
        for page in document:
            assert 'STATIC LABEL' in page.get_text()
            assert page.get_text().count('SYNTHETIC-ID') == 1
            assert '{{' not in page.get_text()
            assert len(page.get_drawings()) == 1


def test_missing_value_fails(experiment):
    blank, fields, font = experiment
    with pytest.raises(ValueError, match='MISSING_FIELD_VALUE'):
        replace_placeholders(placeholder_template(blank, fields, font), fields, {}, font)


def test_missing_token_fails(experiment):
    blank, fields, font = experiment
    with pytest.raises(ValueError, match='PLACEHOLDER_CONTRACT_MISMATCH'):
        replace_placeholders(blank, fields, {'person.surname': 'Testová',
                                            'certificate.document_id': 'TEST'}, font)


def test_overlong_value_is_rejected_instead_of_clipped(experiment):
    blank, fields, font = experiment
    with pytest.raises(ValueError, match='FIELD_OVERFLOW'):
        replace_placeholders(placeholder_template(blank, fields, font), fields,
                             {'person.surname': 'A' * 1000, 'certificate.document_id': 'TEST'}, font)


def test_overlay_uses_same_name_rule():
    form = {'person': {'surname': 'NOVÁKOVÁ'}, 'residence': {}, 'employment': {}, 'institution': {}}
    layout = {'page_count': 3, 'fields': {'person.surname':
              {'page': 0, 'x': 130, 'y': 781.92, 'size': 9, 'max_width': 150}}, 'checkboxes': {}}
    text = PdfReader(BytesIO(render_overlay(form, layout).getvalue())).pages[0].extract_text()
    assert 'Nováková' in text
    assert 'NOVÁKOVÁ' not in text
    assert form['person']['surname'] == 'NOVÁKOVÁ'
