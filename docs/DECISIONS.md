# Decisions (ADRs) + verified facts

Short architecture decision records and the §15 web-verification log. Newest first.

---

## ADR-0011 — Whisper+Sarvam comparison pipelines + prompt-cache cost discount

**Status:** accepted (2026-06-15).
**Context:** A cost analysis estimated Whisper STT + {GPT-4.1 nano/mini, Gemini 2.5 Flash} +
Sarvam TTS, and showed the re-sent system prompt makes prompt caching the main LLM lever — but
`cost.py` billed all input at full price, so the dashboard overstated LLM cost.
**Decision:**
1. Added pipelines `whisper_sarvam_nano` / `whisper_sarvam_mini` / `whisper_sarvam_gemini`
   (Whisper `whisper-1` STT → the three LLMs → Sarvam Bulbul) so the dashboard reports these
   exact combinations.
2. Added `usd_per_1m_cached_input` to the LLM entries in `pricing.yaml` (verified 2026-06-15:
   OpenAI cached ≈ 0.25× input → gpt-4.1 $0.50 / mini $0.10 / nano $0.025; Gemini cache read
   ≈ 0.10× input → 2.5-flash $0.03 / flash-lite $0.01).
3. `cost.llm_cost(..., cached_tokens=0)` now bills cached tokens (a clamped subset of input) at
   the cached rate; the meter passes `prompt_cached_tokens`, so `/api/compare` reflects realistic
   cost. `cached_tokens=0` keeps old behavior (back-compatible).
**Verified:** `build_session("whisper_sarvam_nano", ...)` builds; meter shows gpt-4.1-mini with
8k/10k cached = $0.00176 vs $0.00416 uncached; 59 tests pass (incl. 4 new cached-cost tests).
**Note:** `whisper-1` is batch-oriented — swap the STT model to `gpt-4o-mini-transcribe` for live
streaming. Caching realized only if the provider returns `prompt_cached_tokens` (stable system
prompt + tools makes this likely on OpenAI/Gemini).

## ADR-0013 — ASR mis-hearing protection (sense-check + confidence gate)

**Status:** accepted (2026-06-16).
**Context:** When STT mis-transcribes (homophones, garbled words), the agent accepted the
nonsensical text as the patient's answer and continued, instead of clarifying (violates §8.2
"low ASR confidence → clarify, don't guess").
**Decision (two layers):**
1. **Prompt sense-check** (works with any STT, even without confidence): `prompts.py` now tells
   the agent that STT can return wrong/homophone words and to verify each answer is coherent +
   plausible for the question before saving — confirm/repeat on doubt, never assume garbled text,
   read back unusual medicine names/numbers.
2. **Deterministic confidence gate** in `IntakeAgent.on_user_turn_completed`
   (`_low_confidence_decision`): if `ChatMessage.transcript_confidence` is in `(0, MIN_ASR_CONFIDENCE)`
   the agent speaks a localized "please repeat" and `StopResponse`s (the misheard text is never
   processed/saved); after `ASR_LOW_CONFIDENCE_LIMIT` consecutive low-confidence turns it hands
   off to staff. Confidence None/0.0 = provider didn't report it → not gated (layer 1 still applies).
**Settings:** `MIN_ASR_CONFIDENCE=0.5`, `ASR_LOW_CONFIDENCE_LIMIT=3` (tunable).
**Verified:** 67 tests pass incl. `tests/test_asr_confidence.py` (repeat→handoff escalation,
streak reset, None/0 treated as unknown).
**Note:** the confidence gate only fires when the STT provider populates `transcript_confidence`
(varies by provider); the prompt sense-check is the always-on layer.

## ADR-0012 — All-in cost (incl. LiveKit), full transcript, rotating file logs

**Status:** accepted (2026-06-16).
**Context:** `opd.db`/`/api/compare` reported only STT/LLM/TTS cost (no LiveKit), the full
conversation wasn't persisted, and logs were stdout-only.
**Decisions:**
1. **LiveKit cost** — added a `livekit` section to `pricing.yaml` ($0.01/agent-min +
   $0.0004/participant-min, Build/PAYG, verified 2026-06-15), `cost.livekit_cost()`, and
   `session_seconds`/`livekit_cost` columns on `intake_sessions` (set at session end from
   wall-clock). `compare.py` folds LiveKit into an **all-in** cost/intake and reports
   `avg_livekit_cost_usd` + `avg_session_seconds`. A lightweight `init_db` ALTER migration adds
   the new columns to existing DBs (no data loss).
2. **Full transcript** — new `transcripts` table + `intake/transcript.py` `TranscriptRecorder`
   (subscribes to `conversation_item_added`), staff endpoint `GET /api/sessions/{id}/transcript`.
   **PHI:** access-restricted, retention-bound, opt-out via `PERSIST_TRANSCRIPT=false`; transcript
   text never enters logs/telemetry.
3. **Rotating file logs** — `logging_setup` now writes both a human console and a rotating
   `backend/logs/<name>.jsonl` (worker→`agent.jsonl`, API→`api.jsonl`); `logs/` git-ignored.
**Verified:** 63 tests pass (livekit_cost, all-in compare, transcript record/recorder); CLI +
`/api/compare` show the new columns; JSONL log file written; transcript endpoint returns ordered
turns.
**Note:** LiveKit cost is modelled per-minute on the Build/PAYG rate — confirm your tier
(Scale is required for HIPAA and is cheaper). Keep `logs/` and `.venv` out of OneDrive sync.

## ADR-0010 — Marathi enabled end-to-end (VAD turn-detection fallback)

**Status:** accepted (2026-06-15). **Supersedes ADR-0002 and ADR-0008's Marathi deferral.**
**Context:** Marathi is a first-class language in CLAUDE.md §1; the only true blocker was the
turn detector. Re-verified 2026-06-15 against the **installed** model's `languages.json`:
MultilingualModel covers en/hi but **not mr** (authoritative, not just the doc claim).
**Decision:** Ship Marathi across the whole pipeline. STT/TTS already support it (Sarvam
`mr-IN`; Deepgram monolingual `mr`; ElevenLabs/Whisper `mr`). For the turn-detection gap,
`registry.build_session` selects the semantic `MultilingualModel` for supported languages and
falls back to **`turn_detection="vad"`** (Silero VAD endpointing) for Marathi, with patience-
biased `min/max` endpointing delays (§8.2). Added mr to: the 17-field schema, prompts +
consent script, red-flag terms + escalation message, voices.yaml, worker/token
`SUPPORTED_LANGUAGES`, and the UI language picker.
**Also:** migrated `AgentSession` from the now-deprecated `turn_detection` +
`min/max_endpointing_delay` kwargs to `turn_handling=TurnHandlingOptions(turn_detection=...,
endpointing=EndpointingOptions(min_delay=, max_delay=))` (deprecated-in-1.6, removed in v2.0).
**Verified at build:** `build_session(..., "mr")` constructs a full `AgentSession`
(turn_detection=vad) with no deprecation warning; 55 tests pass incl. mr schema/prompt/report/
red-flag/turn-detection coverage.
**Caveat:** mr (and hi) prompts are machine-authored, `needs_clinical_review=true` — a Marathi-
speaking clinician must review before real use. VAD endpointing is less semantically aware than
MultilingualModel, so Marathi turn-taking may be slightly less smooth; revisit if LiveKit adds
Marathi to the turn detector.

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

**Status:** SUPERSEDED by ADR-0010 (2026-06-15) — Marathi is now shipped with a VAD fallback.
**Status (original):** accepted (2026-06-14).
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
