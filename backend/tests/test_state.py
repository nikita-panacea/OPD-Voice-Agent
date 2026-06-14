"""Tests for IntakeState: write-through persistence, completion, consent, urgent."""

import uuid

import pytest

from intake.state import IntakeState
from store.db import IntakeFieldRow, IntakeSession, init_db, session_scope


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def _new_state() -> IntakeState:
    state = IntakeState(session_id=f"test-{uuid.uuid4().hex[:8]}", language="en")
    state.persist_session()
    return state


def test_save_field_persists_to_db() -> None:
    state = _new_state()
    state.save_field("chief_complaint", "stomach pain for two days", confidence=0.9)

    with session_scope() as db:
        row = (
            db.query(IntakeFieldRow)
            .filter_by(session_id=state.session_id, field_id="chief_complaint")
            .one()
        )
        assert row.value == "stomach pain for two days"
        assert row.confidence == 0.9
        assert row.confirmed is False


def test_confirm_field_sets_flag_and_preserves_value() -> None:
    state = _new_state()
    state.save_field("medications", "metformin 500mg twice daily")
    state.confirm_field("medications")
    assert state.fields["medications"].confirmed is True
    # re-saving keeps the confirmed flag until value changes meaningfully
    with session_scope() as db:
        row = (
            db.query(IntakeFieldRow)
            .filter_by(session_id=state.session_id, field_id="medications")
            .one()
        )
        assert row.confirmed is True


def test_consent_persisted() -> None:
    state = _new_state()
    state.set_consent(True)
    with session_scope() as db:
        row = db.get(IntakeSession, state.session_id)
        assert row.consent_given is True


def test_raise_urgent_sets_flag() -> None:
    state = _new_state()
    state.raise_urgent("chest pain")
    assert state.urgent_flag is True
    with session_scope() as db:
        row = db.get(IntakeSession, state.session_id)
        assert row.urgent_flag is True
        assert row.urgent_reason == "chest pain"


def test_completion_rate_increases_with_required_fields() -> None:
    state = _new_state()
    assert state.completion_rate() == 0.0
    state.save_field("chief_complaint", "fever")
    assert 0.0 < state.completion_rate() < 1.0


def test_field_panel_payload_has_localized_label() -> None:
    state = _new_state()
    state.save_field("severity", "7")
    payload = state.field_panel_payload("severity")
    assert payload["type"] == "field_update"
    assert payload["id"] == "severity"
    assert payload["value"] == "7"
    assert "Severity" in str(payload["label"])
