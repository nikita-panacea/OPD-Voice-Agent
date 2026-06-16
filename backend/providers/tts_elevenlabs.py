"""ElevenLabs TTS provider wrapper (for the global_stack comparison pipeline).

Wraps `livekit.plugins.elevenlabs.TTS`. Flash v2.5 (`eleven_flash_v2_5`) is the low-latency,
multilingual (incl. Hindi) tier. Voice can be overridden via `options.voice_id`. Billable unit
= characters synthesized.
"""

from __future__ import annotations

from typing import Any

from livekit.plugins import elevenlabs

from config.settings import get_settings
from providers.base import ProviderMeter, Stage, StageBuild

_LANG_CODES = {"en": "en", "hi": "hi", "mr": "mr"}


class ElevenLabsTTSProvider:
    """Builds an ElevenLabs TTS component."""

    name = "elevenlabs"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `elevenlabs.TTS` from the stage config and resolved language."""
        model = stage_cfg.get("model", "eleven_flash_v2_5")
        pricing_key = stage_cfg.get("pricing_key", f"elevenlabs/{model}")
        options = dict(stage_cfg.get("options") or {})
        voice_id = options.pop("voice_id", None)

        kwargs: dict[str, Any] = {"model": model, "language": _LANG_CODES.get(language, "en")}
        if voice_id:
            kwargs["voice_id"] = voice_id
        # The plugin reads ELEVEN_API_KEY; we standardize on ELEVENLABS_API_KEY in .env, so
        # pass it explicitly when set.
        api_key = get_settings().elevenlabs_api_key
        if api_key:
            kwargs["api_key"] = api_key
        kwargs.update(options)

        tts = elevenlabs.TTS(**kwargs)
        meter = ProviderMeter(
            stage=Stage.TTS, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=tts, meter=meter)


PROVIDER = ElevenLabsTTSProvider()
