# EXPLAINERS index

Per CLAUDE.md §11, **every source file has a companion explainer here** (function-by-function
walkthrough). A file is not "done" until its explainer exists and matches the code. Naming:
`backend/intake/report.py` → `backend__intake__report.md`.

## Backend

### config / foundations (Phase A)
- [backend/config/settings.py](backend__config__settings.md) — env settings + YAML loaders
- [backend/config/pricing.yaml](backend__config__pricing.md) — dated unit prices
- [backend/config/pipelines.yaml](backend__config__pipelines.md) — named STT/LLM/TTS triples
- [backend/config/voices.yaml](backend__config__voices.md) — per-language TTS voices
- [backend/store/db.py](backend__store__db.md) — SQLite engine, ORM models, session scope
- [backend/logging_setup.py](backend__logging_setup.md) — structlog configuration

### providers (Phase B)
- [backend/providers/base.py](backend__providers__base.md) — Protocols, meter, StageBuild
- [backend/providers/registry.py](backend__providers__registry.md) — factory / build_session
- [backend/providers/stt_sarvam.py](backend__providers__stt_sarvam.md) — Sarvam Saaras STT
- [backend/providers/llm_openai.py](backend__providers__llm_openai.md) — OpenAI LLM
- [backend/providers/tts_sarvam.py](backend__providers__tts_sarvam.md) — Sarvam Bulbul TTS
- [backend/tests/test_meter.py](backend__providers__base.md) — meter unit tests (see base explainer)

### agent + api + frontend (Phase C)
- [backend/agent/worker.py](backend__agent__worker.md) — LiveKit worker entrypoint
- [backend/api/main.py](backend__api__main.md) — FastAPI app
- [backend/api/tokens.py](backend__api__tokens.md) — LiveKit token minting
- [frontend/src/lib/livekit.ts](frontend__src__lib__livekit.md) — Room/connection hook
- [frontend/src/pages/Intake.tsx](frontend__src__pages__Intake.md) — patient view
- [frontend/src/components/LanguagePicker.tsx](frontend__src__components__LanguagePicker.md)
- [frontend/src/components/MicIndicator.tsx](frontend__src__components__MicIndicator.md)
- [frontend/src/components/TranscriptView.tsx](frontend__src__components__TranscriptView.md)
- [frontend/src/components/FieldPanel.tsx](frontend__src__components__FieldPanel.md)
- [frontend/src/{main,App}.tsx + vite-env.d.ts + index.css](frontend__src__shell.md)

### intake brain (Phase D)
- [backend/intake/questions.py](backend__intake__questions.md) — §8.1 field schema (en/hi)
- [backend/intake/state.py](backend__intake__state.md) — session state + persistence
- [backend/agent/prompts.py](backend__agent__prompts.md) — system prompt builder
- [backend/agent/intake_agent.py](backend__agent__intake_agent.md) — Agent + tools
- [backend/tests/test_questions.py](backend__intake__questions.md) — schema tests (see questions explainer)
- [backend/tests/test_state.py](backend__intake__state.md) — state tests (see state explainer)

### safety (Phase E)
- [backend/intake/red_flags.py](backend__intake__red_flags.md) — deterministic red-flag backstop
- [backend/tests/test_red_flags.py](backend__intake__red_flags.md) — red-flag + consent-gate tests
- (consent gate + handoff live in [intake_agent.py](backend__agent__intake_agent.md))

### telemetry (Phase F)
- [backend/telemetry/events.py](backend__telemetry__events.md) — per-turn telemetry record
- [backend/telemetry/cost.py](backend__telemetry__cost.md) — cost math from pricing.yaml
- [backend/telemetry/meter.py](backend__telemetry__meter.md) — metrics → costed rows
- [backend/tests/test_cost.py](backend__telemetry__cost.md) — cost-math tests
- [backend/tests/test_telemetry.py](backend__telemetry__meter.md) — meter routing tests

### report (Phase G)
- [backend/intake/report.py](backend__intake__report.md) — structured report + Markdown
- [backend/api/sessions.py](backend__api__sessions.md) — staff list + report endpoints
- [backend/tests/test_report_schema.py](backend__intake__report.md) — report tests

### Hindi (Phase H)
Hindi reused the bilingual support built in Phases C–G (no new source files): Saaras `hi-IN`
([stt_sarvam](backend__providers__stt_sarvam.md)), Bulbul Hindi voice
([tts_sarvam](backend__providers__tts_sarvam.md) + voices.yaml), Hindi prompts
([questions](backend__intake__questions.md) + [prompts](backend__agent__prompts.md)), and the UI
picker. Verified by `backend/tests/test_languages.py`.

> `backend/pyproject.toml` is build/packaging metadata (dependencies, ruff/black/pytest
> config) — documented inline; no separate function-wise explainer.
