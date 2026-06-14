# Explainer — `backend/providers/tts_sarvam.py`

## Purpose
Wraps `livekit.plugins.sarvam.TTS` (Bulbul) as a `TTSProvider`. POC default TTS — native Indic
prosody; the agent replies in the patient's language with a language-matched voice.

## Dependencies & data in/out
- **Imports:** `config.settings.get_voice`, `providers.base`; `livekit.plugins.sarvam` lazily
  inside `build`.
- **In:** the `tts` stage config + short language code. **Out:** `StageBuild` (TTS component +
  meter, billable unit = characters).

## Walkthrough
- **`_LANG_CODES`** — maps `en/hi/mr` → `en-IN/hi-IN/mr-IN`.
- **`SarvamTTSProvider.build(stage_cfg, language)`** — reads `model` (default `bulbul:v2`),
  `pricing_key`, `options`; resolves `target_language_code` and the `speaker` from
  `voices.yaml` (`get_voice`); constructs `sarvam.TTS(model, target_language_code, speaker,
  **options)`; returns a `StageBuild` with a TTS `ProviderMeter`.
- **`PROVIDER`** — module singleton.

## Gotchas / TODOs
- Bulbul speaker IDs are version-specific — verify the `voices.yaml` speakers against the
  installed plugin (Risk R5).
- `options` can carry `pace`/`pitch`/`loudness`; none set in the POC.
