# Explainer — `backend/providers/llm_openai.py`

## Purpose
Wraps `livekit.plugins.openai.LLM` as an `LLMProvider`. POC default intake brain (GPT-4.1) —
strong instruction-following + tool-calling for `save_intake_field`.

## Dependencies & data in/out
- **Imports:** `providers.base`; `livekit.plugins.openai` lazily inside `build`.
- **In:** the `llm` stage config. **Out:** `StageBuild` (LLM component + meter, billable units =
  input/output tokens).

## Walkthrough
- **`OpenAILLMProvider.name`** = `"openai"`.
- **`build(stage_cfg, language)`** — reads `model` (default `gpt-4.1`), `pricing_key`,
  `options`; constructs `openai.LLM(model=..., **options)`; returns a `StageBuild` with an LLM
  `ProviderMeter`. Language is handled by prompts, not here.
- **`PROVIDER`** — module singleton.

## Gotchas / TODOs
- Swapping to Gemini = change `provider`/`model` in `pipelines.yaml` once `llm_gemini` is added
  (deferred).
- Prompt caching reduces input-token cost on the repeated system prompt; the meter captures
  cached tokens when the metrics object exposes them.
