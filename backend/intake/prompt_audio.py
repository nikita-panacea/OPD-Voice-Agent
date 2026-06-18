"""Resolve pre-recorded browser prompt audio for the LiveKit agent flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.settings import get_settings
from intake.questions import get_field, localized

FIELD_AUDIO_BASENAMES = {
    "consent": "q01_consent",
    "identity": "q02_identity",
    "chief_complaint": "q03_chief_complaint",
    "onset_duration": "q04_onset",
    "location": "q05_location",
    "character": "q06_character",
    "severity": "q07_severity",
    "timing_pattern": "q08_timing",
    "aggravating_relieving": "q09_aggravating",
    "associated_symptoms": "q10_associated",
    "medications": "q11_medications",
    "allergies": "q12_allergies",
    "past_medical_history": "q13_past_medical",
    "past_surgical_history": "q14_past_surgical",
    "family_history": "q15_family",
    "social_history": "q16_social",
    "additional_info": "q17_anything_else",
}


@dataclass(frozen=True)
class ResolvedPromptAudio:
    """A prompt clip the browser can play over HTTP."""

    field_id: str
    variant: str
    url: str
    text: str


class PromptAudioResolver:
    """Map an intake field/language to a pre-recorded file under audio_assets."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        self._assets_dir = Path(assets_dir or get_settings().audio_assets_dir)

    @staticmethod
    def _basename(field_id: str, variant: str) -> str | None:
        basename = FIELD_AUDIO_BASENAMES.get(field_id)
        if basename is None:
            return None
        if variant == "simpler":
            return f"{basename}_simpler"
        return basename

    def resolve(
        self, field_id: str, language: str, variant: str = "prompt"
    ) -> ResolvedPromptAudio | None:
        """Return browser-playable prompt audio, or None so the agent can speak normally."""
        if variant not in {"prompt", "simpler"}:
            return None

        field = get_field(field_id)
        basename = self._basename(field_id, variant)
        if field is None or basename is None:
            return None

        for ext in (".mp3", ".wav"):
            candidate = self._assets_dir / language / f"{basename}{ext}"
            if candidate.exists():
                prompt_map = field.simpler_prompt if variant == "simpler" else field.prompt
                return ResolvedPromptAudio(
                    field_id=field_id,
                    variant=variant,
                    url=f"/audio/{language}/{basename}{ext}",
                    text=localized(prompt_map, language),
                )
        return None
