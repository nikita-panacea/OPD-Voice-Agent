"""OpenAI Whisper / transcription STT provider wrapper (eval/comparison baseline).

Wraps `livekit.plugins.openai.STT`. Per CLAUDE.md §5, classic Whisper (`whisper-1`) is
batch-oriented and weak for low-latency streaming — keep it as an **eval baseline**. For a
runnable live comparison, default to `gpt-4o-mini-transcribe` (cheap, streaming-capable);
select `whisper-1` via config for the true-Whisper baseline. Billable unit = audio seconds.
"""

from __future__ import annotations

from typing import Any

from providers.base import ProviderMeter, Stage, StageBuild

_LANG_CODES = {"en": "en", "hi": "hi", "mr": "mr"}


class WhisperSTTProvider:
    """Builds an OpenAI STT (Whisper / gpt-4o-transcribe) component."""

    name = "whisper"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `openai.STT` from the stage config and resolved language."""
        from livekit.plugins import openai  # lazy import (heavy)

        model = stage_cfg.get("model", "gpt-4o-mini-transcribe")
        pricing_key = stage_cfg.get("pricing_key", f"openai/{model}")
        options = dict(stage_cfg.get("options") or {})

        stt = openai.STT(model=model, language=_LANG_CODES.get(language, "en"), **options)
        meter = ProviderMeter(
            stage=Stage.STT, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=stt, meter=meter)


PROVIDER = WhisperSTTProvider()
