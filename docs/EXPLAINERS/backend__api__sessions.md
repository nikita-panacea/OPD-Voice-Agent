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

## Gotchas / TODOs
- Shared-secret auth is POC-only; Phase 9 replaces it with real staff auth + access control +
  audit logging.
- Reports are generated on demand from current intake state, so they always reflect the latest
  captured fields.
