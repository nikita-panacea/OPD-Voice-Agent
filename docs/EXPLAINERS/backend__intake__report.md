# Explainer — `backend/intake/report.py`

## Purpose
Builds the clinician-facing intake report (§8.3) from the persisted fields and renders Markdown.
Both JSON and Markdown carry the disclaimer and contain **no diagnosis or treatment** — collect
and reflect only.

## Dependencies & data in/out
- **Imports:** `pydantic`, `intake.red_flags`, `intake.questions`, `store.db`, logger.
- **In:** a `session_id` (reads the DB). **Out:** an `IntakeReport`, Markdown, and a stored
  `ReportRow`.

## Walkthrough
- **`DISCLAIMER`** — the mandatory header text.
- **`HPI_FIELDS` / `SCREEN_FIELDS`** — which fields form the HPI section / get re-screened for
  red-flag mentions.
- **`ReportItem` / `IntakeReport`** — Pydantic models (HPI item; full report with identity,
  chief complaint + patient's-own-words quote, HPI, meds, allergies, histories, completion rate,
  urgent flag + red-flag categories).
- **`_load(session_id)`** — loads the `IntakeSession` + its fields (detaches the values needed
  before the DB session closes); raises `KeyError` for unknown sessions.
- **`_value(fields, id)`** — safe field-value lookup.
- **`build_report(session_id)`** — computes completion rate, re-screens free text via
  `red_flags.detect`, assembles the HPI list, and returns the `IntakeReport`.
- **`render_markdown(report)`** — doctor-facing Markdown: disclaimer first, an URGENT banner if
  flagged, metadata, chief-complaint quote, HPI bullets (✓ for confirmed), and the history
  sections (each "_Not captured._" when empty).
- **`generate_and_store(session_id)`** — build + render + upsert the `ReportRow`; returns
  (report, markdown).
- **`load_stored(session_id)`** — return the stored (json_dict, markdown) or None.

## Gotchas / TODOs
- POC builds the report deterministically (no LLM narrative) — cheap + testable. An LLM-polished
  HPI is a future enhancement (would add cost/latency + a key dependency).
- PDF rendering is deferred (Markdown only).
- Red-flag re-screen is conservative (same detector as the live backstop).
