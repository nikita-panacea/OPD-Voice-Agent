"""Structured logging configuration (structlog).

Call `configure_logging()` once at process start (worker, API). All modules then use
`structlog.get_logger(__name__)`. Logs are JSON-ish key/value events so cost/telemetry
and flow events are machine-parseable.

GUARDRAIL (CLAUDE.md §2.4 / §9): never log raw PHI. Log identifiers, counts, costs, and
flow events — never transcript text, field values, or clinical content.
"""

from __future__ import annotations

import logging

import structlog

from config.settings import get_settings


def configure_logging() -> None:
    """Configure stdlib logging + structlog with a consistent processor chain."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(format="%(message)s", level=level)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
