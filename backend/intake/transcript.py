"""Full conversation transcript persistence.

Subscribes to the `AgentSession` `conversation_item_added` event and writes every patient/agent
utterance to the `transcripts` table, in order.

PHI WARNING (CLAUDE.md §2.4 / §9): the transcript is verbatim clinical content — the most
sensitive data in the system. It is access-restricted (staff endpoint), retention-bound
(DATA_RETENTION_DAYS), and capture can be disabled entirely via `PERSIST_TRANSCRIPT=false`.
Never copy transcript text into telemetry or logs (we log role + length only).
"""

from __future__ import annotations

from logging_setup import get_logger
from store.db import TranscriptRow, session_scope

log = get_logger(__name__)

# LiveKit ChatMessage roles -> our transcript roles. Other roles (system/tool) are skipped.
_ROLE_MAP = {"user": "patient", "assistant": "agent"}


def record_utterance(session_id: str, role: str, text: str, seq: int) -> None:
    """Persist one utterance to the transcripts table (pure helper, unit-testable)."""
    if not text or not text.strip():
        return
    with session_scope() as db:
        db.add(TranscriptRow(session_id=session_id, seq=seq, role=role, text=text))


class TranscriptRecorder:
    """Attaches to an AgentSession and records the full conversation transcript."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._seq = 0

    def attach(self, agent_session) -> None:
        """Subscribe to conversation items (both patient and agent turns)."""
        agent_session.on("conversation_item_added", self._on_item)

    def _on_item(self, ev) -> None:
        item = getattr(ev, "item", None)
        if item is None:
            return
        role = _ROLE_MAP.get(getattr(item, "role", ""))
        if role is None:
            return  # skip system/tool messages
        text = getattr(item, "text_content", None) or ""
        if not text.strip():
            return
        record_utterance(self.session_id, role, text, self._seq)
        # Log metadata only — never the transcript text itself (§9).
        log.info(
            "transcript_item", session=self.session_id, seq=self._seq, role=role, chars=len(text)
        )
        self._seq += 1
