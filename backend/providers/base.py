"""Provider abstraction core: stage Protocols, billable-unit meter, and build result.

This module is **pure Python** (no LiveKit imports) so the metering logic is unit-testable
without the heavy agent stack. The provider wrappers (`stt_sarvam`, `llm_openai`,
`tts_sarvam`) import LiveKit plugins lazily and return a `StageBuild` = (LiveKit component,
`ProviderMeter`).

The meter's job (CLAUDE.md §6): after each call, report the **billable units** for a stage
(STT: audio seconds; LLM: input/output tokens; TTS: characters) plus the `pricing_key` to
resolve a unit price — so telemetry attributes cost per turn without provider code knowing
anything about reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class Stage(StrEnum):
    """The three swappable pipeline stages."""

    STT = "stt"
    LLM = "llm"
    TTS = "tts"


@dataclass
class BillableUnits:
    """Billable units extracted from a LiveKit metrics event for one stage/turn."""

    stage: Stage
    stt_seconds: float = 0.0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_cached_tokens: int = 0
    tts_characters: int = 0


def _first_attr(obj: Any, names: list[str], default: Any) -> Any:
    """Return the first present, non-None attribute/key in `names`, else `default`.

    LiveKit metric field names vary across plugin/agent versions, so we probe several
    candidates rather than hard-coding one (verify the live names in Phase F).
    """
    for name in names:
        if isinstance(obj, dict):
            if obj.get(name) is not None:
                return obj[name]
        else:
            val = getattr(obj, name, None)
            if val is not None:
                return val
    return default


@dataclass
class ProviderMeter:
    """Knows how to turn a stage's LiveKit metrics into `BillableUnits`.

    Holds the `pricing_key` so the telemetry/cost layer can resolve the unit price; the
    meter itself never computes cost (separation of concerns).
    """

    stage: Stage
    provider: str
    model: str
    pricing_key: str

    def billable_units(self, metrics: Any) -> BillableUnits:
        """Map a LiveKit STT/LLM/TTS metrics object (or dict) to `BillableUnits`."""
        if self.stage is Stage.STT:
            seconds = float(
                _first_attr(metrics, ["audio_duration", "duration", "audio_seconds"], 0.0) or 0.0
            )
            return BillableUnits(stage=self.stage, stt_seconds=seconds)
        if self.stage is Stage.LLM:
            return BillableUnits(
                stage=self.stage,
                llm_input_tokens=int(
                    _first_attr(metrics, ["prompt_tokens", "input_tokens"], 0) or 0
                ),
                llm_output_tokens=int(
                    _first_attr(metrics, ["completion_tokens", "output_tokens"], 0) or 0
                ),
                llm_cached_tokens=int(
                    _first_attr(
                        metrics,
                        ["prompt_cached_tokens", "cached_tokens", "cache_read_input_tokens"],
                        0,
                    )
                    or 0
                ),
            )
        # TTS
        chars = int(
            _first_attr(metrics, ["characters_count", "characters", "char_count"], 0) or 0
        )
        return BillableUnits(stage=self.stage, tts_characters=chars)


@dataclass
class StageBuild:
    """A built stage: the LiveKit component to hand to AgentSession + its meter."""

    component: Any
    meter: ProviderMeter


@runtime_checkable
class STTProvider(Protocol):
    """Builds an STT component for a pipeline stage config + resolved language."""

    name: str

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild: ...


@runtime_checkable
class LLMProvider(Protocol):
    """Builds an LLM component for a pipeline stage config."""

    name: str

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild: ...


@runtime_checkable
class TTSProvider(Protocol):
    """Builds a TTS component for a pipeline stage config + resolved language/voice."""

    name: str

    def build(self, stage_cfg: dict[str, Any], language: str) -> StageBuild: ...
