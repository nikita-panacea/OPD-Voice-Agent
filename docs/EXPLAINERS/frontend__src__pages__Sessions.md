# Explainer — `frontend/src/pages/Sessions.tsx`

## Purpose
The staff view: enter the staff secret, browse intake sessions, and inspect each one across three
sub-tabs — **Report** (doctor-facing Markdown), **Summary & cost** (per-component usage + cost
breakdown + metrics), and **Transcript** (full conversation). PHI — authorized staff only.

## Dependencies & data in/out
- **Imports:** `lib/staff` (listSessions/getReportMarkdown/getSummary/getTranscript + types).

## Walkthrough
- **`Sessions()`** — holds the staff `secret` (persisted in `localStorage`), the `sessions` list,
  the `selected` session, the active `tab`, and per-tab data + loading/error.
  - `loadSessions()` — saves the secret + fetches the session list.
  - a `useEffect` lazily loads the active tab's data whenever the selection/tab changes (with a
    `cancelled` guard to avoid races).
  - Left pane: clickable session list (id, language·pipeline·status, 🚨 if urgent).
  - Right pane: tab bar + content — report in a monospace `<pre>`, `SummaryView`, or
    `TranscriptList`.
- **`SummaryView`** — metric chips (duration, turns, completion, latency, **total cost**, urgent)
  + a cost table (STT/LLM/TTS/LiveKit usage + cost, with a Total row).
- **`Metric` / `TranscriptList`** — small presentational helpers (Patient/Dhara bubbles).

## Gotchas / TODOs
- Report is shown as raw Markdown text (no Markdown renderer, to keep deps light).
- Selecting a session + switching tabs refetches; data is always fresh from the DB.
