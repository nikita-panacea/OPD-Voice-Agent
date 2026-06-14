# Explainer — `backend/intake/questions.py`

## Purpose
The §8.1 intake field schema — the goal-driven checklist the agent fills. Pure data + helpers
(no LiveKit), so it's unit-testable and reusable by prompts, state, and the report.

## Dependencies & data in/out
- **Imports:** `enum.StrEnum`, `pydantic`.
- **Out:** `INTAKE_FIELDS` (the 17-field list) + lookup helpers.

## Walkthrough
- **`FieldType`** — StrEnum: `free_text`, `scale_0_10`, `yes_no`, `enum`, `list`.
- **`IntakeField`** (Pydantic) — `id`, `ftype`, `required`, `critical` (read-back),
  `is_consent_gate`, `red_flag_check`, `needs_clinical_review`, plus per-language `label`,
  `prompt`, `simpler_prompt` dicts and optional `enum_options`.
- **`localized(d, language)`** — returns the language variant, falling back to English (this is
  how Marathi/any-missing language degrades safely).
- **`INTAKE_FIELDS`** — the 17 fields (consent gate → identity → complaint loop → history →
  additional). English canonical; Hindi authored + `needs_clinical_review=True`. Critical
  fields: chief_complaint, medications, allergies. Red-flag-screen fields: associated_symptoms,
  allergies.
- **`get_field(id)` / `required_field_ids()` / `critical_field_ids()`** — lookups used by
  prompts (checklist), state (completion rate), and the agent (read-back gating).

## Gotchas / TODOs
- Hindi strings are machine-authored — must be clinician-reviewed before real use (§7).
- Marathi prompts intentionally absent (deferred); `localized` falls back to English.
- The whole set is flagged `needs_clinical_review` per the POC decision.
