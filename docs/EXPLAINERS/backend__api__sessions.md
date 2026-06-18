# Explainer — `backend/api/sessions.py`

## Purpose
Staff-facing read endpoints: list sessions and fetch a session's intake report (JSON + Markdown).
Gated by a shared `STAFF_AUTH_SECRET` (POC-grade auth).

## Dependencies & data in/out
- **Imports:** `fastapi`, `config.settings`, `intake.report`, `store.db`.

## Walkthrough
- **`require_staff(x_staff_secret)`** — FastAPI dependency; 401 unless the `X-Staff-Secret`
  header matches `STAFF_AUTH_SECRET`.
- **`list_sessions()`** (`GET /api/sessions`) — metadata only (id, language, pipeline, status,
  urgent flag, created_at) — **no clinical content** in the list.
- **`get_report(session_id)`** (`GET /api/sessions/{id}/report`) — `generate_and_store` then
  return the structured JSON; 404 for unknown sessions.
- **`get_report_markdown(session_id)`** (`GET /api/sessions/{id}/report.md`) — same, returned as
  `text/markdown`.
- **`get_summary(session_id)`** (`GET /api/sessions/{id}/summary`) — the per-session
  cost/performance summary (`session_summary.build_summary`): duration, per-component usage +
  cost breakdown, total cost, completion, latency, transcript. Powers the staff UI's Summary tab.
- **`get_transcript(session_id)`** (`GET /api/sessions/{id}/transcript`) — the full ordered
  conversation (seq/role/text). **PHI** — staff-gated, retention-bound.

## Gotchas / TODOs
- Shared-secret auth is POC-only; Phase 9 replaces it with real staff auth + access control +
  audit logging.
- Reports are generated on demand from current intake state, so they always reflect the latest
  captured fields.
