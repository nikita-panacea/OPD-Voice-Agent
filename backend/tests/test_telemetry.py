"""SessionMeter routing/accumulation tests using fake metric objects (no LiveKit session)."""

import uuid

import pytest

from providers.base import ProviderMeter, Stage
from store.db import TelemetryRow, init_db, session_scope
from telemetry.meter import SessionMeter


# Fake metric classes — class NAME drives routing in SessionMeter.record().
class STTMetrics:
    def __init__(self, audio_duration: float) -> None:
        self.audio_duration = audio_duration


class EOUMetrics:
    def __init__(self, end_of_utterance_delay: float) -> None:
        self.end_of_utterance_delay = end_of_utterance_delay


class LLMMetrics:
    def __init__(self, prompt_tokens: int, completion_tokens: int, ttft: float) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.prompt_cached_tokens = 0
        self.ttft = ttft


class TTSMetrics:
    def __init__(self, characters_count: int, ttfb: float) -> None:
        self.characters_count = characters_count
        self.ttfb = ttfb


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def _meters() -> dict[str, ProviderMeter]:
    return {
        "stt": ProviderMeter(Stage.STT, "sarvam", "saaras:v3", "sarvam/saaras:v3"),
        "llm": ProviderMeter(Stage.LLM, "openai", "gpt-4.1", "openai/gpt-4.1"),
        "tts": ProviderMeter(Stage.TTS, "sarvam", "bulbul:v2", "sarvam/bulbul:v2"),
    }


def test_single_turn_flush_persists_costed_row() -> None:
    sid = f"tel-{uuid.uuid4().hex[:8]}"
    meter = SessionMeter(sid, "indic_quality", _meters())

    meter.record(STTMetrics(audio_duration=2.0))
    meter.record(EOUMetrics(end_of_utterance_delay=0.3))
    meter.record(LLMMetrics(prompt_tokens=100, completion_tokens=50, ttft=0.4))
    meter.record(TTSMetrics(characters_count=120, ttfb=0.2))
    meter.close()  # flush

    with session_scope() as db:
        row = db.query(TelemetryRow).filter_by(session_id=sid, turn_index=0).one()
        assert row.stt_seconds == 2.0
        assert row.llm_input_tokens == 100
        assert row.llm_output_tokens == 50
        assert row.tts_characters == 120
        assert row.stt_cost == pytest.approx(2.0 * 0.000092)
        assert row.llm_cost == pytest.approx((100 * 2 + 50 * 8) / 1e6)
        assert row.tts_cost == pytest.approx(120 * 0.0000165)
        # e2e = (eou 0.3 + ttft 0.4 + ttfb 0.2) * 1000
        assert row.e2e_latency_ms == pytest.approx(900.0)


def test_new_user_utterance_flushes_previous_turn() -> None:
    sid = f"tel-{uuid.uuid4().hex[:8]}"
    meter = SessionMeter(sid, "indic_quality", _meters())

    # turn 0
    meter.record(STTMetrics(1.0))
    meter.record(LLMMetrics(10, 5, 0.3))
    meter.record(TTSMetrics(40, 0.1))
    # new user utterance -> flush turn 0, begin turn 1
    meter.record(STTMetrics(1.5))
    meter.record(LLMMetrics(20, 8, 0.25))
    meter.record(TTSMetrics(60, 0.15))
    meter.close()

    with session_scope() as db:
        rows = (
            db.query(TelemetryRow).filter_by(session_id=sid).order_by(TelemetryRow.turn_index).all()
        )
        assert [r.turn_index for r in rows] == [0, 1]
        assert rows[0].tts_characters == 40
        assert rows[1].tts_characters == 60
