# Explainer — `backend/agent/worker.py`

## Purpose
The LiveKit agent worker process. For each room (= each patient), it connects, resolves the
patient's language, creates the persisted `IntakeState`, builds the active pipeline's
`AgentSession` via the registry, wires the `IntakeAgent` (intake brain), starts the session
with Krisp BVC noise cancellation, and greets the patient with the consent ask.

## Dependencies & data in/out
- **Imports:** `livekit.agents` (`Agent`, `AgentServer`, `JobContext`, `RoomInputOptions`,
  `cli`); `config.settings`, `logging_setup`, `providers.registry.build_session`.
- **In:** a LiveKit job (room + participant). **Out:** a running voice session.

## Walkthrough
- **module top** — `configure_logging()`, create the `AgentServer` singleton `server`, define
  `SUPPORTED_LANGUAGES = {"en","hi"}` (Marathi deferred).
- **`_resolve_language(participant)`** — reads `participant.attributes["language"]` (set by the
  token API); falls back to `en` and logs if unsupported.
- **`entrypoint(ctx)`** (decorated `@server.rtc_session()`) — `await ctx.connect()`; wait for
  the participant; resolve language; create `IntakeState(session_id=room.name, ...)` and
  `persist_session()`; `build_session(active_pipeline, language)`; create `IntakeAgent(state,
  language)` and `bind_room(ctx.room)`; build `RoomInputOptions` with Krisp if available;
  attach a `SessionMeter` for per-turn telemetry, attach a `TranscriptRecorder` (when
  `PERSIST_TRANSCRIPT`), record a start time, and register a shutdown callback that flushes the
  meter and records `session_seconds` + LiveKit cost (`cost.livekit_cost`) on the session row;
  `session.start(agent, room, room_input_options)`. The agent greets via `IntakeAgent.on_enter`.
- **`__main__`** — `cli.run_app(server)` (verified signature accepts `AgentServer`).

## Gotchas / TODOs
- `MultilingualModel()` (inside `build_session`) needs the live job context — that's why the
  session is built inside the entrypoint, not at import time.
- Run `python -m livekit.agents download-files` once before first run (model files).
- Krisp BVC requires LiveKit Cloud; `build_session` degrades to no-NC otherwise.
- Phase D replaces `GreeterAgent` and wires telemetry to the session's metrics events.
