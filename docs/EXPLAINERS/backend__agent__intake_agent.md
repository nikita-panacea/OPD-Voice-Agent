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
- **`on_user_turn_completed(turn_ctx, new_message)`** — the deterministic red-flag backstop:
  runs `red_flags.detect` on the patient's text; on a hit it raises the URGENT flag, notifies
  the UI, speaks the calm escalation via `session.say`, and `raise StopResponse` to suppress
  the normal LLM reply for that turn. Independent of the LLM (§2.2).
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
