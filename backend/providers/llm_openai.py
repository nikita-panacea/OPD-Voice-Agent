"""OpenAI LLM provider wrapper (POC default intake brain).

Wraps `livekit.plugins.openai.LLM`. GPT-4.1 is the default for strong instruction-following
and tool-calling (`save_intake_field`). Returns a `StageBuild` with a `ProviderMeter`
(billable units = input/output tokens).
"""

from __future__ import annotations

from typing import Any

from livekit.plugins import openai

from providers.base import ProviderMeter, Stage, StageBuild


class OpenAILLMProvider:
    """Builds an OpenAI LLM component."""

    name = "openai"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `openai.LLM` from the stage config (language is prompt-driven, not here)."""
        model = stage_cfg.get("model", "gpt-4.1")
        pricing_key = stage_cfg.get("pricing_key", f"openai/{model}")
        options = dict(stage_cfg.get("options") or {})

        llm = openai.LLM(model=model, **options)
        meter = ProviderMeter(
            stage=Stage.LLM, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=llm, meter=meter)


PROVIDER = OpenAILLMProvider()
