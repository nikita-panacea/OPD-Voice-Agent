"""The intake brain: an `Agent` subclass with the tools that drive a goal-driven OPD intake.

Tools the LLM calls:
  * record_consent  — the consent gate (no consent → no collection)
  * save_intake_field — store an answer (+ push a live update to the patient's UI panel)
  * confirm_field   — mark a critical field confirmed after read-back
  * flag_urgent     — raise the URGENT staff escalation on a red flag
  * complete_intake — finish the session

Prerecorded checklist prompts are played deterministically in code (not left to the LLM) so
each question is asked once, recorded in chat history, and the patient's reply is saved.
"""

from __future__ import annotations

import json

from livekit import rtc
from livekit.agents import Agent, RunContext, StopResponse, function_tool
from livekit.agents.llm import ChatContext, ChatMessage

from agent.prompts import (
    build_instructions,
    greeting_instructions,
    low_confidence_handoff,
    repeat_request,
)
from config.settings import get_settings
from intake import red_flags, report
from intake.questions import INTAKE_FIELDS, critical_field_ids, get_field
from intake.prompt_audio import PromptAudioResolver
from intake.state import IntakeState
from logging_setup import get_logger

log = get_logger("agent.intake")

DATA_TOPIC = "intake"


class IntakeAgent(Agent):
    """Goal-driven OPD intake agent for one session."""

    def __init__(self, state: IntakeState, language: str) -> None:
        super().__init__(instructions=build_instructions(language))
        self._state = state
        self._language = language
        self._room: rtc.Room | None = None
        settings = get_settings()
        self._min_asr_confidence = settings.min_asr_confidence
        self._asr_low_confidence_limit = settings.asr_low_confidence_limit
        self._low_conf_streak = 0
        self._prompt_audio = PromptAudioResolver()
        self._played_audio_keys: set[tuple[str, str]] = set()
        self._pending_field_id: str | None = None  # field we are waiting for an answer on

    def bind_room(self, room: rtc.Room) -> None:
        """Give the agent the room handle so it can push live UI updates (set by the worker)."""
        self._room = room

    async def on_enter(self) -> None:
        """Greet and play the consent prompt (or fall back to LiveKit TTS)."""
        log.info("agent_on_enter_greeting", session=self._state.session_id, language=self._language)
        if await self._play_field_prompt("consent"):
            raise StopResponse
        await self.session.generate_reply(instructions=greeting_instructions(self._language))
    async def _publish(self, payload: dict) -> None:
        if self._room is None:
            return
        try:
            await self._room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"), topic=DATA_TOPIC
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("publish_data_failed", error=str(exc))

    async def _record_spoken_prompt(self, text: str) -> None:
        """Record a browser-played prompt in chat history so the LLM knows what was asked."""
        if not text.strip():
            return
        new_ctx = self.chat_ctx.copy()
        new_ctx.add_message(role="assistant", content=text)
        await self.update_chat_ctx(new_ctx)

    def _next_field_to_ask(self) -> str | None:
        """Return the next checklist field id to ask, in order (skips consent gate)."""
        for field in INTAKE_FIELDS:
            if field.is_consent_gate:
                continue
            if field.id not in self._state.fields:
                return field.id
            if field.id in critical_field_ids():
                fv = self._state.fields[field.id]
                if not fv.confirmed:
                    return None
        return None

    async def _play_field_prompt(self, field_id: str, variant: str = "prompt") -> bool:
        """Play a prerecorded prompt once; set pending field. Returns True if audio was sent."""
        key = (field_id, variant)
        if key in self._played_audio_keys:
            return False

        prompt = self._prompt_audio.resolve(field_id, self._language, variant)
        if prompt is None:
            return False

        await self._publish(
            {
                "type": "prompt_audio",
                "field_id": prompt.field_id,
                "variant": prompt.variant,
                "url": prompt.url,
                "text": prompt.text,
            }
        )
        await self._record_spoken_prompt(prompt.text)
        self._played_audio_keys.add(key)
        self._pending_field_id = field_id
        log.info(
            "prompt_audio_published",
            session=self._state.session_id,
            field=field_id,
            variant=variant,
            url=prompt.url,
        )
        return True

    async def _advance_to_next_prompt(self) -> None:
        """Play the next checklist prompt and stop the LLM turn (wait for patient answer)."""
        next_id = self._next_field_to_ask()
        if next_id and await self._play_field_prompt(next_id):
            raise StopResponse

    def _low_confidence_decision(self, confidence: float | None) -> str | None:
        if confidence is None or not (0.0 < confidence < self._min_asr_confidence):
            self._low_conf_streak = 0
            return None
        self._low_conf_streak += 1
        if self._low_conf_streak >= self._asr_low_confidence_limit:
            return "handoff"
        return "repeat"

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        text = getattr(new_message, "text_content", None) or ""

        flag = red_flags.detect(text, self._language)
        if flag is not None:
            if not self._state.urgent_flag:
                self._state.raise_urgent(f"{flag.category}: {flag.term}")
                await self._publish({"type": "urgent", "reason": flag.category})
            try:
                await self.session.say(flag.advice)
            except Exception as exc:  # noqa: BLE001
                log.warning("escalation_say_failed", error=str(exc))
            raise StopResponse

        action = self._low_confidence_decision(getattr(new_message, "transcript_confidence", None))
        if action is None:
            return
        log.info(
            "asr_low_confidence",
            session=self._state.session_id,
            action=action,
            streak=self._low_conf_streak,
        )
        if action == "handoff":
            self._state.finalize("handoff")
            await self._publish({"type": "handoff", "reason": "repeated low ASR confidence"})
            message = low_confidence_handoff(self._language)
        else:
            message = repeat_request(self._language)
        try:
            await self.session.say(message)
        except Exception as exc:  # noqa: BLE001
            log.warning("asr_say_failed", error=str(exc))
        raise StopResponse

    @function_tool
    async def play_predefined_prompt(
        self, context: RunContext, field_id: str, variant: str = "prompt"
    ) -> str:
        """Play a checklist prompt clip (usually handled automatically — rarely needed)."""
        key = (field_id, variant)
        if key in self._played_audio_keys:
            pending = self._pending_field_id
            if pending == field_id:
                return (
                    f"Audio for '{field_id}' was already played and you are waiting for the "
                    f"patient's answer. Do NOT play it again. Call save_intake_field with "
                    f"field_id='{field_id}' and the patient's latest words as the value."
                )
            return (
                f"Audio for '{field_id}' ({variant}) was already played. Speak with your own "
                "voice for clarifications or read-backs — do not replay."
            )
        if await self._play_field_prompt(field_id, variant):
            raise StopResponse
        return f"No pre-recorded audio for {field_id} ({variant}). Ask with your LiveKit voice."

    @function_tool
    async def record_consent(self, context: RunContext, granted: bool) -> str:
        """Record whether the patient consents to the automated intake."""
        self._state.set_consent(granted)
        await self._publish({"type": "consent", "granted": granted})
        if not granted:
            self._pending_field_id = None
            return (
                "Consent declined. Do not collect any health information. Politely offer to "
                "connect the patient to hospital staff and end."
            )
        self._pending_field_id = None
        if await self._play_field_prompt("chief_complaint"):
            raise StopResponse
        return "Consent granted. Ask for chief_complaint with your voice."

    async def apply_field(self, field_id: str, value: str, confidence: float = 1.0) -> str:
        if get_field(field_id) is None:
            return f"Unknown field_id '{field_id}'. Use one of the checklist ids."
        if not self._state.consent_given:
            return "Consent has not been granted yet. Ask for consent first; do not save fields."

        self._state.save_field(field_id, value, confidence)
        await self._publish(self._state.field_panel_payload(field_id))
        if self._pending_field_id == field_id:
            self._pending_field_id = None

        if field_id in critical_field_ids():
            return (
                f"Saved {field_id}. This is a critical field — read it back to the patient "
                "with your voice and ask them to confirm, then call confirm_field. Do NOT "
                "replay prerecorded audio for this field."
            )
        return f"Saved {field_id}. Continue to the next field."

    @function_tool
    async def save_intake_field(
        self, context: RunContext, field_id: str, value: str, confidence: float = 1.0
    ) -> str:
        """Save one intake answer. Refuses until consent is granted."""
        msg = await self.apply_field(field_id, value, confidence)
        if field_id in critical_field_ids():
            return msg
        await self._advance_to_next_prompt()
        return msg

    @function_tool
    async def confirm_field(self, context: RunContext, field_id: str) -> str:
        """Mark a critical field as confirmed after the patient verifies the read-back."""
        self._state.confirm_field(field_id)
        await self._publish(self._state.field_panel_payload(field_id))
        await self._advance_to_next_prompt()
        return f"Confirmed {field_id}. Continue to the next field."

    @function_tool
    async def flag_urgent(self, context: RunContext, reason: str) -> str:
        self._state.raise_urgent(reason)
        await self._publish({"type": "urgent", "reason": reason})
        return (
            "URGENT flag raised for staff. Calmly tell the patient to alert hospital staff or "
            "seek immediate help right now."
        )

    @function_tool
    async def request_staff_handoff(self, context: RunContext, reason: str) -> str:
        self._state.finalize("handoff")
        await self._publish({"type": "handoff", "reason": reason})
        log.info("staff_handoff", session=self._state.session_id, reason=reason)
        return (
            "Tell the patient that a member of the hospital staff will help them shortly, "
            "thank them, and stop collecting information."
        )

    @function_tool
    async def complete_intake(self, context: RunContext) -> str:
        self._state.finalize("completed")
        self._pending_field_id = None
        try:
            report.generate_and_store(self._state.session_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("report_generation_failed", error=str(exc))
        await self._publish({"type": "complete", "completion_rate": self._state.completion_rate()})
        return (
            "Intake complete. Thank the patient and let them know the doctor will review the "
            "summary."
        )
