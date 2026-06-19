"""Per-session analysis log: aggregates cost components + captured fields (POC, contains PHI)."""

from __future__ import annotations

import uuid

from store.db import IntakeFieldRow, IntakeSession, TelemetryRow, init_db, session_scope
from telemetry.session_log import build_session_log


def _seed_session() -> str:
    init_db()
    sid = f"log-{uuid.uuid4().hex[:8]}"
    with session_scope() as db:
        db.add(
            IntakeSession(
                id=sid,
                language="en",
                pipeline="indic_quality",
                status="completed",
                consent_given=True,
                session_seconds=42.5,
                livekit_cost=0.004,
            )
        )
        db.add(
            IntakeFieldRow(
                session_id=sid,
                field_id="chief_complaint",
                value="severe chest pain",
                confidence=0.91,
            )
        )
        db.add(
            TelemetryRow(
                session_id=sid,
                turn_index=0,
                pipeline="indic_quality",
                stt_seconds=8.0,
                llm_input_tokens=150,
                llm_output_tokens=40,
                tts_characters=90,
                stt_cost=0.0007,
                llm_cost=0.0005,
                tts_cost=0.0015,
                e2e_latency_ms=950.0,
            )
        )
    return sid


def test_session_log_has_costs_transcript_and_flags() -> None:
    sid = _seed_session()
    log = build_session_log(sid, interaction_seconds=42.5)

    assert log.assistant_name == "Dhara"
    assert log.interaction_seconds == 42.5
    assert log.components["stt"].units == 8.0
    assert log.components["llm"].input_tokens == 150
    assert log.components["tts"].units == 90
    assert log.components["webrtc"].cost_usd == 0.004
    assert log.total_cost_usd > 0
    assert log.latency_e2e_ms == [950.0]

    fields = {t["field_id"] for t in log.transcript if t["answer_transcript"]}
    assert "chief_complaint" in fields
    assert "chest_pain" in log.red_flags

    d = log.to_dict()
    assert d["cost"]["total_cost_usd"] > 0
    assert any(t["field_id"] == "chief_complaint" for t in d["transcript"])
