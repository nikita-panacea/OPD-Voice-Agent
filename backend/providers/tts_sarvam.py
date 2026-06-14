"""Sarvam Bulbul TTS provider wrapper (POC default TTS).

Wraps `livekit.plugins.sarvam.TTS` (Bulbul). The agent replies in the patient's language
with a language-matched voice from `voices.yaml`. Returns a `StageBuild` with a
`ProviderMeter` (billable unit = characters synthesized).
"""

from __future__ import annotations

from typing import Any

from config.settings import get_voice
from providers.base import ProviderMeter, Stage, StageBuild

# Map our short language codes to Sarvam TTS target language codes.
_LANG_CODES = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN"}


class SarvamTTSProvider:
    """Builds a Sarvam Bulbul TTS component."""

    name = "sarvam"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `sarvam.TTS` from the stage config, language, and voice config."""
        from livekit.plugins import sarvam  # lazy import (heavy)

        model = stage_cfg.get("model", "bulbul:v2")
        pricing_key = stage_cfg.get("pricing_key", f"sarvam/{model}")
        options = dict(stage_cfg.get("options") or {})
        target_lang = _LANG_CODES.get(language, "en-IN")
        speaker = get_voice(language).get("speaker", "anushka")

        tts = sarvam.TTS(
            model=model,
            target_language_code=target_lang,
            speaker=speaker,
            **options,
        )
        meter = ProviderMeter(
            stage=Stage.TTS, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=tts, meter=meter)


PROVIDER = SarvamTTSProvider()
