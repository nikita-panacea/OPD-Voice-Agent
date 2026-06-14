"""Google Gemini LLM provider wrapper (for the low_cost comparison pipeline).

Wraps `livekit.plugins.google.LLM`. Gemini 2.5 Flash / Flash-Lite are low-cost, tool-calling
capable intake brains. Billable units = input/output tokens.
"""

from __future__ import annotations

from typing import Any

from providers.base import ProviderMeter, Stage, StageBuild


class GeminiLLMProvider:
    """Builds a Google Gemini LLM component."""

    name = "google"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `google.LLM` from the stage config (language is prompt-driven)."""
        from livekit.plugins import google  # lazy import (heavy)

        model = stage_cfg.get("model", "gemini-2.5-flash")
        pricing_key = stage_cfg.get("pricing_key", f"google/{model}")
        options = dict(stage_cfg.get("options") or {})

        llm = google.LLM(model=model, **options)
        meter = ProviderMeter(
            stage=Stage.LLM, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=llm, meter=meter)


PROVIDER = GeminiLLMProvider()
