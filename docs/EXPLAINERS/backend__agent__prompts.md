# Explainer — `backend/agent/prompts.py`

## Purpose
Builds the system prompt for the intake brain: persona, the §2 guardrails, the consent script,
behavior rules (one question at a time, read-back, clarification), and the localized field
checklist. The guardrails appear here AND as code paths (consent gate + tools + red_flags).

## Dependencies & data in/out
- **Imports:** `intake.questions` (`INTAKE_FIELDS`, `localized`).
- **In:** language code. **Out:** the full instruction string + a greeting instruction.

## Walkthrough
- **`PERSONA`** — "Dhara", a warm, **female** automated OPD assistant; short, plain, patient.
  Instructs feminine grammatical self-forms in Hindi/Marathi (e.g. "करती हूँ" / "करते").
- **anti-repetition rule** in `BEHAVIOR` — capture volunteered info immediately, skip already-
  captured fields, and ask only what the tool reports as "Still needed".
- **`GUARDRAILS`** — the absolute rules: not a doctor, no diagnosis/advice, red-flag → stop +
  `flag_urgent`, consent first, brevity.
- **`CONSENT_SCRIPT`** — per-language consent framing (en/hi/mr); `LANGUAGE_NAMES` maps the
  short code to the spoken language name ("English"/"Hindi"/"Marathi").
- **`BEHAVIOR`** — how to run the intake: one field at a time, adapt order, call
  `save_intake_field`, read-back + `confirm_field` for critical fields, clarify with the simpler
  prompt + example, ask to repeat when unsure, `complete_intake` at the end.
- **`_checklist(language)`** — renders each field (id, type, tags, localized ask + simpler
  re-ask) into the prompt.
  - Includes a **mishearing/sense-check rule**: STT can return wrong/homophone words, so the
    agent must check each answer is coherent + plausible for the question before saving, and
    confirm/repeat on doubt (never assume garbled text is correct).
- **`build_instructions(language)`** — assembles persona + "speak only in <lang>" + guardrails +
  consent + behavior + checklist.
- **`greeting_instructions(language)`** — instruction for the first spoken turn (greet + consent).
- **`repeat_request(language)` / `low_confidence_handoff(language)`** — localized (en/hi/mr)
  spoken lines the agent's ASR-confidence gate uses (deterministic, not LLM-generated).

## Gotchas / TODOs
- Prompt is ~6KB; sent each turn → prompt caching (OpenAI `prompt_cache_key`) matters for cost.
- Clarification quality depends on the LLM following instructions; the deterministic red-flag
  backstop (Phase E) does not depend on the prompt.
