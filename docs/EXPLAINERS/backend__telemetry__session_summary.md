# Explainer — `backend/telemetry/session_summary.py`

## Purpose
The POC observability artifact: a per-session **cost + performance** rollup written to
`backend/logs/sessions/<session_id>.json` and `.md`. Aggregates duration, per-component usage
(STT seconds, LLM in/out/cached tokens, TTS characters, LiveKit minutes) with a **cost breakdown
+ total**, completion rate, median latency, and the **full transcript** — everything needed to
analyze the pipeline's cost & performance for one intake.

## PHI note
The files include the verbatim transcript (clinical content) — same access/retention rules as
the DB; keep `logs/` out of un-controlled sync/backup.

## Dependencies & data in/out
- **Imports:** `config.settings.get_pipeline`, `intake.questions.required_field_ids`, `store.db`
  (IntakeSession / TelemetryRow / IntakeFieldRow / TranscriptRow), logger.
- **In:** a `session_id` (reads the DB). **Out:** a summary dict + JSON/MD files.

## Walkthrough
- **`build_summary(session_id)`** — loads the session row + its telemetry/fields/transcript;
  sums per-component usage and cost; reads `session_seconds`/`livekit_cost` from the session row;
  resolves each stage's `provider/model` from the pipeline config; computes completion rate and
  median e2e latency; returns a nested dict incl. `total_cost_usd` and the transcript.
- **`_render_markdown(summary)`** — a human-readable report: metadata, a cost/usage table
  (per component + total), and the transcript (patient / Dhara).
- **`write_session_files(session_id)`** — writes `<id>.json` + `<id>.md` to `logs/sessions/`,
  logs a `session_summary_written` event (cost/turns/duration, no PHI), returns the JSON path.

## Gotchas / TODOs
- Called from the worker's shutdown callback **after** `meter.close()` + `record_session_cost`,
  so it sees the final telemetry + LiveKit cost.
- Per-component `cost_usd` reflects the cached-token discount (computed upstream in the meter).
- Cross-session rollups live in `telemetry/compare.py` / `GET /api/compare`; this is the
  per-session detail.
