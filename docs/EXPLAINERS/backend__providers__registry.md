# Explainer — `backend/providers/registry.py`

## Purpose
The factory that turns a named pipeline into a runnable `AgentSession`. Holds the
name → builder tables and assembles STT/LLM/TTS + Silero VAD + MultilingualModel turn
detection + Krisp BVC. This is what makes "swap a provider = edit YAML" true.

## Dependencies & data in/out
- **Imports:** `config.settings.get_pipeline`, the three wrapper modules, `base` types,
  logger. LiveKit (`AgentSession`, `silero`, `MultilingualModel`, `noise_cancellation`) is
  imported lazily inside `build_session`/`_load_krisp`.
- **In:** pipeline name + language. **Out:** a `BuiltSession`.

## Walkthrough
- **`STT_PROVIDERS` / `LLM_PROVIDERS` / `TTS_PROVIDERS`** — dicts of provider name → builder
  singleton. Registered: STT = sarvam/deepgram/whisper; LLM = openai/google; TTS =
  sarvam/elevenlabs — covering all comparison pipelines in `pipelines.yaml`.
- **`BuiltSession`** — dataclass returned to the worker: the `AgentSession`, the per-stage
  `meters` dict, the `noise_cancellation` component, and the resolved `pipeline`/`language`.
- **`_resolve(table, stage_cfg, stage)`** — looks up a stage's provider; raises a descriptive
  `KeyError` listing registered providers if it's missing (deferred providers fail fast).
- **`_load_krisp()`** — returns `noise_cancellation.BVC()`; on any failure (plugin missing /
  not on Cloud) logs a warning and returns `None` so the session still runs without NC.
- **`build_session(pipeline_name, language)`** — fetches the pipeline config, builds each stage
  via its resolved provider, lazily imports LiveKit, constructs the `AgentSession` (stt/llm/tts
  + `silero.VAD.load()` + `MultilingualModel()`), logs the wiring, and returns a `BuiltSession`
  with meters + noise cancellation.

## Gotchas / TODOs
- The worker applies `noise_cancellation` via `RoomInputOptions` at `session.start` (it isn't
  an `AgentSession` ctor arg).
- `silero.VAD.load()` / `MultilingualModel()` need their model files downloaded once
  (`python -m agent.worker download-files`).
- `MultilingualModel` has no Marathi — fine for the POC (en/hi); revisit for Marathi.
