# Explainer — `backend/providers/stt_sarvam.py`

## Purpose
Wraps `livekit.plugins.sarvam.STT` (Saaras) as an `STTProvider`. POC default STT — best Indic
+ code-mix support.

## Dependencies & data in/out
- **Imports:** `providers.base` (Stage/ProviderMeter/StageBuild); `livekit.plugins.sarvam`
  lazily inside `build`.
- **In:** the `stt` stage config + short language code. **Out:** `StageBuild` (STT component +
  meter, billable unit = audio seconds).

## Walkthrough
- **`_LANG_CODES`** — maps `en/hi/mr` → Sarvam codes `en-IN/hi-IN/mr-IN`.
- **`SarvamSTTProvider.name`** = `"sarvam"`.
- **`SarvamSTTProvider.build(stage_cfg, language)`** — reads `model` (default `saaras:v3`),
  `pricing_key`, and `options`; resolves the language code; passes `mode` only when set **and**
  the model is `saaras:v3` (mode selection is v3-only); constructs `sarvam.STT(...)`; returns a
  `StageBuild` with an STT `ProviderMeter`.
- **`PROVIDER`** — module singleton registered by the registry.

## Gotchas / TODOs
- Confirm `livekit-plugins-sarvam` version + exact `STT` kwargs after install (Risk R5/R1).
- For heavy code-mix, Saaras auto-detect can be used; POC pins the UI-selected language.
