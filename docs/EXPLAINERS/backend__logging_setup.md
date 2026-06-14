# Explainer — `backend/logging_setup.py`

## Purpose
Configures structured logging (structlog) once per process and hands out bound loggers.
Centralizing this enforces a consistent, machine-parseable log format and the §2.4/§9
guardrail: **no raw PHI in logs**.

## Dependencies & data in/out
- **Imports:** stdlib `logging`, `structlog`, `config.settings.get_settings` (for `LOG_LEVEL`).
- **In:** the configured log level. **Out:** configured global logging + logger instances.

## Walkthrough
- **`configure_logging()`** — reads `LOG_LEVEL`, sets up stdlib `logging.basicConfig`, then
  configures structlog with a processor chain: merge contextvars → add level → ISO timestamp →
  stack/exception rendering → console renderer. Uses a filtering bound logger for the level and
  caches loggers on first use. Call exactly once at worker/API startup.
- **`get_logger(name)`** — thin wrapper over `structlog.get_logger` returning a bound logger
  for a module.

## Gotchas / TODOs
- Currently uses `ConsoleRenderer` (human-readable). For production, swap to
  `JSONRenderer` for log aggregation.
- The "no PHI" rule is a convention enforced by code review — log counts/ids/costs, never
  transcript or field text.
