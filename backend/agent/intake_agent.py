"""The intake brain: an `Agent` subclass with the tools that drive a goal-driven OPD intake.

Tools the LLM calls:
  * record_consent  — the consent gate (no consent → no collection)
  * save_intake_field — store an answer (+ push a live update to the patient's UI panel)
  * confirm_field   — mark a critical field confirmed after read-back
  * flag_urgent     — raise the URGENT staff escalation on a red flag
  * complete_intake — finish the session

Guardrails (§2) live both in the prompt (`prompts.py`) and here as code: `save_intake_field`
refuses to store anything until consent is granted.
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
from intake.questions import critical_field_ids, get_field
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
        self._low_conf_streak = 0  # consecutive low-confidence (misheard) turns

    def bind_room(self, room: rtc.Room) -> None:
        """Give the agent the room handle so it can push live UI updates (set by the worker)."""
        self._room = room

    async def on_enter(self) -> None:
        """Speak first: greet the patient and ask for consent the moment the agent joins.

        Runs automatically when the agent becomes active in the session, so the patient hears
        the assistant before they say anything.
        """
        log.info("agent_on_enter_greeting", session=self._state.session_id, language=self._language)
        await self.session.generate_reply(instructions=greeting_instructions(self._language))

    async def _publish(self, payload: dict) -> None:
        """Send a JSON data message to the patient's browser (live field panel)."""
        if self._room is None:
            return
        try:
            await self._room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"), topic=DATA_TOPIC
            )
        except Exception as exc:  # noqa: BLE001 - UI update is best-effort
            log.warning("publish_data_failed", error=str(exc))

    def _low_confidence_decision(self, confidence: float | None) -> str | None:
        """Decide what to do about an STT transcript's confidence (updates the streak).

        Returns "handoff" after too many consecutive low-confidence turns, "repeat" for a single
        low-confidence turn, or None when the turn is trusted. A confidence of None or 0.0 means
        the provider didn't report it → treated as unknown (no gating; the prompt sense-check
        still applies). Pure + stateful → unit-testable.
        """
        if confidence is None or not (0.0 < confidence < self._min_asr_confidence):
            self._low_conf_streak = 0
            return None
        self._low_conf_streak += 1
        if self._low_conf_streak >= self._asr_low_confidence_limit:
            return "handoff"
        return "repeat"

    # ----------------------------------------------------- per-turn safety + ASR hook
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        """Per-utterance guards that run before the LLM replies.

        1. Red-flag screen (§2.2): on a hit, raise URGENT, notify the UI, speak the calm
           "alert staff" line, and `StopResponse` so the escalation isn't contradicted.
        2. ASR-confidence gate: if the transcript is low-confidence (likely misheard), ask the
           patient to repeat instead of acting on garbled speech; after repeated failures, hand
           off to staff. Both use `StopResponse` so the misheard text is never processed/saved.
        """
        text = getattr(new_message, "text_content", None) or ""

        flag = red_flags.detect(text, self._language)
        if flag is not None:
            if not self._state.urgent_flag:
                self._state.raise_urgent(f"{flag.category}: {flag.term}")
                await self._publish({"type": "urgent", "reason": flag.category})
            try:
                await self.session.say(flag.advice)
            except Exception as exc:  # noqa: BLE001 - speaking is best-effort
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
        except Exception as exc:  # noqa: BLE001 - speaking is best-effort
            log.warning("asr_say_failed", error=str(exc))
        raise StopResponse

    # ------------------------------------------------------------------ tools
    @function_tool
    async def record_consent(self, context: RunContext, granted: bool) -> str:
        """Record whether the patient consents to the automated intake.

        Args:
            granted: True if the patient agreed to continue, else False.
        """
        self._state.set_consent(granted)
        await self._publish({"type": "consent", "granted": granted})
        if granted:
            return "Consent granted. Begin collecting the chief complaint."
        return (
            "Consent declined. Do not collect any health information. Politely offer to connect "
            "the patient to hospital staff and end."
        )

    async def apply_field(self, field_id: str, value: str, confidence: float = 1.0) -> str:
        """Validate + consent-gate + save + push a field. Returns the LLM-facing message.

        Separated from the tool wrapper so the consent gate is directly unit-testable.
        """
        if get_field(field_id) is None:
            return f"Unknown field_id '{field_id}'. Use one of the checklist ids."
        if not self._state.consent_given:
            return "Consent has not been granted yet. Ask for consent first; do not save fields."

        self._state.save_field(field_id, value, confidence)
        await self._publish(self._state.field_panel_payload(field_id))

        if field_id in critical_field_ids():
            return (
                f"Saved {field_id}. This is a critical field — read it back to the patient and "
                "ask them to confirm, then call confirm_field."
            )
        return f"Saved {field_id}. Continue with the next needed field."

    @function_tool
    async def save_intake_field(
        self, context: RunContext, field_id: str, value: str, confidence: float = 1.0
    ) -> str:
        """Save one intake answer. Refuses until consent is granted (the consent gate).

        Args:
            field_id: the checklist field id (e.g. "chief_complaint").
            value: the patient's answer, in their own words.
            confidence: 0.0–1.0, how sure you are you understood correctly.
        """
        return await self.apply_field(field_id, value, confidence)

    @function_tool
    async def confirm_field(self, context: RunContext, field_id: str) -> str:
        """Mark a critical field as confirmed after the patient verifies the read-back."""
        self._state.confirm_field(field_id)
        await self._publish(self._state.field_panel_payload(field_id))
        return f"Confirmed {field_id}."

    @function_tool
    async def flag_urgent(self, context: RunContext, reason: str) -> str:
        """Raise an URGENT staff escalation for a red-flag symptom.

        Args:
            reason: short description of the red flag (e.g. "chest pain").
        """
        self._state.raise_urgent(reason)
        await self._publish({"type": "urgent", "reason": reason})
        return (
            "URGENT flag raised for staff. Calmly tell the patient to alert hospital staff or "
            "seek immediate help right now. Do not attempt to manage the emergency yourself."
        )

    @function_tool
    async def request_staff_handoff(self, context: RunContext, reason: str) -> str:
        """Hand off to hospital staff (graceful failure / patient request, §2.6).

        Use when the patient declines consent, asks for a human, or after repeated
        misunderstandings — do not keep guessing.

        Args:
            reason: short reason for the handoff (e.g. "repeated ASR failure").
        """
        self._state.finalize("handoff")
        await self._publish({"type": "handoff", "reason": reason})
        log.info("staff_handoff", session=self._state.session_id, reason=reason)
        return (
            "Tell the patient that a member of the hospital staff will help them shortly, "
            "thank them, and stop collecting information."
        )

    @function_tool
    async def complete_intake(self, context: RunContext) -> str:
        """Finish the intake once all required fields are captured."""
        self._state.finalize("completed")
        try:
            report.generate_and_store(self._state.session_id)
        except Exception as exc:  # noqa: BLE001 - report is best-effort at completion
            log.warning("report_generation_failed", error=str(exc))
        await self._publish({"type": "complete", "completion_rate": self._state.completion_rate()})
        return (
            "Intake complete. Thank the patient and let them know the doctor will review the "
            "summary."
        )
