# Explainer — `backend/providers/tts_elevenlabs.py`

## Purpose
Wraps `livekit.plugins.elevenlabs.TTS` as a `TTSProvider` for the global_stack / global_quality
pipelines. Flash v2.5 (`eleven_flash_v2_5`) = low-latency, multilingual (incl. Hindi).

## Walkthrough
- **`_LANG_CODES`** — `en/hi/mr` passthrough.
- **`ElevenLabsTTSProvider.build(stage_cfg, language)`** — reads `model` (default
  `eleven_flash_v2_5`), `pricing_key`, `options`; optional `options.voice_id`; passes `language`
  for text normalization; constructs `elevenlabs.TTS(...)`; returns a `StageBuild` with a TTS
  meter (billable unit = characters).

## Gotchas / TODOs
- **API key naming:** the plugin reads `ELEVEN_API_KEY`, but we standardize on
  `ELEVENLABS_API_KEY` in `.env` — the wrapper injects it explicitly via `get_settings()`.
- Default voice is the plugin default; set `options.voice_id` for a specific voice.
- ElevenLabs $/char is plan-dependent — `pricing.yaml` carries an estimate (replace with your
  plan's rate before trusting cost numbers).
