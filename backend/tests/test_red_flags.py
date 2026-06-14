"""Tests for the safety layer: deterministic red-flag detection + the consent gate."""

import uuid

import pytest

from agent.intake_agent import IntakeAgent
from intake.red_flags import detect
from intake.state import IntakeState
from store.db import init_db


# --------------------------------------------------------------------- red flags
def test_chest_pain_english() -> None:
    flag = detect("I have really bad chest pain right now")
    assert flag is not None and flag.category == "chest_pain"


def test_breathing_english() -> None:
    flag = detect("I can't breathe properly")
    assert flag is not None and flag.category == "breathing"


def test_self_harm_english() -> None:
    flag = detect("sometimes I want to kill myself")
    assert flag is not None and flag.category == "self_harm"


def test_chest_pain_hindi() -> None:
    flag = detect("मेरे सीने में दर्द है", "hi")
    assert flag is not None and flag.category == "chest_pain"


def test_faint_hindi() -> None:
    flag = detect("वह अचानक बेहोश हो गया", "hi")
    assert flag is not None and flag.category == "loss_of_consciousness"


def test_codemix_breathing() -> None:
    flag = detect("doctor mujhe saans nahi aa rahi")
    assert flag is not None and flag.category == "breathing"


def test_no_false_positive_on_mild_symptom() -> None:
    assert detect("I have a mild cough and a runny nose") is None


def test_advice_is_localized_to_hindi() -> None:
    flag = detect("सीने में दर्द", "hi")
    assert flag is not None and "स्टाफ़" in flag.advice


# ------------------------------------------------------------------ consent gate
@pytest.mark.asyncio
async def test_consent_gate_blocks_saving_before_consent() -> None:
    state = IntakeState(session_id=f"t-{uuid.uuid4().hex[:8]}", language="en")
    agent = IntakeAgent(state, "en")
    msg = await agent.apply_field("chief_complaint", "fever", 1.0)
    assert "consent" in msg.lower()
    assert "chief_complaint" not in state.fields  # nothing saved


@pytest.mark.asyncio
async def test_consent_gate_allows_saving_after_consent() -> None:
    init_db()
    state = IntakeState(session_id=f"t-{uuid.uuid4().hex[:8]}", language="en")
    state.persist_session()
    state.set_consent(True)
    agent = IntakeAgent(state, "en")
    msg = await agent.apply_field("chief_complaint", "fever for two days", 0.95)
    assert "saved" in msg.lower()
    assert state.fields["chief_complaint"].value == "fever for two days"
