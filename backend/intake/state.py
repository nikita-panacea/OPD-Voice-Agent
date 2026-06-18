"""Per-session intake state: the live answers + their persistence to SQLite.

`IntakeState` is the single object the agent mutates as it learns answers. Every change is
written through to the DB so partial progress survives a dropped call and the report generator
can read a finished session. It also produces the small payloads pushed to the live UI panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from intake.questions import get_field, localized, required_field_ids
from logging_setup import get_logger
from store.db import IntakeFieldRow, IntakeSession, session_scope

log = get_logger(__name__)


@dataclass
class FieldValue:
    """One captured answer."""

    value: str
    confidence: float = 1.0
    confirmed: bool = False


@dataclass
class IntakeState:
    """Live intake state for one session, with write-through persistence."""

    session_id: str
    language: str = "en"
    pipeline: str = "indic_quality"
    consent_given: bool = False
    urgent_flag: bool = False
    urgent_reason: str | None = None
    fields: dict[str, FieldValue] = field(default_factory=dict)

    # ---- persistence ----
    def persist_session(self) -> None:
        """Insert (or update) the session row. Call once at session start."""
        with session_scope() as db:
            row = db.get(IntakeSession, self.session_id)
            if row is None:
                row = IntakeSession(id=self.session_id)
                db.add(row)
            row.language = self.language
            row.pipeline = self.pipeline
            row.consent_given = self.consent_given
            row.urgent_flag = self.urgent_flag
            row.urgent_reason = self.urgent_reason

    def set_consent(self, granted: bool) -> None:
        """Record the consent decision (gate for all other collection)."""
        self.consent_given = granted
        with session_scope() as db:
            row = db.get(IntakeSession, self.session_id)
            if row is not None:
                row.consent_given = granted
        log.info("consent_recorded", session=self.session_id, granted=granted)

    def save_field(self, field_id: str, value: str, confidence: float = 1.0) -> None:
        """Upsert a captured field in memory + DB (preserves an existing confirmed flag)."""
        existing = self.fields.get(field_id)
        confirmed = existing.confirmed if existing else False
        self.fields[field_id] = FieldValue(value=value, confidence=confidence, confirmed=confirmed)
        self._persist_field(field_id)
        log.info("field_saved", session=self.session_id, field=field_id, confidence=confidence)

    def confirm_field(self, field_id: str) -> None:
        """Mark a critical field as confirmed after read-back."""
        fv = self.fields.get(field_id)
        if fv is None:
            return
        fv.confirmed = True
        self._persist_field(field_id)

    def raise_urgent(self, reason: str) -> None:
        """Set the URGENT escalation flag (surfaced to staff)."""
        self.urgent_flag = True
        self.urgent_reason = reason
        with session_scope() as db:
            row = db.get(IntakeSession, self.session_id)
            if row is not None:
                row.urgent_flag = True
                row.urgent_reason = reason
        log.warning("urgent_raised", session=self.session_id, reason=reason)

    def finalize(self, status: str = "completed") -> None:
        """Mark the session complete (or handoff)."""
        with session_scope() as db:
            row = db.get(IntakeSession, self.session_id)
            if row is not None:
                row.status = status
                row.completed_at = datetime.now(UTC)

    def record_session_cost(self, session_seconds: float, livekit_cost: float) -> None:
        """Persist session duration + LiveKit transport cost (called at session end)."""
        with session_scope() as db:
            row = db.get(IntakeSession, self.session_id)
            if row is not None:
                row.session_seconds = session_seconds
                row.livekit_cost = livekit_cost
        log.info(
            "session_cost_recorded",
            session=self.session_id,
            seconds=round(session_seconds, 1),
            livekit_cost=livekit_cost,
        )

    def _persist_field(self, field_id: str) -> None:
        fv = self.fields[field_id]
        with session_scope() as db:
            row = (
                db.query(IntakeFieldRow)
                .filter_by(session_id=self.session_id, field_id=field_id)
                .one_or_none()
            )
            if row is None:
                row = IntakeFieldRow(session_id=self.session_id, field_id=field_id)
                db.add(row)
            row.value = fv.value
            row.confidence = fv.confidence
            row.confirmed = fv.confirmed

    # ---- derived ----
    def completion_rate(self) -> float:
        """Fraction of required fields that have a value (0.0–1.0)."""
        required = required_field_ids()
        if not required:
            return 1.0
        filled = sum(1 for fid in required if fid in self.fields)
        return filled / len(required)

    def remaining_required(self) -> list[str]:
        """Required field ids not captured yet — fed back to the LLM to avoid re-asking."""
        return [fid for fid in required_field_ids() if fid not in self.fields]

    def field_panel_payload(self, field_id: str) -> dict[str, object]:
        """A small dict for the live UI panel (label localized to the session language)."""
        fv = self.fields[field_id]
        spec = get_field(field_id)
        label = localized(spec.label, self.language) if spec else field_id
        return {
            "type": "field_update",
            "id": field_id,
            "label": label,
            "value": fv.value,
            "confirmed": fv.confirmed,
        }
