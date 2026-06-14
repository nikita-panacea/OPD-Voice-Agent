# CLAUDE.md — OPD Intelligence (Voice-to-Voice Patient Intake)

> This file is the build contract for Claude Code (VS Code extension). Read it fully
> before writing any code. Build in the **phases** defined in §13. Do not skip the
> guardrails in §2 or the per-file explanation rule in §11. When a fact about a model,
> price, SDK signature, or language-support claim might be stale, **use Web Search to
> re-verify before relying on it** — see §15.

---

## 1. What we are building

A **voice-to-voice patient intake agent** for a hospital **OPD (Outpatient Department)**.
Before a patient sees the doctor, the agent holds a natural spoken conversation, collects
the patient's **current complaint** and **relevant medical history**, and produces a
concise **structured intake report** the doctor can read in under a minute.

Core loop: **patient speaks → STT → LLM (intake brain) → TTS → patient hears the agent**,
orchestrated in real time by **LiveKit Agents**. The conversation is captured, scored for
quality, costed per component, and summarized into a clinician-facing report.

**Three languages, first-class:** English (`en`), Hindi (`hi`), Marathi (`mr`),
including code-mixed speech (Hinglish / Marathi-English), which is the realistic input in
Indian OPDs.

**Two cross-cutting goals run through the whole system:**
1. **Smoothness** — natural turn-taking, graceful handling of pauses, and re-explaining a
   question in simpler words (with examples) when the patient is confused.
2. **Cost & performance comparison** — the STT/LLM/TTS providers are *swappable*, and every
   run is logged with token/character/audio counts, per-component cost, and latency, so we
   can compare pipelines on a **cost-vs-smoothness** basis for production.

---

## 2. Non-negotiable guardrails (read before coding)

This is a **healthcare intake** tool. It is **not** a diagnostic or treatment tool.

1. **No diagnosis, no medical advice, no treatment recommendations.** The agent collects
   information and reflects it back to confirm. If the patient asks "what's wrong with me?"
   or "what should I take?", the agent says a doctor will review shortly and does not answer.
2. **Emergency / red-flag escalation is mandatory.** If the patient reports red-flag
   symptoms (e.g. chest pain, difficulty breathing, suspected stroke signs, severe bleeding,
   suicidal ideation/self-harm, signs of anaphylaxis), the agent must (a) calmly advise them
   to alert hospital staff / seek immediate help right now, and (b) raise an `URGENT` flag on
   the session that surfaces to staff immediately. The agent must **not** attempt to manage a
   medical emergency conversationally. This logic lives in `intake/red_flags.py` and is tested.
3. **Consent first.** The session opens by stating that this is an automated assistant
   collecting intake information, that the conversation is recorded/transcribed for the care
   team, and asks the patient to confirm before continuing. No confirmation → no collection.
4. **Patient data is sensitive personal data.** Treat all transcripts, audio, and reports as
   protected health information. Minimize what is stored, encrypt at rest and in transit,
   restrict access, keep an audit log, and make retention configurable. India's DPDP Act 2023
   and the hospital's own policy apply — **confirm specifics with the hospital's compliance/legal
   owner; do not assume.** Never log raw PHI into cost/telemetry logs (telemetry stores counts
   and costs, never clinical content — see §9).
5. **Honesty about identity.** The agent always presents as an automated assistant, never as a
   doctor, nurse, or human.
6. **Graceful failure.** If STT/LLM/TTS fails or confidence is low, the agent degrades
   politely ("Sorry, I didn't catch that — could you repeat it?") and, after repeated failure,
   offers to hand off to hospital staff rather than guessing.

Encode these as explicit code paths and tests, not just prose.

---

## 3. Architecture

**Pattern: cascaded pipeline (STT → LLM → TTS), not speech-to-speech.**
Rationale, confirmed against current (2026) LiveKit guidance: the cascade is the production
default because it lets us (a) **swap any provider independently** for the cost comparison,
(b) get **separate per-stage logs** for token/character/cost tracking, (c) **redact PII
between stages** if needed, and (d) keep **compliance/debuggability**. Speech-to-speech is
lower-latency but gives us none of those, which are central to this project's goals.

```
                       ┌──────────────── LiveKit Room (WebRTC) ───────────────┐
   Patient mic ──────► │  audio in                                            │
                       │     │                                                │
                       │     ▼                                                │
                       │  Silero VAD ──► Turn Detector (MultilingualModel)    │
                       │     │              │                                 │
                       │     ▼              ▼                                 │
                       │   STT  ──► transcript ──► LLM (intake brain) ──► text │
                       │  (plug)                    │ + tools/state            │
                       │                            ▼                          │
                       │                          TTS (plug) ──► audio out ────┼──► Patient ear
                       │  Krisp noise cancellation on the input track          │
                       └───────────────────────────────────────────────────────┘
                                   │ events + metrics (per turn)
                                   ▼
                   Telemetry/Cost ledger  ──►  Session store  ──►  Report generator
                                   │                                     │
                                   ▼                                     ▼
                          Comparison dashboard                Doctor-facing intake report
```

- **Orchestration:** LiveKit Agents 1.x — `AgentServer` + `AgentSession`, with `Agent`
  subclasses for the intake flow and `@function_tool` functions for saving answers.
- **VAD:** Silero VAD (detects speech vs silence).
- **Turn detection:** LiveKit `turn_detector.multilingual.MultilingualModel` (semantic
  end-of-turn — knows the difference between a thinking pause and a finished sentence). This
  is what makes the "understands when the user is pausing" requirement real.
- **Noise suppression:** LiveKit's Krisp integration on the input track.
- **Transport:** WebRTC via LiveKit (browser client ↔ agent worker).

Put a **Mermaid** version of this diagram and the §8 state machine inside `docs/ARCHITECTURE.md`
so they render in VS Code/GitHub.

---

## 4. Tech stack

**Backend / agent / API:** Python 3.11+, `livekit-agents ~=1.0` with the relevant plugins,
FastAPI for the REST/token API, Pydantic for schemas, SQLite for dev → Postgres for prod,
`structlog` for structured logging.

**Frontend:** React (Vite + TypeScript), `@livekit/components-react` + `livekit-client` for
the room connection and mic handling, Tailwind for styling. The UI is intentionally simple:
language picker, connect/disconnect, live transcript, a "speaking/listening" indicator, live
captured-fields panel, and (for staff) a session/report view + the comparison dashboard.

Install (agent): `pip install "livekit-agents[silero,turn-detector]~=1.0"` plus the plugin
packages for whichever providers are enabled (see §6).

---

## 5. Provider matrix (cost comparison is a first-class feature)

Every STT, LLM, and TTS provider sits behind a common interface (§6) and is selected by
config, so a pipeline is just a named triple. **Build these as pluggable from day one.**

### Pricing snapshot — captured June 2026, *verify before trusting*
> Prices move constantly and newer models (e.g. GPT-5.x, Gemini 3.x families) now exist.
> Store these in a versioned `config/pricing.yaml` (§9) and **re-verify via Web Search**
> when running a real cost comparison. Treat the numbers below as starting defaults only.

**LLMs** (USD per 1M tokens, input / output):
| Model | Input | Output | Notes |
|---|---|---|---|
| GPT-4.1 | ~$2.00 | ~$8.00 | 1M context; strong instruction-following |
| GPT-4.1 mini | ~$0.40 | ~$1.60 | great default for structured intake |
| GPT-4.1 nano | ~$0.10 | ~$0.40 | cheapest; routing/extraction |
| Gemini 2.5 Flash | ~$0.30 | ~$2.50 | low cost, multimodal |
| Gemini 2.5 Flash-Lite | ~$0.10 | ~$0.40 | budget tier |
| Sarvam (sarvam-30b / 105b) | provider-priced | provider-priced | native Indic reasoning; OpenAI-compatible, tool-calling |

Prompt caching cuts repeated-system-prompt input cost substantially on GPT-4.1 and Gemini —
factor it in, since our system prompt + intake schema is sent every turn.

**STT** (streaming):
| Provider / model | ~Price | Hindi | Marathi | Notes |
|---|---|---|---|---|
| Deepgram Nova-3 | ~$0.0077/min PAYG | ✅ (in `multi` code-switch set) | ✅ monolingual (set `language="mr"`) | true streaming, low TTFT; Marathi is **not** in the 10-lang code-switch set, so set it explicitly |
| Sarvam Saaras v3 | provider-priced | ✅ | ✅ | **best Indic + code-mix**; auto language detect; `mode="translate"` can emit English for an English LLM |
| Whisper (OpenAI) | per-min | ✅ | ✅ | **batch-oriented**, weak for low-latency streaming — use only as an offline eval baseline, not live |

**TTS:**
| Provider / model | Billing | Hindi | Marathi | Notes |
|---|---|---|---|---|
| ElevenLabs (Flash v2.5 / Multilingual) | per character | ✅ | ✅ | very natural; Flash tier for low latency |
| Sarvam Bulbul (v2/v3) | per character | ✅ | ✅ | native Indic prosody, pitch/pace/loudness control |
| Deepgram Aura | per char/min | English-first | limited | fine for English-only pipelines |

### Recommended starting pipelines to compare
- **`indic_quality`** (default for India): Sarvam Saaras v3 STT → GPT-4.1 (or Gemini 2.5 Flash) → Sarvam Bulbul TTS.
- **`global_stack`**: Deepgram Nova-3 → GPT-4.1 → ElevenLabs Multilingual.
- **`low_cost`**: Deepgram Nova-3 → Gemini 2.5 Flash-Lite / GPT-4.1-nano → Sarvam Bulbul.
- **`translate_bridge`**: Sarvam Saaras v3 (`mode="translate"` → English) → English LLM → translate reply → TTS in patient's language. Cheaper/simpler LLM reasoning, but loses some nuance — make this a *strategy flag*, not the default, and measure its quality cost.

The agent always **responds in the patient's language** (system-prompt instruction +
language-aware TTS), regardless of which STT path is used.

---

## 6. Provider abstraction (how swapping works)

Define three `Protocol`s and a factory. A "pipeline" is a config object naming one provider
per stage plus their options. Switching providers must be a **config change, not a code
change** — this is what makes the comparison harness honest.

```
backend/providers/
  base.py          # STTProvider, LLMProvider, TTSProvider Protocols + ProviderMeter mixin
  registry.py      # name -> builder; reads config, returns LiveKit plugin instances
  stt_deepgram.py  # wraps livekit.plugins.deepgram.STT
  stt_sarvam.py    # wraps livekit.plugins.sarvam.STT  (saaras:v3, set language/mode)
  stt_whisper.py   # offline/eval baseline
  llm_openai.py    # livekit.plugins.openai.LLM (gpt-4.1 / mini / nano)
  llm_gemini.py    # livekit.plugins.google.LLM (gemini-2.5-flash ...)
  llm_sarvam.py    # livekit.plugins.sarvam.LLM (sarvam-30b/105b)
  tts_elevenlabs.py
  tts_sarvam.py
  tts_deepgram.py
```

Each wrapper exposes a `meter` that, after each call, reports the **billable units** for that
stage (STT: audio seconds; LLM: input+output tokens; TTS: characters) and the resolved unit
price from `pricing.yaml`, so the telemetry layer (§9) can attribute cost per turn without
the provider code knowing anything about reporting.

`registry.build_session(pipeline_cfg, language) -> AgentSession(...)` assembles
`stt=`, `llm=`, `tts=`, `vad=silero.VAD.load()`,
`turn_detection=MultilingualModel()`, and Krisp noise cancellation, then returns the session.

---

## 7. Languages: handling en / hi / mr + code-mixing

- **Language selection:** patient picks language in the UI at start; also allow the STT's
  auto-detect (Sarvam Saaras v3 / Deepgram multi) to override if the patient clearly speaks
  another supported language. Persist the resolved language on the session.
- **Marathi caveat (Deepgram path):** Marathi is supported as a *monolingual* Nova-3 language
  but is **not** in the multilingual code-switch set, so for Marathi-first patients on the
  Deepgram pipeline, set `language="mr"` explicitly. For heavy code-mixing, prefer the Sarvam
  pipeline.
- **Agent replies in the patient's language**, enforced by the system prompt and the
  language-matched TTS voice. Keep one voice per language in `config/voices.yaml`.
- **Intake questions** are authored in English (canonical, in `intake/questions.py`) with
  `hi` and `mr` translations. Generate the translations with an LLM during build, but mark
  them `needs_clinical_review: true` — a Marathi/Hindi-speaking clinician should review medical
  phrasing before production. Do not ship machine translations of medical questions unreviewed.

---

## 8. Conversation design (the "intake brain")

The agent is **goal-driven, not script-locked**. It has a checklist of fields to fill and
asks for them conversationally, adapting order to what the patient says (if they volunteer
medications while describing the complaint, capture it and don't re-ask).

### 8.1 Default intake schema (`intake/questions.py`)
Each field: `id`, `prompt_{en,hi,mr}`, `simpler_prompt_{en,hi,mr}` (plain-language re-ask
with an example), `type` (free_text / scale_0_10 / yes_no / enum / list), `required`,
`red_flag_check` (optional).

Default fields (clinically standard OPD intake — have a clinician confirm/adjust):
1. **Consent** (yes/no, gate)
2. **Identity confirm** (name, age, sex — if not already from hospital system)
3. **Chief complaint** — "What brought you in today?"
4. **Onset / duration** — when it started, sudden vs gradual
5. **Location** — where in the body
6. **Character** — what it feels like (sharp, dull, burning…)
7. **Severity** — 0–10 scale
8. **Timing / pattern** — constant vs comes-and-goes; worse at any time
9. **Aggravating / relieving factors**
10. **Associated symptoms** (incl. targeted red-flag screen)
11. **Current medications** (incl. dose if known)
12. **Allergies** (drug/food) — flag severe reactions
13. **Past medical history** (chronic conditions, prior similar episodes)
14. **Past surgical / hospitalization history**
15. **Family history** (relevant conditions)
16. **Social history** (tobacco, alcohol, occupation; pregnancy status where relevant)
17. **Anything else the patient wants the doctor to know**

State is saved continuously via a `@function_tool save_intake_field(field_id, value,
confidence)` the LLM calls as it learns each answer — so partial progress survives a dropped
call and the live UI panel updates in real time.

### 8.2 Smoothness behaviors (build + test these)
- **Pause vs done:** rely on the multilingual turn detector + tuned `min_endpointing_delay` /
  `max_endpointing_delay`; don't cut the patient off mid-thought. Elderly/unwell patients
  speak slowly — bias toward patience.
- **Confusion handling:** if the patient says "I don't understand", gives an off-topic answer,
  asks "what do you mean?", or is silent after a question, the agent **re-asks using
  `simpler_prompt_*`** — plainer words + a concrete example (e.g. for "character of pain":
  "Is it more like a sharp poke, or a dull ache, or a burning feeling?"). Track how often this
  happens (a smoothness signal).
- **Confirmation / read-back:** for critical fields (medications, allergies, chief complaint)
  the agent repeats back what it understood and asks the patient to confirm.
- **Barge-in / interruption:** allow the patient to interrupt the agent; stop TTS promptly.
- **Low ASR confidence → clarify**, don't guess.
- **Empathy, brevity:** short, warm, plain sentences. No medical jargon unless the patient uses
  it. One question at a time.

Represent the flow as a state machine in `docs/ARCHITECTURE.md` (Mermaid `stateDiagram`):
`greeting/consent → identity → complaint loop (ask → listen → [clarify?] → save → confirm) →
history loop → red-flag monitor (always on) → wrap-up/confirm → report`.

### 8.3 Report generation (`intake/report.py`)
After wrap-up (or on staff request), the LLM converts the saved fields + transcript into a
**structured clinical intake report**: chief complaint, HPI (history of present illness),
PMH, medications, allergies, family/social history, pertinent positives/negatives, red-flag
flags, language used, and a "patient's own words" quote for the chief complaint. Output as
**structured JSON** (validated by a Pydantic model) **and** a rendered doctor-facing
**Markdown/PDF**. The report carries a header disclaimer: *"Automated intake summary — not a
diagnosis. For clinician review."* No diagnostic impression, no treatment suggestion.

---

## 9. Telemetry, cost ledger & "cost vs smoothness"

This is a headline feature. Build a clean event/metrics layer; **never put clinical content
into cost logs.**

### 9.1 Per-turn metrics (`telemetry/meter.py`, `telemetry/events.py`)
For every turn capture:
- **STT:** audio seconds processed, provider+model, `stt_cost`, ASR confidence (if available).
- **LLM:** input tokens, output tokens, cached tokens, provider+model, `llm_cost`.
- **TTS:** characters synthesized, provider+model, `tts_cost`.
- **Latency:** time-to-first-token (LLM), time-to-first-audio (TTS), and **end-to-end
  response latency** = patient stops speaking → agent audio starts. This is the key UX number.
- **Interaction quality:** interruptions/barge-ins, turn-detector re-cuts, clarification/
  re-ask count, repeats requested, STT retries.

### 9.2 Cost math (`telemetry/cost.py` + `config/pricing.yaml`)
`pricing.yaml` holds dated unit prices per provider/model with a `source` and `as_of` field.
Cost per stage = billable_units × unit_price. **Cost per patient intake** = Σ over all turns.
Keep pricing data-driven so updating a price never touches code, and so every historical
session can be re-costed against the price set that was live then.

### 9.3 Smoothness score (`telemetry/smoothness.py`)
Define a transparent composite (document the formula and weights), e.g. a weighted blend of:
median end-to-end latency, clarification rate, interruption/cut rate, ASR confidence, intake
**completion rate** (fields filled ÷ required), and (optional) a post-call 1–5 patient rating
collected in the UI. Output 0–100. Keep the weights in config so they're tunable, and always
store the raw components alongside the score so it stays auditable.

### 9.4 Cost-vs-smoothness comparison (`telemetry/compare.py` + dashboard)
Aggregate sessions by pipeline config and produce, per pipeline: median cost/intake, p50/p95
end-to-end latency, completion rate, smoothness score, and a **cost-vs-smoothness scatter**
(x = cost/intake, y = smoothness). This is the artifact that answers "which pipeline for
production?". Expose it via a FastAPI endpoint and a React dashboard page; also support CSV
export.

### 9.5 Offline experiment runner (`experiments/run_matrix.py`)
A harness that replays a set of recorded intake audio (or scripted patient utterances)
through each enabled pipeline so providers are compared **on identical input**, removing
patient-to-patient variance. Emits the same telemetry rows as live sessions. This is how the
real provider bake-off happens before production.

---

## 10. Repository structure

```
opd-intelligence/
├── CLAUDE.md                      # this file
├── README.md                      # human setup + run guide
├── .env.example                   # all required env vars, documented
├── docs/
│   ├── ARCHITECTURE.md            # mermaid architecture + state diagrams
│   ├── EXPLAINERS/                # one companion .md per source file (see §11)
│   └── DECISIONS.md               # short ADRs for key choices
├── backend/
│   ├── pyproject.toml
│   ├── config/
│   │   ├── settings.py            # env-driven settings (pydantic-settings)
│   │   ├── pipelines.yaml         # named STT/LLM/TTS triples to compare
│   │   ├── pricing.yaml           # dated unit prices per provider/model
│   │   └── voices.yaml            # per-language TTS voice IDs
│   ├── agent/
│   │   ├── worker.py              # AgentServer entrypoint, session wiring, Krisp/VAD/turn-detect
│   │   ├── intake_agent.py        # Agent subclass: instructions + function tools
│   │   └── prompts.py             # system prompts (en/hi/mr), guardrail text, persona
│   ├── providers/                 # see §6
│   ├── intake/
│   │   ├── questions.py           # field schema + multilingual prompts
│   │   ├── state.py               # session intake state + persistence
│   │   ├── red_flags.py           # emergency detection + URGENT flag
│   │   └── report.py              # structured report + markdown/PDF render
│   ├── telemetry/                 # meter, events, cost, smoothness, compare
│   ├── api/
│   │   ├── main.py                # FastAPI app
│   │   ├── tokens.py              # LiveKit access-token minting for clients
│   │   ├── sessions.py            # session + report read endpoints (staff-auth)
│   │   └── dashboard.py           # comparison data endpoints
│   ├── store/                     # db models + repositories (SQLite→Postgres)
│   ├── experiments/run_matrix.py  # offline provider bake-off
│   └── tests/                     # pytest: red flags, cost math, state, smoothness, schema
└── frontend/
    ├── package.json
    └── src/
        ├── App.tsx
        ├── lib/livekit.ts         # connect to room, mic, events
        ├── pages/
        │   ├── Intake.tsx         # patient view: language, connect, captions, live fields
        │   ├── Sessions.tsx       # staff: list + report view
        │   └── Dashboard.tsx      # cost-vs-smoothness comparison
        └── components/            # LanguagePicker, MicIndicator, TranscriptView, FieldPanel, CostSmoothChart
```

---

## 11. Coding conventions — including the per-file explanation rule

**Mandatory: every source file you create gets a companion explanation.** The user wants a
detailed, function-wise explanation of every code file.

For each file `backend/intake/report.py`, also create `docs/EXPLAINERS/backend__intake__report.md`
containing:
1. **Purpose** — one paragraph: what this file is responsible for and where it sits in the flow.
2. **Dependencies & data in/out** — what it imports, what it's given, what it returns/emits.
3. **Function-by-function / class-by-class walkthrough** — for *each* function or method:
   its signature, what it does step by step, why it exists, key edge cases, and how it
   connects to other files. Use plain language a new engineer (or the user) can follow.
4. **Gotchas / TODOs** — anything fragile, any assumption, anything left for later.

Also put a concise module docstring at the top of each source file and a docstring on every
public function/class (the in-code docstring is the short version; the EXPLAINERS file is the
long version). Keep an index in `docs/EXPLAINERS/README.md` mapping every source file → its
explainer. **A file is not "done" until its explainer exists and matches the code.**

Other conventions:
- Python: full type hints, `ruff` + `black`, Pydantic models for all structured data, no bare
  `except`, structured logging via `structlog`. Async where LiveKit/IO requires it.
- Secrets only via env vars (`.env`, never committed); `.env.example` documents every key.
- Tests with `pytest` for all non-UI logic; the red-flag and cost-math modules must have
  thorough tests. Frontend: TypeScript strict mode.
- Small, focused commits per phase with clear messages.

---

## 12. Environment & setup

Document everything in `.env.example`. Expected keys (enable only the providers you use):
```
# LiveKit
LIVEKIT_URL=…           LIVEKIT_API_KEY=…        LIVEKIT_API_SECRET=…
# LLM
OPENAI_API_KEY=…        GOOGLE_API_KEY=…         SARVAM_API_KEY=…
# STT/TTS
DEEPGRAM_API_KEY=…      ELEVENLABS_API_KEY=…     # Sarvam uses SARVAM_API_KEY
# Noise suppression
# (Krisp via LiveKit — follow LiveKit's Krisp setup)
# App
DATABASE_URL=…          ACTIVE_PIPELINE=indic_quality
DATA_RETENTION_DAYS=…   STAFF_AUTH_SECRET=…
```
Before first run of the agent, download the turn-detector + VAD model files
(`python -m … download-files` per the plugin docs). Provide a `make dev` / documented commands
to run: (1) the FastAPI token+API server, (2) the LiveKit agent worker, (3) the React app.

---

## 13. Build phases (do them in order; each ends with a working, tested slice)

**Phase 0 — Foundations.** Repo skeleton, `settings.py`, `.env.example`, `pricing.yaml`,
`pipelines.yaml`, logging, db setup, README. Explainers for each file. ✅ when the app boots
and config loads.

**Phase 1 — Provider abstraction.** `providers/base.py` Protocols + `registry.py` + one real
provider per stage (start with the `indic_quality` pipeline) and the `meter` reporting
billable units. ✅ when `registry.build_session(...)` returns a wired `AgentSession`.

**Phase 2 — Minimal live voice loop.** LiveKit `worker.py`, a trivial agent that greets and
echoes, Silero VAD + multilingual turn detection + Krisp. FastAPI `tokens.py`. A bare React
`Intake.tsx` that connects and shows captions. ✅ when you can hold a spoken back-and-forth in
the browser.

**Phase 3 — Intake brain.** `questions.py` (en + generated hi/mr marked for review), `state.py`,
`save_intake_field` tool, `prompts.py` with guardrails + persona, confirmation/read-back,
clarification via `simpler_prompt_*`. Live field panel in the UI. ✅ when a full English intake
completes and fields persist.

**Phase 4 — Safety.** `red_flags.py` + URGENT flagging surfaced to staff; consent gate;
graceful-failure + handoff paths. Tests. ✅ when red-flag utterances reliably trigger escalation
and consent gating works.

**Phase 5 — Multilingual.** Hindi + Marathi end to end (incl. Marathi `language="mr"` on the
Deepgram path), language-matched TTS voices, code-mix handling, clinician-review flags on
translations. ✅ when a full intake completes in each language.

**Phase 6 — Telemetry & cost.** Per-turn meter → events → cost ledger → smoothness score →
cost-per-intake. ✅ when each session yields a complete, accurate metrics row.

**Phase 7 — Report.** `report.py` structured JSON + Markdown/PDF, staff `Sessions.tsx` view. ✅
when a finished intake produces a clean doctor-facing report with the disclaimer.

**Phase 8 — Comparison.** Wire all pipelines, `experiments/run_matrix.py`, `compare.py`,
`Dashboard.tsx` cost-vs-smoothness scatter + CSV export. ✅ when you can rank pipelines on
cost vs smoothness from identical replayed input.

**Phase 9 — Hardening.** Encryption at rest, retention job, staff auth, audit log, error
handling, load sanity. ✅ when guardrails + privacy controls are demonstrably enforced.

After each phase: update the affected EXPLAINERS and `docs/DECISIONS.md`.

---

## 14. Definition of done

A patient connects, picks (or is auto-detected into) en/hi/mr, gives consent, and has a smooth
spoken conversation where the agent patiently handles pauses and re-explains when confused;
all intake fields are captured and confirmed; red flags escalate to staff; a structured,
disclaimered report is produced for the doctor; every session is logged with per-component
counts, cost-per-intake, and a smoothness score; multiple provider pipelines can be compared
on a cost-vs-smoothness dashboard from identical input; and **every source file has a current,
accurate function-wise explainer.**

---

## 15. Web-search policy during the build

Model names, prices, SDK signatures, plugin package names, and language-support claims in this
file are a **June 2026 snapshot and will drift.** Before relying on any of them — especially
when wiring a provider plugin, setting a model string, or populating `pricing.yaml` for a real
cost comparison — **search the web to confirm the current** LiveKit Agents API, plugin import
paths/params, model identifiers, per-unit prices, and Hindi/Marathi support. Prefer official
sources (LiveKit docs, the provider's own pricing/docs pages). When you update a fact, note the
source and date in `pricing.yaml` / `docs/DECISIONS.md`. Don't silently trust this file over
the live docs.
