"""Provider registry + session factory (CLAUDE.md §6).

Maps provider names → builder objects and assembles an `AgentSession` from a named pipeline:
STT/LLM/TTS components + Silero VAD + MultilingualModel turn detection + Krisp BVC noise
cancellation. Switching pipelines/providers is a config change (pipelines.yaml), not a code
change.

All comparison providers are registered: STT (Sarvam, Deepgram, Whisper/OpenAI), LLM (OpenAI,
Google/Gemini), TTS (Sarvam, ElevenLabs). A pipeline naming an unregistered provider fails fast
with a clear error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.settings import get_pipeline
from logging_setup import get_logger
from providers import (
    llm_gemini,
    llm_openai,
    stt_deepgram,
    stt_sarvam,
    stt_whisper,
    tts_elevenlabs,
    tts_sarvam,
)
from providers.base import LLMProvider, ProviderMeter, STTProvider, TTSProvider

log = get_logger(__name__)

# name -> builder. Separate tables per stage (a provider may serve >1 stage, e.g. Sarvam).
STT_PROVIDERS: dict[str, STTProvider] = {
    stt_sarvam.PROVIDER.name: stt_sarvam.PROVIDER,
    stt_deepgram.PROVIDER.name: stt_deepgram.PROVIDER,
    stt_whisper.PROVIDER.name: stt_whisper.PROVIDER,
}
LLM_PROVIDERS: dict[str, LLMProvider] = {
    llm_openai.PROVIDER.name: llm_openai.PROVIDER,
    llm_gemini.PROVIDER.name: llm_gemini.PROVIDER,
}
TTS_PROVIDERS: dict[str, TTSProvider] = {
    tts_sarvam.PROVIDER.name: tts_sarvam.PROVIDER,
    tts_elevenlabs.PROVIDER.name: tts_elevenlabs.PROVIDER,
}


@dataclass
class BuiltSession:
    """Everything the worker needs to run one intake on a chosen pipeline/language."""

    session: Any  # livekit.agents.AgentSession
    meters: dict[str, ProviderMeter]  # {"stt": ..., "llm": ..., "tts": ...}
    noise_cancellation: Any | None
    pipeline: str
    language: str


def _resolve(table: dict[str, Any], stage_cfg: dict[str, Any], stage: str) -> Any:
    """Look up the builder for a stage's provider, or raise a clear error."""
    name = stage_cfg.get("provider")
    if name not in table:
        known = ", ".join(sorted(table)) or "<none>"
        raise KeyError(
            f"No registered {stage} provider '{name}'. Registered: {known}. "
            "(Deferred providers need their wrapper added before use.)"
        )
    return table[name]


def _load_krisp() -> Any | None:
    """Return a Krisp BVC noise-cancellation component, or None if unavailable.

    Krisp/BVC requires LiveKit Cloud. We degrade gracefully (no NC) rather than crash if the
    plugin or Cloud entitlement is missing.
    """
    try:
        from livekit.plugins import noise_cancellation

        return noise_cancellation.BVC()
    except Exception as exc:  # noqa: BLE001 - degrade gracefully, log why
        log.warning("krisp_unavailable", error=str(exc))
        return None


def build_session(pipeline_name: str, language: str) -> BuiltSession:
    """Assemble a fully wired `AgentSession` for a pipeline + language.

    Returns the session plus per-stage meters (for telemetry) and the noise-cancellation
    component (the worker applies it via `RoomInputOptions` at `session.start`).
    """
    cfg = get_pipeline(pipeline_name)

    stt_b = _resolve(STT_PROVIDERS, cfg["stt"], "STT").build(cfg["stt"], language)
    llm_b = _resolve(LLM_PROVIDERS, cfg["llm"], "LLM").build(cfg["llm"], language)
    tts_b = _resolve(TTS_PROVIDERS, cfg["tts"], "TTS").build(cfg["tts"], language)

    # Lazy heavy imports so this module imports without the full agent stack.
    from livekit.agents import AgentSession
    from livekit.plugins import silero
    from livekit.plugins.turn_detector.multilingual import MultilingualModel

    session = AgentSession(
        stt=stt_b.component,
        llm=llm_b.component,
        tts=tts_b.component,
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    log.info(
        "session_built",
        pipeline=pipeline_name,
        language=language,
        stt=f"{cfg['stt']['provider']}/{cfg['stt']['model']}",
        llm=f"{cfg['llm']['provider']}/{cfg['llm']['model']}",
        tts=f"{cfg['tts']['provider']}/{cfg['tts']['model']}",
    )

    return BuiltSession(
        session=session,
        meters={"stt": stt_b.meter, "llm": llm_b.meter, "tts": tts_b.meter},
        noise_cancellation=_load_krisp(),
        pipeline=pipeline_name,
        language=language,
    )
