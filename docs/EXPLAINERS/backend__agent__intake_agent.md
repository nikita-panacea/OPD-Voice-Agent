# Explainer — `backend/agent/intake_agent.py`

## Purpose
The intake brain: an `Agent` subclass whose `@function_tool` methods the LLM calls to drive a
goal-driven OPD intake. Encodes the consent gate as code (not just prompt) and pushes live
updates to the patient's UI panel.

## Dependencies & data in/out
- **Imports:** `livekit` (`rtc`), `livekit.agents` (`Agent`, `RunContext`, `function_tool`),
  `agent.prompts.build_instructions`, `intake.questions`, `intake.state.IntakeState`, logger.
- **In:** tool calls from the LLM + the bound room. **Out:** state mutations + data messages.

## Walkthrough
- **`IntakeAgent.__init__(state, language)`** — sets instructions from `build_instructions`,
  stores the state + language; `_room` starts None.
- **`bind_room(room)`** — the worker injects the room so the agent can publish UI updates.
- **`_publish(payload)`** — best-effort JSON `publish_data` to the browser on topic `intake`
  (swallows errors; UI updates are non-critical).
- **`on_user_turn_completed(turn_ctx, new_message)`** — per-utterance guards before the LLM
  replies: (1) the deterministic **red-flag backstop** (raise URGENT + speak escalation +
  `StopResponse`); (2) the **ASR-confidence gate** — if the transcript looks misheard it asks
  the patient to repeat (or hands off after repeated failures), `StopResponse`-ing so garbled
  text is never processed/saved.
- **`_low_confidence_decision(confidence)`** — pure/stateful helper: returns `"repeat"`,
  `"handoff"`, or `None` from the transcript confidence vs `MIN_ASR_CONFIDENCE`, tracking a
  consecutive-low-confidence streak (`ASR_LOW_CONFIDENCE_LIMIT` → handoff). Confidence of
  None/0.0 = "provider didn't report it" → not gated (the prompt sense-check still applies).
  Unit-tested in `tests/test_asr_confidence.py`.
- **`record_consent(context, granted)`** — sets consent in state + UI; returns next-step
  guidance (or the decline path: collect nothing, offer staff).
- **`apply_field(field_id, value, confidence)`** — plain (non-tool) method holding the
  validate + **consent gate** + save + UI-push logic; returns the LLM-facing message. Split out
  so the gate is directly unit-testable (`tests/test_red_flags.py`).
- **`save_intake_field(context, ...)`** — thin `@function_tool` wrapper over `apply_field`.
- **`confirm_field(context, field_id)`** — marks a critical field confirmed + updates the UI.
- **`flag_urgent(context, reason)`** — LLM-initiated escalation (the deterministic hook is the
  backstop); raises the URGENT flag + UI banner.
- **`request_staff_handoff(context, reason)`** — graceful failure (§2.6): finalize as
  "handoff", notify UI, instruct the agent to stop collecting and hand to staff.
- **`complete_intake(context)`** — finalizes the session, generates + stores the report
  (best-effort), and sends a completion message.

## Gotchas / TODOs
- Tools are auto-collected by `Agent` because they're `@function_tool`-decorated methods;
  `apply_field`/`on_user_turn_completed`/`bind_room` are plain methods.
- `_publish` requires `bind_room`; without it (e.g. tests) updates are silently skipped.
- Red-flag escalation is enforced in code (the hook), not just the prompt.
