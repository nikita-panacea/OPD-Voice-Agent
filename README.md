# OPD Intelligence — Voice-to-Voice Patient Intake (POC)

A voice-to-voice patient intake agent for a hospital OPD. Before a patient sees the doctor,
the agent holds a natural spoken conversation, collects the current complaint and relevant
history, and produces a concise structured intake report for the clinician.

> **This is a POC**, not the production system. The default live pipeline is `indic_quality`
> (Sarvam Saaras v3 STT → GPT-4.1 → Sarvam Bulbul TTS); several other pipelines are wired for
> cost/performance comparison. Languages: **English, Hindi, Marathi** (Marathi uses a VAD
> turn-detection fallback — see [docs/DECISIONS.md](docs/DECISIONS.md) ADR-0010). See
> `.claude/plans/` and `docs/DECISIONS.md` for scope. Build contract: [CLAUDE.md](CLAUDE.md).

> ⚠️ **Not a diagnostic or treatment tool.** It collects information and reflects it back.
> Patient data is sensitive personal data — see the guardrails in CLAUDE.md §2. PHI handling
> in this POC is **dev-grade only** (SQLite + a shared secret); production hardening (Phase 9)
> and DPDP/hospital compliance review are required before any real patient use.

## Architecture

Cascaded pipeline (STT → LLM → TTS) orchestrated by LiveKit Agents, so each provider is
swappable and separately cost-metered. Full diagram + conversation state machine in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Layout

```
backend/    Python: LiveKit agent worker, FastAPI token/report API, providers, intake, telemetry
frontend/   React (Vite + TS): patient intake UI (connect, captions, live captured-fields panel)
docs/       ARCHITECTURE.md, DECISIONS.md, and EXPLAINERS/ (one companion .md per source file)
```

## Setup

> 📘 **Full step-by-step runbook (keys, env, run, verify, troubleshoot):**
> [docs/SETUP_AND_RUN.md](docs/SETUP_AND_RUN.md). The quick version is below.

### 1. Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate            # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -e ".[dev]"             # installs livekit-agents 1.6 + sarvam/openai/krisp plugins
# Download the Silero VAD + MultilingualModel turn-detector model files (one-time):
python -m livekit.agents download-files   # downloads files for all installed plugins
```

Copy `.env.example` → `.env` (at repo root) and fill in the keys (LiveKit Cloud, OpenAI,
Sarvam). You already hold every key on the POC critical path.

### 2. Run (three processes, all from `backend/`)

```bash
# 1) Token + report API
uvicorn api.main:app --reload --port 8000
# 2) LiveKit agent worker
python -m agent.worker dev
# 3) Frontend
cd ../frontend && npm install && npm run dev
```

> **Node version:** the frontend is pinned to Vite 4 so it runs on Node 16+. Node 18 LTS or
> newer is recommended (Node 16 is end-of-life); if you upgrade, you can bump Vite too.

### 3. Tests

```bash
cd backend && pytest
```

## The two cross-cutting goals

1. **Smoothness** — natural turn-taking (Silero VAD + multilingual turn detector), patient
   handling of pauses, and re-explaining a question in simpler words with an example when the
   patient is confused.
2. **Cost & performance comparison** — per-turn token/character/audio counts, per-component
   cost, and end-to-end latency are logged per pipeline. Six provider pipelines ship
   (`indic_quality`, `global_stack`, `low_cost`, `global_quality`, `translate_bridge`,
   `whisper_eval`) across Sarvam / OpenAI / Deepgram / ElevenLabs / Google / Whisper; switch
   with `ACTIVE_PIPELINE` and compare median cost/intake + p50/p95 latency + completion via
   `python -m telemetry.compare` or `GET /api/compare`. See
   [docs/SETUP_AND_RUN.md §7A](docs/SETUP_AND_RUN.md).
