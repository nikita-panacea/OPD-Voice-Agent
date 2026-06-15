"""Session meter: turns LiveKit per-turn metrics into costed `TelemetryRow`s.

Subscribes to the `AgentSession`'s `metrics_collected` events, uses the per-stage
`ProviderMeter`s (from the registry) to extract billable units, prices them via `cost.py`, and
persists one row per conversational turn. Routing is by metric class name, so the accumulation
logic is unit-testable with fakes (no LiveKit session needed).

NEVER stores clinical content — counts, costs, latency only (§9).
"""

from __future__ import annotations

from logging_setup import get_logger
from providers.base import ProviderMeter
from store.db import TelemetryRow, session_scope
from telemetry import cost
from telemetry.events import TurnTelemetry

log = get_logger(__name__)


def _ms(seconds: float | None) -> float | None:
    """Convert a LiveKit latency (seconds) to milliseconds, preserving None."""
    return None if seconds is None else round(float(seconds) * 1000.0, 3)


class SessionMeter:
    """Accumulates and persists per-turn telemetry for one session."""

    def __init__(self, session_id: str, pipeline: str, meters: dict[str, ProviderMeter]) -> None:
        self.session_id = session_id
        self.pipeline = pipeline
        self.meters = meters
        self._turn_index = 0
        self._cur = self._new_turn()

    def _new_turn(self) -> TurnTelemetry:
        return TurnTelemetry(
            session_id=self.session_id, pipeline=self.pipeline, turn_index=self._turn_index
        )

    def attach(self, agent_session) -> None:
        """Subscribe to the AgentSession's metrics stream."""
        agent_session.on("metrics_collected", self._on_metrics)

    def _on_metrics(self, ev) -> None:
        self.record(getattr(ev, "metrics", ev))

    def record(self, metric) -> None:
        """Route one metric into the current turn (by metric class name)."""
        name = type(metric).__name__
        if name == "STTMetrics":
            # A new user utterance starts a new turn once the previous one had a response.
            if self._cur.has_response():
                self.flush()
            units = self.meters["stt"].billable_units(metric)
            self._cur.stt_seconds += units.stt_seconds
            self._cur.stt_cost += cost.stt_cost(units.stt_seconds, self.meters["stt"].pricing_key)
        elif name == "EOUMetrics":
            self._cur.eou_delay_ms = _ms(getattr(metric, "end_of_utterance_delay", None))
        elif name == "LLMMetrics":
            units = self.meters["llm"].billable_units(metric)
            self._cur.llm_input_tokens += units.llm_input_tokens
            self._cur.llm_output_tokens += units.llm_output_tokens
            self._cur.llm_cached_tokens += units.llm_cached_tokens
            self._cur.llm_cost += cost.llm_cost(
                units.llm_input_tokens,
                units.llm_output_tokens,
                self.meters["llm"].pricing_key,
                cached_tokens=units.llm_cached_tokens,
            )
            if self._cur.llm_ttft_ms is None:
                self._cur.llm_ttft_ms = _ms(getattr(metric, "ttft", None))
        elif name == "TTSMetrics":
            units = self.meters["tts"].billable_units(metric)
            self._cur.tts_characters += units.tts_characters
            self._cur.tts_cost += cost.tts_cost(
                units.tts_characters, self.meters["tts"].pricing_key
            )
            if self._cur.tts_ttfb_ms is None:
                self._cur.tts_ttfb_ms = _ms(getattr(metric, "ttfb", None))

    def flush(self) -> None:
        """Persist the current turn (if it has data) and start a new one."""
        t = self._cur
        if not (t.stt_seconds or t.has_response()):
            return
        with session_scope() as db:
            db.add(
                TelemetryRow(
                    session_id=t.session_id,
                    turn_index=t.turn_index,
                    pipeline=t.pipeline,
                    stt_seconds=t.stt_seconds,
                    llm_input_tokens=t.llm_input_tokens,
                    llm_output_tokens=t.llm_output_tokens,
                    llm_cached_tokens=t.llm_cached_tokens,
                    tts_characters=t.tts_characters,
                    stt_cost=t.stt_cost,
                    llm_cost=t.llm_cost,
                    tts_cost=t.tts_cost,
                    e2e_latency_ms=t.e2e_latency_ms,
                )
            )
        log.info(
            "turn_metered",
            session=t.session_id,
            turn=t.turn_index,
            cost_usd=t.total_cost,
            e2e_ms=t.e2e_latency_ms,
        )
        self._turn_index += 1
        self._cur = self._new_turn()

    def close(self) -> None:
        """Flush any in-progress turn at session end."""
        self.flush()
