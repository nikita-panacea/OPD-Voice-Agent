# Explainer — `backend/telemetry/compare.py`

## Purpose
The cost-vs-performance comparison across pipelines (§9.4). Aggregates the per-turn `telemetry`
rows (tagged by pipeline) + captured fields into one summary per pipeline: sessions, turns,
**median/avg cost per intake**, **p50/p95 end-to-end latency**, **avg completion rate**. This is
the artifact for "which pipeline for production?". Pure DB reads — no clinical content.

## Dependencies & data in/out
- **Imports:** `intake.questions.required_field_ids`, `store.db` (TelemetryRow / IntakeSession /
  IntakeFieldRow / session_scope).
- **Out:** `list[PipelineStats]`, dicts (API), CSV, or a text table (CLI).

## Walkthrough
- **`PipelineStats`** — dataclass with the per-pipeline metrics.
- **`_percentile(values, pct)`** — nearest-rank percentile (None if empty).
- **`_median(values)`** — median (0.0 if empty).
- **`aggregate()`** — loads telemetry + sessions + fields; computes per-session cost
  (Σ stt+llm+tts over its turns) grouped by pipeline; gathers all turn latencies; computes
  completion per session (filled required ÷ required); returns stats sorted by median
  cost/intake (cheapest first).
- **`to_dicts()` / `to_csv()`** — serializations for the API / spreadsheet export.
- **`format_table()`** — human-readable CLI table.
- **`_main()`** — `init_db()` then print the table (or CSV with `--csv`).

## Usage
- API: `GET /api/compare` and `GET /api/compare.csv` (staff-gated, see `api/dashboard.py`).
- CLI: `python -m telemetry.compare` / `python -m telemetry.compare --csv` (from `backend/`).

## Gotchas / TODOs
- Live comparison = run sessions under each `ACTIVE_PIPELINE`, then aggregate — this carries
  patient-to-patient variance. The **offline replay harness** (identical input per pipeline,
  CLAUDE.md §9.5) and the React scatter dashboard remain deferred; this module is their data
  source.
- Cost accuracy depends on `pricing.yaml` (ElevenLabs $/char is an estimate).
