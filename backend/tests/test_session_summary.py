"""Tests for the per-session cost/performance summary log."""

import uuid

import pytest

from store.db import (
    IntakeFieldRow,
    IntakeSession,
    TelemetryRow,
    TranscriptRow,
    init_db,
    session_scope,
)
from telemetry import session_summary


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def _seed() -> str:
    sid = f"sum-{uuid.uuid4().hex[:8]}"
    with session_scope() as db:
        db.add(
            IntakeSession(
                id=sid,
                pipeline="indic_quality",
                language="en",
                status="completed",
                session_seconds=300.0,
                livekit_cost=0.05,
            )
        )
        db.add(IntakeFieldRow(session_id=sid, field_id="chief_complaint", value="fever"))
        for i in range(2):
            db.add(
                TelemetryRow(
                    session_id=sid,
                    turn_index=i,
                    pipeline="indic_quality",
                    stt_seconds=2.0,
                    llm_input_tokens=100,
                    llm_output_tokens=20,
                    llm_cached_tokens=50,
                    tts_characters=80,
                    stt_cost=0.001,
                    llm_cost=0.002,
                    tts_cost=0.003,
                    e2e_latency_ms=500.0 + i * 100,
                )
            )
        db.add(TranscriptRow(session_id=sid, seq=0, role="agent", text="Hello, I'm Dhara."))
        db.add(TranscriptRow(session_id=sid, seq=1, role="patient", text="I have a fever."))
    return sid


def test_build_summary_aggregates_components_and_total() -> None:
    sid = _seed()
    s = session_summary.build_summary(sid)

    assert s["duration_seconds"] == 300.0
    assert s["turns"] == 2
    c = s["components"]
    assert c["stt"]["audio_seconds"] == pytest.approx(4.0)
    assert c["llm"]["input_tokens"] == 200
    assert c["llm"]["output_tokens"] == 40
    assert c["llm"]["cached_tokens"] == 100
    assert c["tts"]["characters"] == 160
    assert c["livekit"]["cost_usd"] == pytest.approx(0.05)
    assert c["stt"]["model"] == "sarvam/saaras:v3"  # from indic_quality pipeline config
    # total = STT(0.002) + LLM(0.004) + TTS(0.006) + LiveKit(0.05)
    assert s["total_cost_usd"] == pytest.approx(0.062)
    assert s["median_e2e_latency_ms"] == pytest.approx(550.0)
    assert len(s["transcript"]) == 2
    assert 0.0 < s["completion_rate"] <= 1.0


def test_write_session_files_creates_json_and_md() -> None:
    sid = _seed()
    json_path = session_summary.write_session_files(sid)
    assert json_path.exists()
    md_path = json_path.with_suffix(".md")
    assert md_path.exists()
    md = md_path.read_text(encoding="utf-8")
    assert "Cost & usage breakdown" in md
    assert "Total" in md
