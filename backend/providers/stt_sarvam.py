"""Sarvam Saaras STT provider wrapper (POC default STT).

Wraps `livekit.plugins.sarvam.STT`. Saaras v3 supports en/hi/mr + code-mix natively and a
`mode` (transcribe/translate/verbatim/translit) available only on saaras:v3. Returns a
`StageBuild` carrying the LiveKit STT component + a `ProviderMeter` (billable unit = audio
seconds).
"""

from __future__ import annotations

from typing import Any

from livekit.plugins import sarvam

from providers.base import ProviderMeter, Stage, StageBuild

# Map our short language codes to Sarvam STT language codes (verified: hi-IN, mr-IN, en-IN).
_LANG_CODES = {"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN"}


class SarvamSTTProvider:
    """Builds a Sarvam Saaras STT component."""

    name = "sarvam"

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild:
        """Construct `sarvam.STT` from the stage config and resolved language."""
        model = stage_cfg.get("model", "saaras:v3")
        pricing_key = stage_cfg.get("pricing_key", f"sarvam/{model}")
        options = dict(stage_cfg.get("options") or {})
        lang_code = _LANG_CODES.get(language, "en-IN")

        kwargs: dict[str, Any] = {"model": model, "language": lang_code}
        # `mode` (e.g. "translate") is only valid on saaras:v3.
        if "mode" in options and model.startswith("saaras:v3"):
            kwargs["mode"] = options["mode"]

        stt = sarvam.STT(**kwargs)
        meter = ProviderMeter(
            stage=Stage.STT, provider=self.name, model=model, pricing_key=pricing_key
        )
        return StageBuild(component=stt, meter=meter)


PROVIDER = SarvamSTTProvider()
