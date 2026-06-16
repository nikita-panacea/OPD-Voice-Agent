# Explainer — `backend/config/pricing.yaml`

## Purpose
Dated unit prices per provider/model, in USD. Read by `telemetry/cost.py` so cost math is
data-driven: changing a price never touches code, and historical sessions can be re-costed
against the price set that was live then.

## Structure
- `stt:` keyed by `provider/model` → `usd_per_second`.
- `llm:` keyed by `provider/model` → `usd_per_1m_input` + `usd_per_1m_output` + optional
  `usd_per_1m_cached_input` (prompt-cache hit rate; ≈0.25× input for OpenAI, ≈0.10× for Gemini).
  If omitted, cached tokens bill at the full input price.
- `tts:` keyed by `provider/model` → `usd_per_character`.
- `livekit:` keyed by `livekit/cloud` → `usd_per_agent_minute` + `usd_per_participant_minute`
  (transport, billed per minute; read by `cost.livekit_cost`).
- Every entry carries `as_of` (date) + `source` (URL/notes) for auditability.
- The keys here match each pipeline stage's `pricing_key` in `pipelines.yaml`.

## Gotchas / TODOs
- All values verified 2026-06-14 (see `docs/DECISIONS.md` facts table). Re-verify before any
  real cost comparison (§15).
- `null` prices (Sarvam LLM tokens, ElevenLabs $/char) are TODOs — not on the POC critical
  path. Cost math treats missing prices as 0 and should warn.
