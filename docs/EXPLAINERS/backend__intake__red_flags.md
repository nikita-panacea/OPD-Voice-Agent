# Explainer — `backend/intake/red_flags.py`

## Purpose
The mandatory emergency safety backstop (§2.2). Scans every patient utterance for red-flag
phrases (en + hi + mr + romanized code-mix) and returns a match so the agent can escalate —
independently of whether the LLM chooses to. Pure Python, heavily unit-tested.

## Dependencies & data in/out
- **Imports:** stdlib only (`dataclasses`).
- **In:** an utterance + language. **Out:** a `RedFlag` (category, term, localized advice) or None.

## Walkthrough
- **`RedFlag`** — frozen dataclass `{category, term, advice}`.
- **`ESCALATION_MESSAGE`** — calm, localized "alert staff now" message spoken on escalation.
- **`RED_FLAG_TERMS`** — category → trigger phrases. Categories: chest_pain, breathing, stroke,
  severe_bleeding, anaphylaxis, loss_of_consciousness, self_harm. Each has English, Hindi +
  Marathi (Devanagari), and romanized code-mix variants. Marathi terms use short roots so
  common intensifiers (e.g. "खूप") between words still match.
- **`detect(text, language)`** — case-insensitive substring scan; returns the first match with
  the language-appropriate advice, else None.

## Gotchas / TODOs
- **Conservative by design:** no negation handling, so "no chest pain" will also trigger. This
  is intentional — over-escalation is the safe failure mode (§2.2), and the LLM path handles
  nuance. Documented tradeoff; revisit with clinician input post-POC.
- Wired in `IntakeAgent.on_user_turn_completed`, which raises the URGENT flag, notifies the UI,
  speaks `advice`, and `StopResponse`s the normal LLM turn.
- Term lists are not exhaustive — expand with clinical review before production.
