# Explainer — `backend/intake/state.py`

## Purpose
The live per-session intake state and its write-through persistence to SQLite. The agent
mutates this object as it learns answers; every change hits the DB so partial progress survives
a dropped call and the report generator can read a finished session.

## Dependencies & data in/out
- **Imports:** `intake.questions` (field specs/helpers), `store.db` (ORM + session_scope), logger.
- **In:** field saves/confirms/consent/urgent from the agent. **Out:** persisted rows + small
  UI payloads.

## Walkthrough
- **`FieldValue`** — dataclass `{value, confidence, confirmed}`.
- **`IntakeState`** — dataclass: `session_id`, `language`, `pipeline`, `consent_given`,
  `urgent_flag`/`urgent_reason`, and `fields: {id -> FieldValue}`.
  - **`persist_session()`** — insert/update the `IntakeSession` row (call once at start).
  - **`set_consent(granted)`** — record consent in memory + DB (the gate).
  - **`save_field(id, value, confidence)`** — upsert a field, preserving an existing `confirmed`
    flag; write through via `_persist_field`.
  - **`confirm_field(id)`** — mark a critical field confirmed (post read-back).
  - **`raise_urgent(reason)`** — set the URGENT flag in memory + DB (logged at warning).
  - **`finalize(status)`** — set status + `completed_at`.
  - **`_persist_field(id)`** — upsert the `IntakeFieldRow` (query by session+field).
  - **`completion_rate()`** — filled required ÷ total required (0–1); feeds telemetry/smoothness.
  - **`field_panel_payload(id)`** — small dict (localized label) pushed to the live UI panel.

## Gotchas / TODOs
- `save_field` itself does not enforce the consent gate — the agent tool does, before calling
  it (kept here as pure persistence). Tested in `tests/test_state.py`.
- Field values are clinical content: never log them (logs carry ids + confidence only).
