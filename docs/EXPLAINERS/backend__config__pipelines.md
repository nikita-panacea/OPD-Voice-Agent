# Explainer — `backend/config/pipelines.yaml`

## Purpose
Named STT/LLM/TTS triples. "A pipeline is a named triple" (CLAUDE.md §6) — switching pipelines
is a config change, not a code change. Read by `providers/registry.py` to build an
`AgentSession`.

## Structure
- `active_default` — pipeline used when `ACTIVE_PIPELINE` isn't set.
- `pipelines:` map. Each pipeline has `stt` / `llm` / `tts` blocks; each block names a
  `provider` (must match a builder in the registry), a `model`, a `pricing_key` (→
  `pricing.yaml`), and free-form `options` passed to the provider wrapper.
- Pipelines: `indic_quality` (default), `global_stack`, `low_cost`, `global_quality`,
  `translate_bridge`, `whisper_eval`, and the Whisper+Sarvam cost-comparison combos
  `whisper_sarvam_nano` / `_mini` / `_gemini` (Whisper STT → {GPT-4.1 nano | mini |
  Gemini 2.5 Flash} → Sarvam Bulbul). Switch live with `ACTIVE_PIPELINE`.

## Gotchas / TODOs
- `translate_bridge` sets STT `options.mode: translate` (Saaras v3 emits English) — a strategy
  flag, measured not defaulted.
- Adding a pipeline that names a provider without a registered builder will fail fast in the
  registry (intended).
