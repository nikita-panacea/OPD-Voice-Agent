# Explainer — `backend/config/voices.yaml`

## Purpose
Per-language TTS voice IDs. The agent replies in the patient's language with a language-matched
voice. Read via `config.settings.get_voice(language)`; passed by the registry into the TTS
wrapper.

## Structure
- `provider` / `model` — the TTS engine these voices belong to (Sarvam Bulbul for the POC).
- `voices:` map of language → `{ speaker: ... }` (`en`, `hi`, `mr`).
- `default:` fallback voice used for any language not listed.

## Gotchas / TODOs
- Sarvam Bulbul speaker IDs can change between model versions — verify the exact speaker names
  against the Sarvam plugin/docs at build (Risk R5).
- Bulbul voices are multilingual across Indic languages, so one speaker serves en/hi/mr
  (the TTS wrapper sets `target_language_code` per language, e.g. `mr-IN`).
