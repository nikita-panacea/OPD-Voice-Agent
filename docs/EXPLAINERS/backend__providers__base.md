# Explainer — `backend/providers/base.py`

## Purpose
The pure-Python core of the provider abstraction (CLAUDE.md §6). Defines the stage enum, the
`BillableUnits` record, the `ProviderMeter` that converts LiveKit metrics into billable units,
the `StageBuild` result, and the three builder Protocols (`STTProvider`, `LLMProvider`,
`TTSProvider`). No LiveKit imports here, so the metering logic is unit-testable standalone.

## Dependencies & data in/out
- **Imports:** stdlib only (`dataclasses`, `enum`, `typing`).
- **In:** LiveKit metrics objects (or dicts) at runtime. **Out:** `BillableUnits`, `StageBuild`.

## Walkthrough
- **`Stage`** — `str` enum: `STT`/`LLM`/`TTS`.
- **`BillableUnits`** — dataclass holding the units relevant to a stage (STT seconds; LLM
  input/output/cached tokens; TTS characters). Only the stage's own fields are populated.
- **`_first_attr(obj, names, default)`** — probes a list of candidate attribute/dict-key names
  and returns the first present non-None one. Used because LiveKit metric field names differ
  across versions (resolved live in Phase F).
- **`ProviderMeter`** — dataclass holding `stage`, `provider`, `model`, `pricing_key`.
  - `billable_units(metrics)` — branches on `stage` and extracts the right units via
    `_first_attr`. Returns a `BillableUnits`. The meter never computes cost — it only reports
    units + carries `pricing_key`, so telemetry/cost resolves the price (separation of
    concerns, §6).
- **`StageBuild`** — pairs a built LiveKit `component` with its `ProviderMeter`.
- **`STTProvider` / `LLMProvider` / `TTSProvider`** — `runtime_checkable` Protocols; each
  builder object has a `name` and a `build(stage_cfg, language) -> StageBuild` method.

## Gotchas / TODOs
- The candidate metric field names are best-effort; confirm against the installed
  livekit-agents version in Phase F and trim the lists.
- LLM `cached_tokens` mapping enables prompt-caching cost savings later; defaults to 0 if the
  metrics object doesn't expose it.
