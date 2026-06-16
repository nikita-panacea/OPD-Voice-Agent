# Explainer — `backend/intake/transcript.py`

## Purpose
Persists the **full conversation transcript** (patient + agent turns) to the `transcripts`
table by subscribing to the AgentSession's `conversation_item_added` event.

## PHI note
The transcript is verbatim clinical content — the most sensitive data in the system. It is
access-restricted (staff endpoint), retention-bound (`DATA_RETENTION_DAYS`), and capture can be
disabled with `PERSIST_TRANSCRIPT=false`. Transcript text is **never** written to logs or
telemetry (we log role + length only).

## Dependencies & data in/out
- **Imports:** `logging_setup`, `store.db` (TranscriptRow / session_scope).
- **In:** `ConversationItemAddedEvent` (`.item` = ChatMessage with `role` + `text_content`).
  **Out:** rows in the `transcripts` table.

## Walkthrough
- **`_ROLE_MAP`** — maps LiveKit roles `user`→`patient`, `assistant`→`agent`; other roles
  (system/tool) are skipped.
- **`record_utterance(session_id, role, text, seq)`** — pure helper; persists one non-empty
  utterance (unit-tested).
- **`TranscriptRecorder`** — `attach(session)` subscribes to `conversation_item_added`;
  `_on_item(ev)` maps the role, skips empty/system items, persists via `record_utterance`,
  increments an internal `seq`, and logs metadata only.

## Gotchas / TODOs
- Wired in the worker only when `settings.persist_transcript` is true.
- Captures finalized conversation items (not interim partials).
- Read it via `GET /api/sessions/{id}/transcript` (staff-gated).
