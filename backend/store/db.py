"""SQLite persistence: engine, ORM models, and a session-scope helper.

POC storage layer (SQLite for dev -> Postgres for prod, per CLAUDE.md §4). Holds four
tables that later phases populate:

  * IntakeSession  — one row per patient intake (language, pipeline, consent, urgent flag)
  * IntakeFieldRow — captured §8.1 fields (value + confidence + confirmed)
  * TelemetryRow   — per-turn counts + per-component cost + end-to-end latency (NO PHI)
  * ReportRow      — the generated JSON + Markdown report

GUARDRAIL: TelemetryRow stores counts and costs only — never clinical content (§9).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from config.settings import get_settings


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class IntakeSession(Base):
    """One patient intake session."""

    __tablename__ = "intake_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    language: Mapped[str] = mapped_column(String, default="en")
    pipeline: Mapped[str] = mapped_column(String, default="indic_quality")
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    urgent_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    urgent_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")  # active|completed|handoff
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fields: Mapped[list[IntakeFieldRow]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class IntakeFieldRow(Base):
    """A single captured intake field (clinical content — access-restricted)."""

    __tablename__ = "intake_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("intake_sessions.id"))
    field_id: Mapped[str] = mapped_column(String)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    session: Mapped[IntakeSession] = relationship(back_populates="fields")


class TelemetryRow(Base):
    """Per-turn telemetry — counts, costs, latency only. NEVER clinical content (§9)."""

    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("intake_sessions.id"))
    turn_index: Mapped[int] = mapped_column(Integer, default=0)
    pipeline: Mapped[str] = mapped_column(String, default="")
    stt_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    llm_cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    tts_characters: Mapped[int] = mapped_column(Integer, default=0)
    stt_cost: Mapped[float] = mapped_column(Float, default=0.0)
    llm_cost: Mapped[float] = mapped_column(Float, default=0.0)
    tts_cost: Mapped[float] = mapped_column(Float, default=0.0)
    e2e_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ReportRow(Base):
    """The generated clinician-facing report (JSON + Markdown)."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("intake_sessions.id"))
    json_blob: Mapped[str] = mapped_column(Text)
    markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


def _make_engine():
    """Create the SQLAlchemy engine, adding SQLite-specific connect args when needed."""
    url = get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


_engine = _make_engine()
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create all tables if they do not exist (idempotent)."""
    Base.metadata.create_all(_engine)


@contextmanager
def session_scope() -> Iterator:
    """Provide a transactional DB session; commit on success, roll back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
