# Explainer — `backend/providers/llm_gemini.py`

## Purpose
Wraps `livekit.plugins.google.LLM` (Gemini) as an `LLMProvider` for the low_cost /
global_quality pipelines. Gemini 2.5 Flash / Flash-Lite are low-cost, tool-calling intake
brains.

## Walkthrough
- **`GeminiLLMProvider.build(stage_cfg, language)`** — reads `model` (default
  `gemini-2.5-flash`), `pricing_key`, `options`; constructs `google.LLM(model=..., **options)`;
  returns a `StageBuild` with an LLM meter (billable units = input/output tokens). Reads
  `GOOGLE_API_KEY` from env. Language is prompt-driven.

## Gotchas / TODOs
- Tool-calling for `save_intake_field` works on Gemini; if a model variant misbehaves on tools,
  switch the `model` in `pipelines.yaml`.
- Verified constructor kwargs against livekit-plugins-google 1.6.0 (2026-06-14).
