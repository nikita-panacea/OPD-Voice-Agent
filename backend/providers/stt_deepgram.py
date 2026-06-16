"""Deepgram Nova-3 STT provider wrapper (for the global_stack / low_cost comparison pipelines).

Wraps `livekit.plugins.deepgram.STT`. Nova-3 is true-streaming, low-latency. Language notes
(§7): Hindi is in the code-switch set; Marathi is supported only as a **monolingual** language
(`language="mr"`) — not in the code-switch set. Pass `options.language="multi"` for code-mix.
Billable unit = audio seconds.
"""

from __future__ import annotations

from typing import Any

from livekit.plugins import deepgram

from providers.base import ProviderMeter, Stage, StageBuild

# Our short codes -> Deepgram language codes. "multi" enables code-switch (en+hi etc.).
_LANG_CODES = {"en": "en-US", "hi": "hi", "mr": "mr"}


class DeepgramSTTProvider:
    """Builds a Deepgram Nova-3 STT component."""

    name = "deepgram"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `deepgram.STT` from the stage config and resolved language."""
        model = stage_cfg.get("model", "nova-3")
        pricing_key = stage_cfg.get("pricing_key", f"deepgram/{model}")
        options = dict(stage_cfg.get("options") or {})
        # An explicit options.language (e.g. "multi") overrides the per-session mapping.
        lang = options.pop("language", None) or _LANG_CODES.get(language, "en-US")

        stt = deepgram.STT(model=model, language=lang, **options)
        meter = ProviderMeter(
            stage=Stage.STT, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=stt, meter=meter)


PROVIDER = DeepgramSTTProvider()
