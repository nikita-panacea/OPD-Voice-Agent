# Explainer — `backend/telemetry/events.py`

## Purpose
The per-turn telemetry record. Accumulates billable units + latency components for one
conversational turn; the meter computes costs and persists it. Counts/costs/latency only —
**never clinical content** (§9). Pure Python.

## Walkthrough
- **`TurnTelemetry`** — dataclass: `session_id`, `pipeline`, `turn_index`; STT seconds; LLM
  in/out/cached tokens; TTS characters; per-component costs; latency parts (`eou_delay_ms`,
  `llm_ttft_ms`, `tts_ttfb_ms`).
  - **`total_cost`** — sum of the three stage costs.
  - **`e2e_latency_ms`** — end-to-end response latency (patient stops speaking → agent audio
    starts), approximated as EOU delay + LLM TTFT + TTS TTFB; None if no components seen.
  - **`has_response()`** — True once the agent side produced metrics (used to detect turn
    boundaries).

## Gotchas / TODOs
- e2e latency is an approximation from component metrics; good enough for relative comparison.
- Cached tokens are recorded but not yet discounted in cost math (POC).
