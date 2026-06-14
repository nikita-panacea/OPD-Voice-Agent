# Decisions (ADRs) + verified facts

Short architecture decision records and the §15 web-verification log. Newest first.

---

## ADR-0001 — POC scope: one pipeline, en + hi, narrow vertical slice

**Status:** accepted (2026-06-14).
**Context:** CLAUDE.md describes a full 9-phase system. We need to prove the concept fast.
**Decision:** Build the narrowest end-to-end slice on a single live pipeline (`indic_quality`),
English first then Hindi. Defer: multi-pipeline dashboard, smoothness composite score, offline
replay harness, Whisper, full Marathi, other pipelines, PDF, Phase 9 hardening — while keeping
the §6 provider abstraction intact so nothing is architected away.
**Consequence:** The registry/Protocols are real from day one; deferred pipelines need only
their provider wrappers added later (no code churn).

## ADR-0002 — Marathi deferred (turn-detector limitation)

**Status:** accepted (2026-06-14).
**Context:** CLAUDE.md wants all three of en/hi/mr first-class.
**Decision:** POC ships en + hi only. The LiveKit `MultilingualModel` turn detector supports
Hindi but **not Marathi** (verified — see facts table #5). Marathi belongs in the post-POC
full-multilingual phase, where it needs VAD-only/heuristic endpointing or a fallback.
**Consequence:** Marathi voices/prompts are stubbed in config but not wired live.

## ADR-0003 — Intake brain LLM = GPT-4.1 (config-swappable)

**Status:** accepted (2026-06-14).
**Context:** The intake brain relies heavily on tool-calling (`save_intake_field`).
**Decision:** Default to OpenAI GPT-4.1 for strong instruction-following + tool-calling.
Gemini 2.5 Flash and Sarvam LLM remain config swaps via `pipelines.yaml`.

## ADR-0004 — Run from `backend/` with top-level imports

**Status:** accepted (2026-06-14).
**Decision:** `backend/` is the Python import root. Modules import as `config.*`, `store.*`,
`providers.*`, etc. Run the worker with `python -m agent.worker` and the API with
`uvicorn api.main:app`, both from `backend/`, so package imports resolve consistently.

## ADR-0005 — Frontend uses `livekit-client` directly + plain CSS (not components-react/Tailwind)

**Status:** accepted (2026-06-14).
**Context:** CLAUDE.md §4 lists `@livekit/components-react` + Tailwind. Hook names in the React
component library shift between versions and we can't run the live loop in this environment.
**Decision:** Implement the client on `livekit-client` directly (stable API: `Room`,
`RoomEvent.TranscriptionReceived`, `ActiveSpeakersChanged`, `TrackSubscribed`) and style with
plain CSS. This keeps the POC robust and easy to follow. Swapping to components-react/Tailwind
later is contained to the `frontend/src` layer.

## ADR-0009 — All comparison providers added; pipeline cost/perf comparison enabled

**Status:** accepted (2026-06-14). Supersedes the "single-pipeline first" scope of ADR-0001 for
providers.
**Context:** Cost-vs-smoothness comparison across provider combinations is a first-class POC
goal (CLAUDE.md §1/§5/§9). The initial pass shipped one pipeline; the abstraction was built to
make adding the rest cheap.
**Decision:** Added wrappers for **Deepgram** (STT), **ElevenLabs** (TTS), **Google/Gemini**
(LLM), and **OpenAI/Whisper** (STT, eval), registered them, and enabled six pipelines in
`pipelines.yaml` (`indic_quality`, `global_stack`, `low_cost`, `translate_bridge`,
`global_quality`, `whisper_eval`). Added `telemetry/compare.py` + `GET /api/compare` +
`python -m telemetry.compare` to aggregate **median cost/intake, p50/p95 latency, completion**
per pipeline from real sessions. Verified prices (2026-06-14): OpenAI STT $0.003–0.006/min;
ElevenLabs Flash ≈ $0.05–0.12/1K chars (estimate stored, plan-dependent).
**Verified at build:** all four plugins install at 1.6.0; constructors match the wrappers;
ElevenLabs reads `ELEVEN_API_KEY` so the wrapper injects `ELEVENLABS_API_KEY` explicitly.
**Still deferred:** the offline **replay harness** (identical-input bake-off, §9.5), the React
**scatter dashboard**, and the weighted **smoothness composite** — `compare.py`/`/api/compare`
is their data source. To compare now: set `ACTIVE_PIPELINE`, run sessions, read `/api/compare`.

## ADR-0007 — Report is built deterministically (no LLM narrative) in the POC

**Status:** accepted (2026-06-14).
**Context:** §8.3 envisions an LLM-generated HPI narrative.
**Decision:** The POC assembles the report deterministically from captured fields (cheap,
reproducible, testable, no extra key/latency). The structured JSON + Markdown carry the
disclaimer and contain no diagnosis/treatment. An LLM-polished narrative + PDF are deferred.

## ADR-0008 — Hindi added by reusing the bilingual build (no separate phase code)

**Status:** accepted (2026-06-14).
**Decision:** Rather than bolt Hindi on at the end, en/hi were built together through Phases
C–G (questions, prompts, voices, language codes, UI picker). Phase H is therefore verification
(`tests/test_languages.py`), not new code. Marathi remains deferred (turn-detector gap, ADR-0002).

## ADR-0006 — Frontend pinned to Vite 4 for Node 16

**Status:** accepted (2026-06-14).
**Context:** The dev machine runs Node 16 (EOL); Vite 5/6 require Node 18+.
**Decision:** Pin Vite 4 (`engines: node >=16`). README recommends upgrading to Node 18 LTS,
after which Vite can be bumped. `download-files` is now run via `python -m livekit.agents
download-files` (the agent-script form was deprecated in livekit-agents 1.5.10) — confirmed live.

**Verified at build (2026-06-14):** installed `livekit-agents 1.6.0` + all plugins at `1.6.0`
(`livekit-plugins-sarvam 1.6.0` — the earlier 1.2.8 tracker number was stale, resolving R5).
`AgentServer`/`WorkerOptions`/`AgentSession`/`RoomInputOptions`/`function_tool` all present;
`cli.run_app(AgentServer)` valid; Sarvam STT/TTS + OpenAI LLM constructor kwargs match the
wrappers; `noise_cancellation.BVC()` present; `MultilingualModel()` requires a live job context
(constructed inside the worker entrypoint, as designed).

---

## Verified facts (§15) — all checked 2026-06-14 via web search

| # | Fact | Source |
|---|---|---|
| 1 | `livekit-agents` latest **1.6.0** (released 2026-06-11); Python 3.10–3.14 → use `~=1.6` | PyPI livekit-agents |
| 2 | Worker: both `AgentServer`+`@server.rtc_session()` and `WorkerOptions`+`cli.run_app(entrypoint_fnc=)` exist in 1.6 — confirm exact form against installed pkg | docs.livekit.io/agents/server/options ; PyPI quickstart |
| 3 | `AgentSession(stt=, llm=, tts=, vad=, turn_detection=)`; string model specs supported | LiveKit Agents docs |
| 4 | Silero `silero.VAD.load()`; turn detector `from livekit.plugins.turn_detector.multilingual import MultilingualModel` | docs.livekit.io python reference |
| 5 | MultilingualModel includes **Hindi**, **not Marathi** | LiveKit turn-detector docs / HF livekit/turn-detector |
| 6 | Krisp: `from livekit.plugins import noise_cancellation` → `BVC()/BVCTelephony()/NC()`; **requires LiveKit Cloud** | docs.livekit.io enhanced-noise-cancellation ; PyPI noise-cancellation |
| 7 | Sarvam: `from livekit.plugins import sarvam`; `sarvam.STT(model="saaras:v3", language="hi-IN"/"mr-IN", mode=...)`, `sarvam.TTS`, `sarvam.LLM`; mode selection only on saaras:v3 | docs.livekit.io sarvam plugin pages |
| 8 | Deepgram Nova-3 code-switch set excludes Marathi (use monolingual `language="mr"`); Multilingual ≈ **$0.0092/min** (CLAUDE.md's $0.0077 is stale) | deepgram.com/pricing ; Nova-3 expansion blog |
| 9 | Sarvam Saaras STT ≈ **$0.000092/sec**; Bulbul TTS ≈ **$0.0000165/char**; STT `saarika:v2.5`/`saaras:v3`, TTS `bulbul:v2`/`bulbul:v3-beta` | sarvam.ai/api-pricing ; sarvam.ai/models |
| 10 | OpenAI: GPT-4.1 $2/$8, 4.1-mini $0.40/$1.60, 4.1-nano $0.10/$0.40 per 1M (in/out); GPT-5 family also available | OpenAI 2026 pricing trackers |
| 11 | Gemini: 2.5 Flash $0.30/$2.50, 2.5 Flash-Lite $0.10/$0.40 per 1M | ai.google.dev/gemini-api/docs/pricing |
| 12 | ElevenLabs Flash v2.5 = 0.5 credits/char (credit→USD depends on plan) | ElevenLabs 2026 pricing pages |

**Unconfirmed / TODO:** exact 1.6.x worker decorator signature (#2); current
`livekit-plugins-sarvam` version (#7, tracker showed 1.2.8 — likely stale, pin after install);
Sarvam LLM token price (#9, not on POC path); ElevenLabs exact $/char (#12, deferred pipeline).
