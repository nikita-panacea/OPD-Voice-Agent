# Explainer — `backend/store/db.py`

## Purpose
The persistence layer. Defines the SQLAlchemy engine, the four ORM tables the POC needs, and
a transactional `session_scope()` context manager. SQLite for dev (→ Postgres for prod).

## Dependencies & data in/out
- **Imports:** SQLAlchemy 2.x (`create_engine`, typed `Mapped`/`mapped_column`,
  `DeclarativeBase`, `sessionmaker`, `relationship`); `config.settings.get_settings` for the
  `DATABASE_URL`.
- **In:** rows written by intake state (Phase D), telemetry (Phase F), and report (Phase G).
- **Out:** persisted intake sessions/fields/telemetry/reports; read back by the staff API.

## Walkthrough
- **`_utcnow()`** — timezone-aware UTC timestamp used as the default for all `created_at` /
  `updated_at` columns.
- **`class Base(DeclarativeBase)`** — the declarative base all models inherit from; its
  `metadata` drives `create_all`.
- **`IntakeSession`** — one row per intake: `id`, `language`, `pipeline`, `consent_given`,
  `urgent_flag` + `urgent_reason` (red-flag escalation), `status` (active/completed/handoff),
  timestamps. Has a cascade `relationship` to its fields.
- **`IntakeFieldRow`** — a captured §8.1 field: `field_id`, `value`, `confidence`,
  `confirmed`, `updated_at`. This is clinical content (access-restricted).
- **`TelemetryRow`** — per-turn metrics: STT seconds, LLM in/out/cached tokens, TTS chars,
  per-component costs, end-to-end latency. **Contains no clinical content** by design (§9).
- **`ReportRow`** — the generated report stored as both `json_blob` and `markdown`.
- **`_make_engine()`** — builds the engine from `DATABASE_URL`, adding
  `check_same_thread=False` for SQLite so the async agent worker and the API can share it.
- **`_engine` / `SessionLocal`** — module-level engine + session factory
  (`expire_on_commit=False` so objects stay usable after commit).
- **`init_db()`** — idempotently creates all tables; called at API/worker startup.
- **`session_scope()`** — `@contextmanager` yielding a DB session that commits on success and
  rolls back on any exception, always closing the session. The standard way callers touch the
  DB.

## Gotchas / TODOs
- SQLite is single-file dev storage; concurrent writers are limited — fine for the POC.
- No encryption at rest / retention job / access control yet — deferred to Phase 9; required
  before real PHI (CLAUDE.md §2.4).
- Field values store clinical content; keep them out of logs and telemetry.
