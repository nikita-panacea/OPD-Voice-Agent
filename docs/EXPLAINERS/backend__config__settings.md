# Explainer — `backend/config/settings.py`

## Purpose
Central configuration hub. It exposes (a) a typed `Settings` object built from environment
variables / the project-root `.env`, and (b) cached loaders for the three YAML config files
(`pricing.yaml`, `pipelines.yaml`, `voices.yaml`). Every other module reads config through
this file instead of touching env vars or YAML directly, so configuration is centralized,
typed, and easy to stub in tests.

## Dependencies & data in/out
- **Imports:** `pydantic_settings` (BaseSettings), `yaml`, stdlib `pathlib`/`functools`.
- **In:** OS environment + `.env` at repo root; YAML files in `backend/config/`.
- **Out:** a `Settings` instance and parsed `dict`s for pricing/pipelines/voices.

## Walkthrough
- **`CONFIG_DIR` / `PROJECT_ROOT` / `ENV_FILE`** — module-level paths resolved from
  `__file__`. `PROJECT_ROOT` is two levels up (`config/` → `backend/` → repo root), where
  `.env` lives.
- **`class Settings(BaseSettings)`** — declares every env var as a typed field with a safe
  default (empty string for secrets, sensible defaults for app settings). `model_config`
  points at the root `.env`, is case-insensitive, and ignores unknown keys so extra env vars
  don't crash startup. Field names map to UPPER_SNAKE env vars (e.g. `livekit_url` ←
  `LIVEKIT_URL`). Includes `persist_transcript` (bool, default true) — the PHI control for
  full-transcript capture — and `min_asr_confidence` / `asr_low_confidence_limit` (the ASR
  mis-hearing gate thresholds used by `IntakeAgent`).
- **`get_settings()`** — `@lru_cache`d factory returning the process-wide singleton. Cached so
  the `.env` is read once; tests can clear the cache to inject overrides.
- **`_load_yaml(name)`** — opens a YAML file in `CONFIG_DIR` and returns the parsed dict (or
  `{}` if empty). Private helper for the three public loaders.
- **`load_pricing()` / `load_pipelines()` / `load_voices()`** — `@lru_cache`d wrappers around
  `_load_yaml` for each config file.
- **`get_pipeline(name)`** — returns one pipeline's config block from `pipelines.yaml`; raises
  `KeyError` with the list of known pipelines if the name is unknown (fail-fast on typos in
  `ACTIVE_PIPELINE`).
- **`get_voice(language)`** — returns the voice config for a language, falling back to the
  `default` voice when the language isn't configured (e.g. Marathi in the POC).

## Gotchas / TODOs
- Caches mean config edits require a process restart (or `get_settings.cache_clear()`).
- Defaults keep imports from failing when `.env` is absent (good for unit tests), but the
  worker/API will fail at connect time if real keys are missing — that's intentional.
