"""Tests for prerecorded prompt playback guardrails (no replay loops)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.intake_agent import IntakeAgent
from intake.prompt_audio import ResolvedPromptAudio
from intake.state import IntakeState


def _agent() -> IntakeAgent:
    return IntakeAgent(IntakeState(session_id="prompt-test", language="en"), "en")


def _resolved(field_id: str = "chief_complaint") -> ResolvedPromptAudio:
    return ResolvedPromptAudio(
        field_id=field_id,
        variant="prompt",
        url=f"/audio/en/{field_id}.wav",
        text="What is the main issue that brought you in today?",
    )


@pytest.mark.asyncio
async def test_field_prompt_plays_once_and_sets_pending() -> None:
    agent = _agent()
    agent._publish = AsyncMock()
    agent._record_spoken_prompt = AsyncMock()

    with patch.object(agent._prompt_audio, "resolve", return_value=_resolved()):
        assert await agent._play_field_prompt("chief_complaint") is True
        assert await agent._play_field_prompt("chief_complaint") is False

    agent._publish.assert_called_once()
    agent._record_spoken_prompt.assert_called_once()
    assert agent._pending_field_id == "chief_complaint"
    assert ("chief_complaint", "prompt") in agent._played_audio_keys


@pytest.mark.asyncio
async def test_play_predefined_prompt_tool_refuses_replay_and_hints_save() -> None:
    agent = _agent()
    agent._played_audio_keys.add(("chief_complaint", "prompt"))
    agent._pending_field_id = "chief_complaint"

    result = await agent.play_predefined_prompt(MagicMock(), "chief_complaint", "prompt")

    assert "already played" in result.lower()
    assert "save_intake_field" in result.lower()


@pytest.mark.asyncio
async def test_save_clears_pending_for_that_field() -> None:
    agent = _agent()
    agent._state.consent_given = True
    agent._pending_field_id = "chief_complaint"
    agent._publish = AsyncMock()
    agent._state.save_field = MagicMock()
    agent._state.field_panel_payload = MagicMock(
        return_value={"type": "field_update", "id": "chief_complaint"}
    )

    msg = await agent.apply_field("chief_complaint", "shoulder pain", 0.9)

    assert agent._pending_field_id is None
    assert "Saved chief_complaint" in msg
    agent._state.save_field.assert_called_once_with("chief_complaint", "shoulder pain", 0.9)
