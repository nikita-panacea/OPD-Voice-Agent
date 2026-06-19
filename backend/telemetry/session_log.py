"""Per-session analysis log — full transcript + cost/performance breakdown (POC).

Unlike the PHI-free `telemetry` table (counts/cost only), this log intentionally includes
clinical content so the POC can be analyzed for cost AND quality together. Store securely,
access-control it, and disable in production when not needed.

On session end we write one `<session_id>.json` and one `<session_id>.md` under
`backend/logs/sessions/`, containing:
  * total interaction time
  * per-component units (STT seconds, LLM tokens, TTS chars, LiveKit participant-minutes)
  * per-component cost + total cost/intake
  * per-turn end-to-end latency
  * captured fields with prompts + extracted values
  * flags (red-flags, unanswered, urgent)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.settings import CONFIG_DIR, get_settings
from intake import red_flags
from intake.questions import INTAKE_FIELDS, get_field, required_field_ids
from logging_setup import get_logger
from store.db import IntakeFieldRow, IntakeSession, TelemetryRow, TranscriptRow, session_scope

logger = get_logger(__name__)


@dataclass
class ComponentUsage:
    """Aggregated units + cost for one cost component (stt / llm / tts / webrtc)."""

    calls: int = 0
    units: float = 0.0
    unit_kind: str = ""
    input_tokens: float = 0.0
    output_tokens: float = 0.0
    cost_usd: float = 0.0


@dataclass
class SessionLog:
    """The full per-session analysis record."""

    session_id: str
    assistant_name: str
    language: str
    pipeline: str
    status: str
    urgent: bool
    consent_given: bool
    generated_at: str
    interaction_seconds: float
    components: dict[str, ComponentUsage] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    latency_e2e_ms: list[float] = field(default_factory=list)
    transcript: list[dict[str, Any]] = field(default_factory=list)
    conversation: list[dict[str, Any]] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    unanswered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "assistant_name": self.assistant_name,
            "language": self.language,
            "pipeline": self.pipeline,
            "status": self.status,
            "urgent": self.urgent,
            "consent_given": self.consent_given,
            "generated_at": self.generated_at,
            "interaction_seconds": round(self.interaction_seconds, 2),
            "cost": {
                "components": {
                    name: {
                        "calls": c.calls,
                        "units": round(c.units, 3),
                        "unit_kind": c.unit_kind,
                        "input_tokens": c.input_tokens,
                        "output_tokens": c.output_tokens,
                        "cost_usd": round(c.cost_usd, 6),
                    }
                    for name, c in self.components.items()
                },
                "total_cost_usd": round(self.total_cost_usd, 6),
            },
            "latency": {
                "e2e_ms": [round(x, 1) for x in self.latency_e2e_ms],
            },
            "flags": {"red_flags": self.red_flags, "unanswered": self.unanswered},
            "transcript": self.transcript,
            "conversation": self.conversation,
        }


def _field_status(field_id: str, value: str | None, confirmed: bool) -> str:
    if not value:
        return "unanswered"
    spec = get_field(field_id)
    if spec and spec.critical and not confirmed:
        return "needs_confirmation"
    return "answered"


def build_session_log(session_id: str, interaction_seconds: float) -> SessionLog:
    """Assemble the per-session log from the DB (session, telemetry, fields, transcript)."""
    settings = get_settings()
    with session_scope() as db:
        session = db.get(IntakeSession, session_id)
        telemetry = (
            db.query(TelemetryRow)
            .filter(TelemetryRow.session_id == session_id)
            .order_by(TelemetryRow.turn_index)
            .all()
        )
        field_rows = (
            db.query(IntakeFieldRow).filter(IntakeFieldRow.session_id == session_id).all()
        )
        utterances = (
            db.query(TranscriptRow)
            .filter(TranscriptRow.session_id == session_id)
            .order_by(TranscriptRow.seq)
            .all()
        )
        sess_meta = {
            "language": session.language if session else "en",
            "pipeline": session.pipeline if session else "",
            "status": session.status if session else "",
            "urgent": session.urgent_flag if session else False,
            "consent_given": session.consent_given if session else False,
            "livekit_cost": session.livekit_cost if session else 0.0,
            "session_seconds": session.session_seconds if session else interaction_seconds,
        }

    language = sess_meta["language"]
    fields_by_id = {r.field_id: r for r in field_rows}

    log = SessionLog(
        session_id=session_id,
        assistant_name=settings.assistant_name,
        generated_at=datetime.now(UTC).isoformat(),
        interaction_seconds=interaction_seconds,
        language=language,
        pipeline=sess_meta["pipeline"],
        status=sess_meta["status"],
        urgent=sess_meta["urgent"],
        consent_given=sess_meta["consent_given"],
    )

    stt = log.components.setdefault("stt", ComponentUsage(unit_kind="seconds"))
    llm = log.components.setdefault("llm", ComponentUsage(unit_kind="tokens"))
    tts = log.components.setdefault("tts", ComponentUsage(unit_kind="characters"))

    for row in telemetry:
        if row.stt_seconds:
            stt.calls += 1
            stt.units += row.stt_seconds
            stt.cost_usd += row.stt_cost or 0.0
        if row.llm_input_tokens or row.llm_output_tokens:
            llm.calls += 1
            llm.input_tokens += row.llm_input_tokens
            llm.output_tokens += row.llm_output_tokens
            llm.units += row.llm_input_tokens + row.llm_output_tokens
            llm.cost_usd += row.llm_cost or 0.0
        if row.tts_characters:
            tts.calls += 1
            tts.units += row.tts_characters
            tts.cost_usd += row.tts_cost or 0.0
        if row.e2e_latency_ms is not None:
            log.latency_e2e_ms.append(row.e2e_latency_ms)

    lk_cost = sess_meta["livekit_cost"] or 0.0
    lk_seconds = sess_meta["session_seconds"] or interaction_seconds
    if lk_cost or lk_seconds:
        log.components["webrtc"] = ComponentUsage(
            calls=1,
            units=round(lk_seconds / 60.0, 3),
            unit_kind="participant_minutes",
            cost_usd=lk_cost,
        )

    log.total_cost_usd = sum(c.cost_usd for c in log.components.values())

    required = set(required_field_ids())
    for spec in INTAKE_FIELDS:
        row = fields_by_id.get(spec.id)
        value = row.value if row else None
        confirmed = row.confirmed if row else False
        status = _field_status(spec.id, value, confirmed)
        prompt = spec.prompt.get(language) or spec.prompt.get("en", "")
        label = spec.label.get(language) or spec.label.get("en", spec.id)

        log.transcript.append(
            {
                "field_id": spec.id,
                "field": label,
                "prompt": prompt,
                "answer_transcript": value or "",
                "extracted_value": value or "",
                "stt_confidence": row.confidence if row else None,
                "confirmed": confirmed,
                "status": status,
            }
        )

        if spec.id in required and not value:
            log.unanswered.append(label)
        if value:
            hit = red_flags.detect(value, language)
            if hit and hit.category not in log.red_flags:
                log.red_flags.append(hit.category)

    for utt in utterances:
        log.conversation.append({"seq": utt.seq, "role": utt.role, "text": utt.text})
        if utt.role == "patient":
            hit = red_flags.detect(utt.text, language)
            if hit and hit.category not in log.red_flags:
                log.red_flags.append(hit.category)

    return log


def _render_markdown(log: SessionLog) -> str:
    lines = [
        f"# Session log — {log.session_id}",
        f"_Assistant: **{log.assistant_name}** · Language: {log.language} · "
        f"Pipeline: {log.pipeline}_",
        "",
        "> Contains PHI (full transcript). POC analysis aid only — secure / disable in prod.",
        "",
        f"- **Status:** {log.status}  ·  **Urgent:** {log.urgent}  ·  "
        f"**Consent:** {log.consent_given}",
        f"- **Total interaction time:** {log.interaction_seconds:.1f}s",
        f"- **Total cost / intake:** ${log.total_cost_usd:.6f}",
        "",
        "## Cost & usage by component",
        "| Component | calls | units | in_tok | out_tok | cost (USD) |",
        "|---|--:|--:|--:|--:|--:|",
    ]
    for name, c in log.components.items():
        lines.append(
            f"| {name} | {c.calls} | {c.units:.2f} {c.unit_kind} | "
            f"{int(c.input_tokens)} | {int(c.output_tokens)} | {c.cost_usd:.6f} |"
        )
    if log.latency_e2e_ms:
        avg = sum(log.latency_e2e_ms) / len(log.latency_e2e_ms)
        lines += [
            "",
            f"**Avg end-to-end latency:** {avg:.0f} ms (n={len(log.latency_e2e_ms)})",
        ]
    if log.red_flags:
        lines += ["", f"> **RED FLAGS:** {', '.join(log.red_flags)}"]
    if log.unanswered:
        lines += [f"> Unanswered: {', '.join(log.unanswered)}"]
    lines += ["", "## Captured fields"]
    for t in log.transcript:
        if t["status"] == "unanswered" and not t["answer_transcript"]:
            continue
        conf = f"{t['stt_confidence']:.2f}" if t["stt_confidence"] is not None else "n/a"
        lines += [
            f"### {t['field_id']} ({t['field']}) — {t['status']}",
            f"- **{log.assistant_name}:** {t['prompt']}",
            f"- **Patient:** {t['answer_transcript'] or '_(no answer)_'}",
            f"- **Extracted:** {t['extracted_value'] or '—'}  ·  conf={conf}  ·  "
            f"confirmed={t['confirmed']}",
            "",
        ]
    if log.conversation:
        lines += ["## Full conversation"]
        for turn in log.conversation:
            who = log.assistant_name if turn["role"] == "agent" else "Patient"
            lines.append(f"- **{who}:** {turn['text']}")
    return "\n".join(lines)


def write_session_log(session_id: str, interaction_seconds: float) -> Path | None:
    """Build + write the JSON and Markdown session logs. Returns the JSON path (or None)."""
    settings = get_settings()
    if not settings.session_log_enabled:
        return None
    log = build_session_log(session_id, interaction_seconds)
    out_dir = Path(settings.session_log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{session_id}.json"
    json_path.write_text(
        json.dumps(log.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / f"{session_id}.md").write_text(_render_markdown(log), encoding="utf-8")
    logger.info(
        "session_log_written",
        session=session_id,
        total_cost_usd=round(log.total_cost_usd, 6),
        interaction_seconds=round(interaction_seconds, 1),
        path=str(json_path.relative_to(CONFIG_DIR.parent)),
    )
    return json_path
