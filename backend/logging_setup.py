"""Structured logging (structlog) → human console + rotating JSON-lines file.

`configure_logging(log_name)` sets up two sinks:
  * console — human-readable (ConsoleRenderer), for the terminal.
  * file    — `backend/logs/<log_name>.jsonl`, machine-parseable JSON lines, rotated.

The worker uses `log_name="agent"` and the API `log_name="api"` so the two processes write
separate files (no cross-process file contention). All modules then use
`structlog.get_logger(__name__)`.

GUARDRAIL (§2.4 / §9): never log raw PHI. Log identifiers, counts, costs, and flow events —
never transcript text, field values, or clinical content. (The transcript table is the only
place verbatim conversation is stored.)
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import structlog

from config.settings import get_settings

LOG_DIR = Path(__file__).resolve().parent / "logs"
_MAX_BYTES = 10_000_000  # 10 MB per file
_BACKUP_COUNT = 5


def configure_logging(log_name: str = "app") -> None:
    """Configure structlog with a console renderer + a rotating JSONL file handler."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # structlog logs are routed through stdlib so multiple handlers (console + file) can render
    # them differently.
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    handlers: list[logging.Handler] = []

    console = logging.StreamHandler()
    console.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(),
            ],
        )
    )
    handlers.append(console)

    # Rotating JSON-lines file. If the file can't be opened (permissions), fall back to console.
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / f"{log_name}.jsonl",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared_processors,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
            )
        )
        handlers.append(file_handler)
    except OSError as exc:  # pragma: no cover - filesystem dependent
        # Never let file-logging problems break the app; console logging still works.
        print(f"[logging_setup] file logging disabled: {exc}")

    root = logging.getLogger()
    root.handlers[:] = handlers  # replace (avoids duplicates on uvicorn reload)
    root.setLevel(level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
