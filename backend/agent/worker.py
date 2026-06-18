"""LiveKit agent worker — the entrypoint that runs one intake session per job.

Uses the LiveKit Agents 1.6 `AgentServer` + `@server.rtc_session()` pattern (verified against
the installed package, 2026-06-14). For each room it:
  1. connects to the LiveKit Cloud room,
  2. reads the patient's chosen language from participant attributes,
  3. builds the active pipeline's `AgentSession` via the provider registry (STT/LLM/TTS + VAD +
     MultilingualModel turn detection),
  4. creates the `IntakeState` (persisted to SQLite) and the `IntakeAgent` (intake brain),
  5. starts the session with Krisp BVC noise cancellation on the input track,
  6. greets the patient and asks for consent.

Run (from `backend/`):
    python -m livekit.agents download-files   # one-time: fetch VAD + turn-detector models
    python -m agent.worker dev                # run the worker against LiveKit Cloud

Note: as of livekit-agents 1.5.10 `download-files` must be run against the `livekit.agents`
module (not the agent script), and it downloads files for all installed plugins.
"""

from __future__ import annotations

import time

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, RoomInputOptions, cli

from agent.intake_agent import IntakeAgent
from config.settings import ENV_FILE, get_settings
from intake import report
from intake.state import IntakeState
from intake.transcript import TranscriptRecorder
from logging_setup import configure_logging, get_logger
from providers.registry import build_session
from telemetry import cost, session_summary
from telemetry.meter import SessionMeter

# Load the project-root .env into os.environ. The LiveKit SDK (AgentServer reads LIVEKIT_URL/
# API_KEY/API_SECRET) and the provider plugins (OPENAI_API_KEY / SARVAM_API_KEY / DEEPGRAM_API_KEY
# / GOOGLE_API_KEY) read os.environ directly — pydantic-settings alone does not populate it.
load_dotenv(ENV_FILE)
configure_logging("agent")
log = get_logger("agent.worker")

server = AgentServer()

# Languages the POC supports live. Marathi uses a VAD endpointing fallback (the semantic
# turn detector has no Marathi); STT/TTS handle Marathi natively via Sarvam mr-IN.
SUPPORTED_LANGUAGES = {"en", "hi", "mr"}


def _resolve_language(participant) -> str:
    """Read the patient's chosen language from participant attributes; default to English."""
    attributes = getattr(participant, "attributes", None) or {}
    language = attributes.get("language", "en")
    if language not in SUPPORTED_LANGUAGES:
        log.warning("unsupported_language_fallback", requested=language, used="en")
        return "en"
    return language


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Run a single intake session for one LiveKit room."""
    await ctx.connect()
    settings = get_settings()

    log.info("agent_connected_waiting_for_participant", room=ctx.room.name)
    participant = await ctx.wait_for_participant()
    language = _resolve_language(participant)
    log.info(
        "session_starting",
        room=ctx.room.name,
        participant=participant.identity,
        language=language,
        pipeline=settings.active_pipeline,
    )

    # Live state, persisted to SQLite (keyed by room name).
    state = IntakeState(
        session_id=ctx.room.name, language=language, pipeline=settings.active_pipeline
    )
    state.persist_session()

    built = build_session(settings.active_pipeline, language)
    agent = IntakeAgent(state, language)
    agent.bind_room(ctx.room)

    room_input = (
        RoomInputOptions(noise_cancellation=built.noise_cancellation)
        if built.noise_cancellation is not None
        else RoomInputOptions()
    )

    # Per-turn telemetry: counts, per-component cost, end-to-end latency (no PHI).
    meter = SessionMeter(ctx.room.name, settings.active_pipeline, built.meters)
    meter.attach(built.session)

    # Full conversation transcript (PHI) — opt-out via PERSIST_TRANSCRIPT=false.
    if settings.persist_transcript:
        TranscriptRecorder(ctx.room.name).attach(built.session)

    # Measure session wall-clock for the LiveKit (per-minute) cost; finalize on shutdown.
    start_time = time.monotonic()

    async def _on_shutdown() -> None:
        meter.close()  # flush the final turn's telemetry first
        duration = time.monotonic() - start_time
        state.record_session_cost(duration, cost.livekit_cost(duration))
        # Always generate the clinician report at session end — don't rely on the LLM having
        # called complete_intake (it may not on disconnect/hangup).
        try:
            report.generate_and_store(ctx.room.name)
        except Exception as exc:  # noqa: BLE001 - best-effort at shutdown
            log.warning("report_generation_failed", error=str(exc))
        # Per-session cost/performance log file (+ transcript) for POC analysis.
        try:
            session_summary.write_session_files(ctx.room.name)
        except Exception as exc:  # noqa: BLE001 - best-effort at shutdown
            log.warning("session_summary_failed", error=str(exc))

    ctx.add_shutdown_callback(_on_shutdown)

    await built.session.start(agent=agent, room=ctx.room, room_input_options=room_input)
    # The agent greets + asks for consent via IntakeAgent.on_enter (fires on session start).
    log.info("session_started", room=ctx.room.name, language=language)


if __name__ == "__main__":
    cli.run_app(server)
