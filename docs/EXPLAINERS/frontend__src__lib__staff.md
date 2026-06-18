# Explainer — `frontend/src/lib/staff.ts`

## Purpose
Typed client for the staff-gated API (sessions list, report Markdown, per-session summary,
transcript). Every call sends the shared `X-Staff-Secret` header.

## Dependencies & data in/out
- **In:** the staff secret + a session id. **Out:** typed results (`SessionRow[]`,
  `SessionSummary`, `TranscriptTurn[]`, report Markdown string).

## Walkthrough
- **Types** — `SessionRow`, `TranscriptTurn`, `ComponentUsage`, `SessionSummary` mirror the
  backend JSON (`telemetry/session_summary.build_summary` + the sessions endpoints).
- **`staffGet(path, secret)`** — fetch helper that adds the secret header and throws a friendly
  error on 401 ("Invalid staff secret") / other non-OK.
- **`listSessions` / `getReportMarkdown` / `getSummary` / `getTranscript`** — one call per staff
  endpoint; `getReportMarkdown` returns text, the others JSON.

## Gotchas / TODOs
- Uses `VITE_API_BASE` (defaults to `http://localhost:8000`).
- POC auth is a shared secret typed into the UI; Phase 9 replaces it with real staff auth.
