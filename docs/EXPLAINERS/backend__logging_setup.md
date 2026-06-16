# Explainer — `backend/logging_setup.py`

## Purpose
Configures structured logging (structlog) once per process and hands out bound loggers.
Centralizing this enforces a consistent, machine-parseable log format and the §2.4/§9
guardrail: **no raw PHI in logs**.

## Dependencies & data in/out
- **Imports:** stdlib `logging`, `structlog`, `config.settings.get_settings` (for `LOG_LEVEL`).
- **In:** the configured log level. **Out:** configured global logging + logger instances.

## Walkthrough
- **`configure_logging(log_name="app")`** — reads `LOG_LEVEL`; routes structlog through stdlib
  via `ProcessorFormatter` so two handlers can render the same events differently:
  - **console** — human-readable `ConsoleRenderer` (terminal).
  - **file** — `backend/logs/<log_name>.jsonl`, `JSONRenderer`, `RotatingFileHandler`
    (10 MB × 5). Wrapped in try/except so a filesystem problem never breaks the app.
  The worker calls `configure_logging("agent")`, the API `configure_logging("api")`, so the two
  processes write separate files (no cross-process contention). Replaces root handlers each call
  (safe under uvicorn reload).
- **`get_logger(name)`** — thin wrapper over `structlog.get_logger`.

## Gotchas / TODOs
- The "no PHI" rule is a convention enforced by code review — log counts/ids/costs, never
  transcript or field text (transcript text lives only in the `transcripts` table).
- `logs/` is git-ignored; keep it out of OneDrive sync to avoid rotation/lock issues.
