"""Tests for report building, schema validation, and Markdown rendering."""

import uuid

import pytest

from intake.report import (
    DISCLAIMER,
    IntakeReport,
    build_report,
    generate_and_store,
    load_stored,
    render_markdown,
)
from intake.state import IntakeState
from store.db import init_db


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def _seed_session() -> str:
    state = IntakeState(session_id=f"r-{uuid.uuid4().hex[:8]}", language="en")
    state.persist_session()
    state.set_consent(True)
    state.save_field("identity", "Asha, 45, female")
    state.save_field("chief_complaint", "bad chest pain since morning")
    state.save_field("severity", "8")
    state.save_field("medications", "metformin 500mg")
    state.confirm_field("medications")
    return state.session_id


def test_report_builds_and_validates() -> None:
    report = build_report(_seed_session())
    assert isinstance(report, IntakeReport)
    assert report.disclaimer == DISCLAIMER
    assert report.chief_complaint_patient_words == "bad chest pain since morning"
    assert "chest_pain" in report.red_flag_categories  # screened from chief complaint
    assert any(item.field_id == "severity" for item in report.hpi)
    assert report.medications == "metformin 500mg"


def test_markdown_has_disclaimer_and_quote() -> None:
    md = render_markdown(build_report(_seed_session()))
    assert DISCLAIMER in md
    assert "patient's own words" in md
    assert "## Chief complaint" in md
    # No diagnosis/treatment language leaks into the template.
    assert "diagnosis:" not in md.lower()


def test_generate_and_store_roundtrip() -> None:
    sid = _seed_session()
    _report, md = generate_and_store(sid)
    stored = load_stored(sid)
    assert stored is not None
    data, md2 = stored
    assert data["session_id"] == sid
    assert md2 == md


def test_unknown_session_raises() -> None:
    with pytest.raises(KeyError):
        build_report("does-not-exist")
