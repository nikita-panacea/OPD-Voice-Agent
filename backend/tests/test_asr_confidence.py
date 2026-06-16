"""Tests for the ASR low-confidence gate (mis-hearing protection)."""

from agent.intake_agent import IntakeAgent
from intake.state import IntakeState


def _agent() -> IntakeAgent:
    # Defaults: min_asr_confidence=0.5, asr_low_confidence_limit=3.
    return IntakeAgent(IntakeState(session_id="asr-test", language="en"), "en")


def test_high_confidence_is_trusted() -> None:
    agent = _agent()
    assert agent._low_confidence_decision(0.95) is None
    assert agent._low_conf_streak == 0


def test_none_or_zero_confidence_is_unknown_not_gated() -> None:
    agent = _agent()
    assert agent._low_confidence_decision(None) is None  # provider didn't report it
    assert agent._low_confidence_decision(0.0) is None  # 0 treated as unknown, not "very low"
    assert agent._low_conf_streak == 0


def test_low_confidence_asks_to_repeat_then_hands_off() -> None:
    agent = _agent()
    assert agent._low_confidence_decision(0.2) == "repeat"  # streak 1
    assert agent._low_confidence_decision(0.3) == "repeat"  # streak 2
    assert agent._low_confidence_decision(0.1) == "handoff"  # streak 3 -> limit


def test_streak_resets_on_a_good_turn() -> None:
    agent = _agent()
    assert agent._low_confidence_decision(0.2) == "repeat"
    assert agent._low_confidence_decision(0.2) == "repeat"
    assert agent._low_confidence_decision(0.9) is None  # good turn clears the streak
    assert agent._low_conf_streak == 0
    assert agent._low_confidence_decision(0.2) == "repeat"  # counts from 1 again
