# Explainer — `backend/providers/stt_deepgram.py`

## Purpose
Wraps `livekit.plugins.deepgram.STT` (Nova-3) as an `STTProvider` for the comparison pipelines
(global_stack, low_cost, global_quality). True-streaming, low-latency.

## Walkthrough
- **`_LANG_CODES`** — `en→en-US`, `hi→hi`, `mr→mr`.
- **`DeepgramSTTProvider.build(stage_cfg, language)`** — reads `model` (default `nova-3`),
  `pricing_key`, `options`; an explicit `options.language` (e.g. `"multi"` for code-switch)
  overrides the per-session mapping; constructs `deepgram.STT(...)`; returns a `StageBuild` with
  an STT meter (billable unit = audio seconds). Reads `DEEPGRAM_API_KEY` from env.

## Gotchas / TODOs
- **Marathi caveat (§7):** Marathi is monolingual on Nova-3 (`language="mr"`), not in the
  code-switch set; for heavy code-mix prefer Sarvam or set `options.language="multi"`.
- Verified constructor kwargs against livekit-plugins-deepgram 1.6.0 (2026-06-14).
