"""Per-turn telemetry record (counts, costs, latency) — NO clinical content (§9).

A "turn" is one user utterance → one agent response. `TurnTelemetry` accumulates the billable
units and latency components for a turn; the meter computes costs and persists it. Pure Python,
unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TurnTelemetry:
    """Accumulated metrics for one conversational turn."""

    session_id: str
    pipeline: str
    turn_index: int = 0

    # billable units
    stt_seconds: float = 0.0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    llm_cached_tokens: int = 0
    tts_characters: int = 0

    # per-component cost (USD)
    stt_cost: float = 0.0
    llm_cost: float = 0.0
    tts_cost: float = 0.0

    # latency components (milliseconds)
    eou_delay_ms: float | None = None
    llm_ttft_ms: float | None = None
    tts_ttfb_ms: float | None = None

    @property
    def total_cost(self) -> float:
        """Total USD cost for this turn across stages."""
        return round(self.stt_cost + self.llm_cost + self.tts_cost, 8)

    @property
    def e2e_latency_ms(self) -> float | None:
        """End-to-end response latency: patient stops speaking → agent audio starts.

        Approximated as EOU delay + LLM time-to-first-token + TTS time-to-first-byte. Returns
        None if none of the components were observed.
        """
        parts = [
            p for p in (self.eou_delay_ms, self.llm_ttft_ms, self.tts_ttfb_ms) if p is not None
        ]
        return round(sum(parts), 3) if parts else None

    def has_response(self) -> bool:
        """True once the agent side of the turn (LLM or TTS) has produced metrics."""
        return bool(self.llm_output_tokens or self.tts_characters or self.llm_ttft_ms)
