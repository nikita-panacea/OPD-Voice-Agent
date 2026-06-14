# Explainer — `backend/api/dashboard.py`

## Purpose
Exposes the pipeline comparison (`telemetry.compare`) over the API for a future dashboard / CSV
export. Staff-gated (reuses `require_staff` from `api/sessions.py`).

## Walkthrough
- **`compare_pipelines()`** (`GET /api/compare`) — returns `telemetry.compare.to_dicts()` (one
  row per pipeline: cost/intake, p50/p95 latency, completion).
- **`compare_pipelines_csv()`** (`GET /api/compare.csv`) — same data as `text/csv`.

## Gotchas / TODOs
- Mounted in `api/main.py`. The React cost-vs-smoothness scatter page consuming this is deferred.
