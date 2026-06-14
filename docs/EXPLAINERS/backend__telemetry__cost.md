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
- **`stt_cost(seconds, key)`** — seconds × usd_per_second.
- **`llm_cost(input_tokens, output_tokens, key)`** — (in×in_price + out×out_price) / 1e6.
- **`tts_cost(characters, key)`** — characters × usd_per_character.

## Gotchas / TODOs
- Null prices (Sarvam LLM, ElevenLabs $/char) → 0.0 with a warning; fill them before costing
  those providers.
- Prompt-cached tokens are not yet discounted (POC) — would reduce `llm_cost` on cache hits.
