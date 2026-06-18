"""Per-session cost + performance summary log (POC observability).

Aggregates everything about ONE session — duration, per-component usage (STT audio seconds,
LLM input/output/cached tokens, TTS characters, LiveKit minutes) with a per-component **cost
breakdown + total**, completion rate, median latency — plus the **full transcript**, and writes
it to `backend/logs/sessions/<session_id>.json` (machine) and `.md` (human) so you can analyze
the whole pipeline's cost & performance.

PHI: the per-session files include the verbatim transcript (clinical content). Apply the same
access/retention rules as the DB; keep `logs/` out of un-controlled sync/backup.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from config.settings import get_pipeline
from intake.questions import required_field_ids
from logging_setup import get_logger
from store.db import IntakeFieldRow, IntakeSession, TelemetryRow, TranscriptRow, session_scope

log = get_logger(__name__)

SESSIONS_LOG_DIR = Path(__file__).resolve().parents[1] / "logs" / "sessions"


def build_summary(session_id: str) -> dict:
    """Build the per-session cost/performance summary dict (telemetry + session + transcript)."""
    with session_scope() as db:
        s = db.get(IntakeSession, session_id)
        if s is None:
            raise KeyError(f"Unknown session '{session_id}'")
        telem = db.query(TelemetryRow).filter_by(session_id=session_id).all()
        field_rows = db.query(IntakeFieldRow.field_id).filter_by(session_id=session_id).all()
        field_ids = {fid for (fid,) in field_rows}
        transcript = [
            {"seq": t.seq, "role": t.role, "text": t.text}
            for t in db.query(TranscriptRow)
            .filter_by(session_id=session_id)
            .order_by(TranscriptRow.seq)
        ]
        pipeline, language, status = s.pipeline, s.language, s.status
        urgent_flag, urgent_reason = s.urgent_flag, s.urgent_reason
        session_seconds = s.session_seconds or 0.0
        livekit_cost = s.livekit_cost or 0.0
        created_at = s.created_at.isoformat() if s.created_at else None
        completed_at = s.completed_at.isoformat() if s.completed_at else None

    # Aggregate per-turn telemetry into per-component totals.
    stt_seconds = round(sum(t.stt_seconds for t in telem), 2)
    llm_in = sum(t.llm_input_tokens for t in telem)
    llm_out = sum(t.llm_output_tokens for t in telem)
    llm_cached = sum(t.llm_cached_tokens for t in telem)
    tts_chars = sum(t.tts_characters for t in telem)
    stt_cost = round(sum(t.stt_cost for t in telem), 6)
    llm_cost = round(sum(t.llm_cost for t in telem), 6)
    tts_cost = round(sum(t.tts_cost for t in telem), 6)
    latencies = [t.e2e_latency_ms for t in telem if t.e2e_latency_ms is not None]
    median_latency = round(statistics.median(latencies), 1) if latencies else None

    try:
        cfg = get_pipeline(pipeline)
    except KeyError:
        cfg = {}

    def _model(stage: str) -> str:
        st = cfg.get(stage, {})
        return f"{st.get('provider', '?')}/{st.get('model', '?')}"

    required = required_field_ids()
    completion = (
        round(sum(1 for f in required if f in field_ids) / len(required), 3) if required else 1.0
    )
    total_cost = round(stt_cost + llm_cost + tts_cost + livekit_cost, 6)

    return {
        "session_id": session_id,
        "pipeline": pipeline,
        "language": language,
        "status": status,
        "urgent_flag": urgent_flag,
        "urgent_reason": urgent_reason,
        "created_at": created_at,
        "completed_at": completed_at,
        "duration_seconds": round(session_seconds, 1),
        "duration_minutes": round(session_seconds / 60.0, 2),
        "turns": len(telem),
        "median_e2e_latency_ms": median_latency,
        "completion_rate": completion,
        "components": {
            "stt": {"model": _model("stt"), "audio_seconds": stt_seconds, "cost_usd": stt_cost},
            "llm": {
                "model": _model("llm"),
                "input_tokens": llm_in,
                "output_tokens": llm_out,
                "cached_tokens": llm_cached,
                "cost_usd": llm_cost,
            },
            "tts": {"model": _model("tts"), "characters": tts_chars, "cost_usd": tts_cost},
            "livekit": {
                "minutes": round(session_seconds / 60.0, 2),
                "cost_usd": round(livekit_cost, 6),
            },
        },
        "total_cost_usd": total_cost,
        "transcript": transcript,
    }


def _render_markdown(d: dict) -> str:
    c = d["components"]
    lines = [
        f"# Session summary — {d['session_id']}",
        "",
        f"- **Pipeline:** {d['pipeline']}  |  **Language:** {d['language']}  |  "
        f"**Status:** {d['status']}",
        f"- **Duration:** {d['duration_seconds']} s ({d['duration_minutes']} min)  |  "
        f"**Turns:** {d['turns']}",
        f"- **Completion:** {round(d['completion_rate'] * 100)}%  |  "
        f"**Median latency:** {d['median_e2e_latency_ms']} ms",
    ]
    if d["urgent_flag"]:
        lines.append(f"- **🚨 URGENT:** {d['urgent_reason']}")
    lines += [
        "",
        "## Cost & usage breakdown (USD)",
        "| Component | Model | Usage | Cost |",
        "|---|---|---|---|",
        f"| STT | {c['stt']['model']} | {c['stt']['audio_seconds']} s | "
        f"${c['stt']['cost_usd']:.6f} |",
        f"| LLM | {c['llm']['model']} | "
        f"in {c['llm']['input_tokens']} / out {c['llm']['output_tokens']} / "
        f"cached {c['llm']['cached_tokens']} tok | ${c['llm']['cost_usd']:.6f} |",
        f"| TTS | {c['tts']['model']} | {c['tts']['characters']} chars | "
        f"${c['tts']['cost_usd']:.6f} |",
        f"| LiveKit | livekit/cloud | {c['livekit']['minutes']} min | "
        f"${c['livekit']['cost_usd']:.6f} |",
        f"| **Total** | | | **${d['total_cost_usd']:.6f}** |",
        "",
        "## Transcript",
    ]
    if d["transcript"]:
        for t in d["transcript"]:
            who = "You" if t["role"] == "patient" else "Dhara"
            lines.append(f"- **{who}:** {t['text']}")
    else:
        lines.append("_No transcript captured._")
    return "\n".join(lines) + "\n"


def write_session_files(session_id: str) -> Path:
    """Write `<session_id>.json` + `.md` to logs/sessions/ and return the JSON path."""
    summary = build_summary(session_id)
    SESSIONS_LOG_DIR.mkdir(parents=True, exist_ok=True)
    json_path = SESSIONS_LOG_DIR / f"{session_id}.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (SESSIONS_LOG_DIR / f"{session_id}.md").write_text(_render_markdown(summary), encoding="utf-8")
    log.info(
        "session_summary_written",
        session=session_id,
        total_cost_usd=summary["total_cost_usd"],
        turns=summary["turns"],
        duration_s=summary["duration_seconds"],
    )
    return json_path
