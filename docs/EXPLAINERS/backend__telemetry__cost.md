# Explainer — `backend/telemetry/cost.py`

## Purpose
Cost math (§9.2): billable units × dated unit prices from `pricing.yaml`. Data-driven so price
updates never touch code and sessions can be re-costed. Pure Python, unit-tested.

## Dependencies & data in/out
- **Imports:** `config.settings.load_pricing`, logger.
- **In:** units + a `pricing_key`. **Out:** USD cost (float).

## Walkthrough
- **`_price(section, pricing_key, unit_field)`** — looks up the unit price in the pricing YAML;
  warns + returns 0.0 if the entry or field is missing/null.
- **`_cached_input_price(pricing_key, default)`** — returns `usd_per_1m_cached_input` for an LLM,
  silently falling back to `default` (the full input price) when the field is absent. No warning
  — caching pricing is optional per model.
- **`stt_cost(seconds, key)`** — seconds × usd_per_second.
- **`llm_cost(input_tokens, output_tokens, key, cached_tokens=0)`** — applies the prompt-cache
  discount: `cached_tokens` (a subset of `input_tokens`, clamped) is billed at the cached rate,
  the remaining fresh input at the full rate, plus output. `cached_tokens=0` reproduces the
  no-caching cost (back-compatible with callers/tests that omit it).
- **`tts_cost(characters, key)`** — characters × usd_per_character.

## Gotchas / TODOs
- Null prices (Sarvam LLM, ElevenLabs $/char) → 0.0 with a warning; fill them before costing
  those providers.
- The meter passes `cached_tokens=units.llm_cached_tokens` (from LiveKit `prompt_cached_tokens`),
  so `/api/compare` reflects realistic cached cost. Assumes `input_tokens` is the **total** prompt
  (cached + fresh), matching OpenAI/Gemini usage reporting.
