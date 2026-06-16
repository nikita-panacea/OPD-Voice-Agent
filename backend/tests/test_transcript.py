"""Tests for full-transcript persistence (record helper + recorder role mapping)."""

import uuid

import pytest

from intake.transcript import TranscriptRecorder, record_utterance
from store.db import TranscriptRow, init_db, session_scope


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def test_record_utterance_persists_and_skips_empty() -> None:
    sid = f"t-{uuid.uuid4().hex[:8]}"
    record_utterance(sid, "patient", "I have a fever", 0)
    record_utterance(sid, "agent", "Since when?", 1)
    record_utterance(sid, "patient", "   ", 2)  # blank -> skipped
    with session_scope() as db:
        rows = db.query(TranscriptRow).filter_by(session_id=sid).order_by(TranscriptRow.seq).all()
        assert [(r.role, r.text) for r in rows] == [
            ("patient", "I have a fever"),
            ("agent", "Since when?"),
        ]


class _Item:
    def __init__(self, role: str, text: str) -> None:
        self.role = role
        self.text_content = text


class _Ev:
    def __init__(self, item: _Item) -> None:
        self.item = item


def test_recorder_maps_roles_and_skips_system() -> None:
    sid = f"t-{uuid.uuid4().hex[:8]}"
    rec = TranscriptRecorder(sid)
    rec._on_item(_Ev(_Item("user", "hello")))
    rec._on_item(_Ev(_Item("assistant", "Hi, I'm Dhara.")))
    rec._on_item(_Ev(_Item("system", "you are an assistant")))  # skipped
    with session_scope() as db:
        rows = db.query(TranscriptRow).filter_by(session_id=sid).order_by(TranscriptRow.seq).all()
        assert [r.role for r in rows] == ["patient", "agent"]
        assert rows[0].text == "hello"
        assert [r.seq for r in rows] == [0, 1]
