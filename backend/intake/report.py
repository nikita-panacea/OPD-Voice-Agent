"""Structured clinician-facing intake report (CLAUDE.md §8.3).

Builds a Pydantic-validated report from the persisted intake fields and renders a
doctor-facing Markdown version. Both carry the disclaimer and contain **no diagnostic
impression or treatment suggestion** — this tool collects and reflects information only.

POC note: the report is assembled deterministically from the captured fields (no LLM call), so
it is cheap, reproducible, and testable. An LLM-polished HPI narrative is a future enhancement.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from intake import red_flags
from intake.questions import get_field, localized
from logging_setup import get_logger
from store.db import IntakeFieldRow, IntakeSession, ReportRow, session_scope

log = get_logger(__name__)

DISCLAIMER = "Automated intake summary — not a diagnosis. For clinician review."

# Which captured fields make up the History of Present Illness section.
HPI_FIELDS = [
    "onset_duration",
    "location",
    "character",
    "severity",
    "timing_pattern",
    "aggravating_relieving",
    "associated_symptoms",
]
# Free-text fields worth re-screening for red-flag mentions when building the report.
SCREEN_FIELDS = ["chief_complaint", "associated_symptoms", "additional_info", "allergies"]


class ReportItem(BaseModel):
    """A labelled captured value (with confirmation state)."""

    field_id: str
    label: str
    value: str
    confirmed: bool = False


class IntakeReport(BaseModel):
    """The structured intake report handed to the clinician."""

    session_id: str
    language: str
    generated_at: str
    disclaimer: str = DISCLAIMER
    completion_rate: float = 0.0

    urgent_flag: bool = False
    urgent_reason: str | None = None
    red_flag_categories: list[str] = Field(default_factory=list)

    identity: str | None = None
    chief_complaint: str | None = None
    chief_complaint_patient_words: str | None = None
    hpi: list[ReportItem] = Field(default_factory=list)
    medications: str | None = None
    allergies: str | None = None
    past_medical_history: str | None = None
    past_surgical_history: str | None = None
    family_history: str | None = None
    social_history: str | None = None
    additional_info: str | None = None


def _load(session_id: str) -> tuple[IntakeSession, dict[str, IntakeFieldRow]]:
    """Load the session row + its captured fields keyed by field id."""
    with session_scope() as db:
        session = db.get(IntakeSession, session_id)
        if session is None:
            raise KeyError(f"Unknown session '{session_id}'")
        rows = db.query(IntakeFieldRow).filter_by(session_id=session_id).all()
        fields = {r.field_id: r for r in rows}
        # detach: read attributes we need before the session closes
        session_data = IntakeSession(
            id=session.id,
            language=session.language,
            urgent_flag=session.urgent_flag,
            urgent_reason=session.urgent_reason,
        )
    return session_data, fields


def _value(fields: dict[str, IntakeFieldRow], field_id: str) -> str | None:
    row = fields.get(field_id)
    return row.value if row else None


def build_report(session_id: str) -> IntakeReport:
    """Assemble an `IntakeReport` from the persisted intake of one session."""
    session, fields = _load(session_id)
    language = session.language

    # Completion rate over required fields.
    from intake.questions import required_field_ids

    required = required_field_ids()
    filled = sum(1 for fid in required if fid in fields)
    completion = filled / len(required) if required else 1.0

    # Re-screen captured free text for red-flag mentions (pertinent positives for the doctor).
    categories: list[str] = []
    for fid in SCREEN_FIELDS:
        val = _value(fields, fid)
        if val:
            flag = red_flags.detect(val, language)
            if flag and flag.category not in categories:
                categories.append(flag.category)

    hpi: list[ReportItem] = []
    for fid in HPI_FIELDS:
        row = fields.get(fid)
        if row and row.value:
            spec = get_field(fid)
            hpi.append(
                ReportItem(
                    field_id=fid,
                    label=localized(spec.label, language) if spec else fid,
                    value=row.value,
                    confirmed=bool(row.confirmed),
                )
            )

    return IntakeReport(
        session_id=session_id,
        language=language,
        generated_at=datetime.now(UTC).isoformat(),
        completion_rate=round(completion, 3),
        urgent_flag=bool(session.urgent_flag),
        urgent_reason=session.urgent_reason,
        red_flag_categories=categories,
        identity=_value(fields, "identity"),
        chief_complaint=_value(fields, "chief_complaint"),
        chief_complaint_patient_words=_value(fields, "chief_complaint"),
        hpi=hpi,
        medications=_value(fields, "medications"),
        allergies=_value(fields, "allergies"),
        past_medical_history=_value(fields, "past_medical_history"),
        past_surgical_history=_value(fields, "past_surgical_history"),
        family_history=_value(fields, "family_history"),
        social_history=_value(fields, "social_history"),
        additional_info=_value(fields, "additional_info"),
    )


def render_markdown(report: IntakeReport) -> str:
    """Render the report as doctor-facing Markdown (disclaimer first)."""
    lines: list[str] = []
    lines.append(f"> **{report.disclaimer}**")
    lines.append("")
    lines.append("# OPD Intake Summary")
    lines.append("")
    if report.urgent_flag:
        reason = report.urgent_reason or "see red flags"
        lines.append(f"## 🚨 URGENT — flagged for staff: {reason}")
        lines.append("")
    lines.append(f"- **Session:** {report.session_id}")
    lines.append(f"- **Language:** {report.language}")
    lines.append(f"- **Generated:** {report.generated_at}")
    lines.append(f"- **Completion:** {round(report.completion_rate * 100)}% of required fields")
    if report.red_flag_categories:
        lines.append(f"- **Red-flag mentions:** {', '.join(report.red_flag_categories)}")
    lines.append("")

    if report.identity:
        lines.append(f"**Patient:** {report.identity}")
        lines.append("")

    lines.append("## Chief complaint")
    if report.chief_complaint_patient_words:
        lines.append(f'> "{report.chief_complaint_patient_words}" (patient\'s own words)')
    else:
        lines.append("_Not captured._")
    lines.append("")

    lines.append("## History of present illness")
    if report.hpi:
        for item in report.hpi:
            mark = " ✓" if item.confirmed else ""
            lines.append(f"- **{item.label}:** {item.value}{mark}")
    else:
        lines.append("_Not captured._")
    lines.append("")

    sections = [
        ("Current medications", report.medications),
        ("Allergies", report.allergies),
        ("Past medical history", report.past_medical_history),
        ("Past surgical / hospitalization", report.past_surgical_history),
        ("Family history", report.family_history),
        ("Social history", report.social_history),
        ("Anything else", report.additional_info),
    ]
    for title, value in sections:
        lines.append(f"## {title}")
        lines.append(value if value else "_Not captured._")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate_and_store(session_id: str) -> tuple[IntakeReport, str]:
    """Build the report, render Markdown, and upsert the `ReportRow`. Returns (report, md)."""
    report = build_report(session_id)
    markdown = render_markdown(report)
    payload = report.model_dump_json()
    with session_scope() as db:
        row = db.query(ReportRow).filter_by(session_id=session_id).one_or_none()
        if row is None:
            row = ReportRow(session_id=session_id, json_blob=payload, markdown=markdown)
            db.add(row)
        else:
            row.json_blob = payload
            row.markdown = markdown
    log.info("report_generated", session=session_id, completion=report.completion_rate)
    return report, markdown


def load_stored(session_id: str) -> tuple[dict, str] | None:
    """Return the stored (json_dict, markdown) for a session, or None if not generated."""
    with session_scope() as db:
        row = db.query(ReportRow).filter_by(session_id=session_id).one_or_none()
        if row is None:
            return None
        return json.loads(row.json_blob), row.markdown
