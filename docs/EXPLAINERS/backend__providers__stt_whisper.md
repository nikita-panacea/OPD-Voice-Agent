# Explainer — `backend/providers/stt_whisper.py`

## Purpose
Wraps `livekit.plugins.openai.STT` (Whisper / gpt-4o-transcribe) as an `STTProvider` for the
`whisper_eval` comparison/baseline pipeline.

## Walkthrough
- **`_LANG_CODES`** — `en/hi/mr` passthrough.
- **`WhisperSTTProvider.build(stage_cfg, language)`** — reads `model` (default
  `gpt-4o-mini-transcribe`), `pricing_key`, `options`; constructs `openai.STT(model, language,
  ...)`; returns a `StageBuild` with an STT meter (billable unit = audio seconds). Reads
  `OPENAI_API_KEY` from env.

## Gotchas / TODOs
- Per CLAUDE.md §5, classic `whisper-1` is **batch-oriented** (weak for low-latency streaming) —
  select it only for an eval baseline; the default `gpt-4o-mini-transcribe` streams and is cheap.
- Provider name is `whisper` (matches the §6 filename) though it covers OpenAI transcription
  models generally.
