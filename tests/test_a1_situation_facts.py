"""The Article 12 situation facts, and the optional review columns.

Decision D10 and D1b (2026-10-20): the model carries the facts that
condition a posting -- whether the worker replaces another posted person
(Article 12(1) of Regulation 883/2004) and when the self-employed began
pursuing the activity (Article 14(3) of Regulation 987/2009). They are
conditions of the legal claim, not fields on the form, so they are never
rendered; they are carried so the issuance gate can check them.

A missing fact blocks the A1 operation and nothing else. It is never
defaulted to a value that satisfies a check.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.finalize_a1 import (  # noqa: E402
    CSV_FIELDS,
    OPTIONAL_REVIEW_FIELDS,
    FinalizationError,
    _check_posting_conditions,
    read_review,
    review_fieldnames,
    write_review,
)


def _row(**overrides):
    """A row. The optional keys are absent unless asked for."""
    row = {
        "employee_id": "synthetic-1",
        "status_profile": "posted_employee",
        "start_date": "01.01.2026",
        "end_date": "31.12.2026",
    }
    row.update(overrides)
    return row


def _posting(**overrides):
    """A posting row that answers the replacement question."""
    return _row(replaces_worker="no", **overrides)


# --- the review contract -------------------------------------------------


def test_the_required_contract_is_unchanged():
    assert len(CSV_FIELDS) == 44
    assert CSV_FIELDS[0] == "employee_id"
    assert CSV_FIELDS[-1] == "comments"
    # The two situation facts are extensions, not part of the required set.
    for optional in OPTIONAL_REVIEW_FIELDS:
        assert optional not in CSV_FIELDS


def test_optional_columns_appear_only_when_the_rows_carry_them():
    without = review_fieldnames([_row()])
    assert without == list(CSV_FIELDS)
    with_facts = review_fieldnames([_row(replaces_worker="yes")])
    assert with_facts == list(CSV_FIELDS) + ["replaces_worker"]


def test_a_review_file_without_the_facts_still_reads(tmp_path):
    """The 44-column contract is not broken by the extension."""
    path = tmp_path / "review.csv"
    write_review(path, [_row()])
    header = path.read_text(encoding="utf-8-sig").splitlines()[0]
    assert len(header.split(",")) == 44
    rows = read_review(path)
    assert rows and rows[0]["employee_id"] == "synthetic-1"


def test_a_review_file_with_the_facts_reads_and_carries_them(tmp_path):
    path = tmp_path / "review.csv"
    write_review(path, [_row(replaces_worker="yes", prior_activity_start="01.11.2025")])
    header = path.read_text(encoding="utf-8-sig").splitlines()[0].split(",")
    assert header[-2:] == ["prior_activity_start", "replaces_worker"]
    rows = read_review(path)
    assert rows[0]["replaces_worker"] == "yes"
    assert rows[0]["prior_activity_start"] == "01.11.2025"


# --- the Article 12 conditions --------------------------------------------


def test_a_posting_without_the_replacement_answer_is_refused():
    with pytest.raises(FinalizationError, match="replaces_worker"):
        _check_posting_conditions("synthetic-1", _row())


def test_a_posting_with_an_unanswered_flag_is_refused():
    with pytest.raises(FinalizationError, match="replaces_worker"):
        _check_posting_conditions("synthetic-1", _row(replaces_worker="maybe"))


@pytest.mark.parametrize("answer", ["yes", "no", "YES", "No"])
def test_a_posting_with_the_replacement_answer_passes(answer):
    _check_posting_conditions("synthetic-1", _row(replaces_worker=answer))


def test_a_posting_longer_than_twenty_four_months_is_refused():
    with pytest.raises(FinalizationError, match="24 months"):
        _check_posting_conditions(
            "synthetic-1",
            _posting(start_date="01.01.2026", end_date="31.12.2028"),
        )


def test_a_posting_within_twenty_four_months_passes():
    _check_posting_conditions(
        "synthetic-1", _posting(start_date="01.01.2026", end_date="31.12.2027")
    )


def test_a_reversed_period_is_refused():
    with pytest.raises(FinalizationError, match="precedes"):
        _check_posting_conditions(
            "synthetic-1",
            _posting(start_date="01.01.2027", end_date="31.12.2026"),
        )


def test_a_non_posting_status_is_not_affected():
    """Only a posting asserts the Article 12 conditions."""
    _check_posting_conditions(
        "synthetic-1", _row(status_profile="self_employed_multi_state")
    )
    _check_posting_conditions(
        "synthetic-1", _row(status_profile="employee_multi_state")
    )


def test_a_posted_self_employed_person_needs_the_prior_activity_date():
    with pytest.raises(FinalizationError, match="prior_activity_start"):
        _check_posting_conditions(
            "synthetic-1", _posting(status_profile="posted_self_employed")
        )


def test_a_posted_self_employed_person_with_the_prior_activity_date_passes():
    _check_posting_conditions(
        "synthetic-1",
        _posting(
            status_profile="posted_self_employed", prior_activity_start="01.11.2025"
        ),
    )


def test_the_prior_activity_date_must_be_a_date():
    with pytest.raises(FinalizationError, match="DD.MM.YYYY"):
        _check_posting_conditions(
            "synthetic-1",
            _posting(
                status_profile="posted_self_employed", prior_activity_start="2025-11-01"
            ),
        )
