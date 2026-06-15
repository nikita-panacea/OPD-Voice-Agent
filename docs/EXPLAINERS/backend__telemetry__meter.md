# Explainer — `backend/telemetry/meter.py`

## Purpose
The session meter: subscribes to the `AgentSession`'s `metrics_collected` stream, converts each
metric into billable units (via the per-stage `ProviderMeter`s from the registry), prices them
(`cost.py`), accumulates a `TurnTelemetry`, and persists one `TelemetryRow` per turn. No
clinical content stored (§9). Routing is by metric class name, so it's unit-testable with fakes.

## Dependencies & data in/out
- **Imports:** `providers.base.ProviderMeter`, `store.db` (TelemetryRow/session_scope),
  `telemetry.cost`, `telemetry.events.TurnTelemetry`, logger.
- **In:** LiveKit metric objects. **Out:** persisted `TelemetryRow`s.

## Walkthrough
- **`_ms(seconds)`** — seconds → ms (preserves None).
- **`SessionMeter.__init__(session_id, pipeline, meters)`** — holds the stage meters + the
  current `TurnTelemetry` + a turn counter.
- **`attach(agent_session)`** — registers `_on_metrics` on `metrics_collected`.
- **`_on_metrics(ev)`** — unwraps `ev.metrics` and calls `record`.
- **`record(metric)`** — routes by `type(metric).__name__`:
  - `STTMetrics` → if the current turn already has a response, `flush()` first (new utterance =
    new turn); add STT seconds + cost.
  - `EOUMetrics` → set end-of-utterance delay.
  - `LLMMetrics` → add tokens + cost (passes `cached_tokens` to `cost.llm_cost` so the
    prompt-cache discount is applied); capture TTFT.
  - `TTSMetrics` → add characters + cost; capture TTFB.
- **`flush()`** — if the turn has data, write a `TelemetryRow` (counts, costs, e2e latency),
  log a `turn_metered` event (cost + latency only), advance the turn index, reset.
- **`close()`** — flush the final in-progress turn (called from the worker's shutdown callback).

## Gotchas / TODOs
- Turn correlation is heuristic (boundary = next STT after a response). Robust enough for
  per-turn cost/latency; exact speech_id correlation could refine it later.
- Verified metric field names against livekit-agents 1.6.0 (2026-06-14): `audio_duration`,
  `prompt_tokens`/`completion_tokens`/`prompt_cached_tokens`, `characters_count`, `ttft`,
  `ttfb`, `end_of_utterance_delay`.
- Cost-per-intake = Σ of a session's rows (the deferred compare/dashboard aggregates these).
