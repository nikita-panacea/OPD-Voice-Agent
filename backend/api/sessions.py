"""Staff endpoints: list sessions and read a session's intake report.

Gated by a shared `STAFF_AUTH_SECRET` (sent as the `X-Staff-Secret` header). This is POC-grade
auth only — Phase 9 replaces it with real staff authentication + access control + audit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from config.settings import get_settings
from intake import report as report_mod
from store.db import IntakeSession, TranscriptRow, session_scope
from telemetry import session_summary

router = APIRouter(prefix="/api/sessions", tags=["staff"])


def require_staff(x_staff_secret: str | None = Header(default=None)) -> None:
    """Reject requests without the correct staff secret."""
    if x_staff_secret != get_settings().staff_auth_secret:
        raise HTTPException(status_code=401, detail="Invalid or missing staff secret")


@router.get("", dependencies=[Depends(require_staff)])
def list_sessions() -> list[dict]:
    """List intake sessions (metadata only — no clinical content)."""
    with session_scope() as db:
        rows = db.query(IntakeSession).order_by(IntakeSession.created_at.desc()).all()
        return [
            {
                "session_id": r.id,
                "language": r.language,
                "pipeline": r.pipeline,
                "status": r.status,
                "urgent_flag": r.urgent_flag,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@router.get("/{session_id}/report", dependencies=[Depends(require_staff)])
def get_report(session_id: str) -> dict:
    """Return the structured JSON report (generated on demand from current intake)."""
    try:
        report, _md = report_mod.generate_and_store(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session") from None
    return report.model_dump()


@router.get("/{session_id}/report.md", dependencies=[Depends(require_staff)])
def get_report_markdown(session_id: str) -> Response:
    """Return the doctor-facing Markdown report."""
    try:
        _report, markdown = report_mod.generate_and_store(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session") from None
    return Response(content=markdown, media_type="text/markdown")


@router.get("/{session_id}/summary", dependencies=[Depends(require_staff)])
def get_summary(session_id: str) -> dict:
    """Return the per-session cost/performance summary (duration, per-component usage + cost,
    completion, latency, total cost) — computed fresh from the DB."""
    try:
        return session_summary.build_summary(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown session") from None


@router.get("/{session_id}/transcript", dependencies=[Depends(require_staff)])
def get_transcript(session_id: str) -> list[dict]:
    """Return the full ordered conversation transcript (PHI — staff-gated, retention-bound)."""
    with session_scope() as db:
        rows = (
            db.query(TranscriptRow)
            .filter_by(session_id=session_id)
            .order_by(TranscriptRow.seq)
            .all()
        )
        return [
            {"seq": r.seq, "role": r.role, "text": r.text,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ]
