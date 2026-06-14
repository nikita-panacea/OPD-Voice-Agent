# Setup & Run Guide — OPD Voice Intake POC

A complete, copy-paste runbook to get the POC talking end to end: **patient speaks in the
browser → agent listens, asks intake questions, escalates red flags → a clinician report +
per-turn cost/latency telemetry**.

> Pipeline used by the POC: **`indic_quality`** = Sarvam Saaras v3 STT → OpenAI GPT‑4.1 →
> Sarvam Bulbul TTS, on **LiveKit Cloud** (required for Krisp noise cancellation). Languages:
> **English + Hindi**.

> ⚠️ **POC, not production.** No diagnosis/treatment. PHI handling is dev-grade (SQLite +
> shared secret). Hindi prompts and the §8.1 question set are machine-authored and need
> clinical review before real patient use. See [DECISIONS.md](DECISIONS.md) and CLAUDE.md §2.

---

## 0. The big picture (3 processes)

```
┌─────────────┐     POST /api/token      ┌──────────────────────┐
│  Browser    │ ───────────────────────► │  FastAPI API (:8000) │  mints LiveKit token,
│  (frontend  │ ◄─────── token+url ───── │  api.main            │  serves staff reports
│   :5173)    │                          └──────────────────────┘
│             │     WebRTC (mic/audio)    ┌──────────────────────┐
│             │ ◄═══════════════════════►│   LiveKit Cloud Room  │
└─────────────┘                          └──────────┬───────────┘
                                                     │ job dispatch
                                          ┌──────────▼───────────┐
                                          │  Agent worker        │  STT→LLM→TTS, VAD,
                                          │  agent.worker        │  turn-detect, Krisp,
                                          └──────────┬───────────┘  red-flags, telemetry
                                                     ▼
                                            backend/opd.db (SQLite)
```

You will run **three** terminals: (1) the API, (2) the agent worker, (3) the frontend.

---

## 1. Prerequisites

| Need | Version / notes |
|---|---|
| **Python** | 3.11+ (3.12 verified). |
| **Node.js** | 16+ works (frontend pinned to Vite 4). **Node 18 LTS recommended.** |
| **LiveKit Cloud account** | Free tier is fine and **includes Krisp** (required). |
| **OpenAI API key** | For the GPT‑4.1 intake brain. |
| **Sarvam API key** | For Saaras STT + Bulbul TTS. |
| OS | Windows verified (PowerShell). macOS/Linux work with the bash equivalents shown. |

> If the `backend/.venv` and `frontend/node_modules` already exist (they do after the build),
> you can skip the install steps and jump to **§3 (keys)** → **§5 (run)**.

---

## 2. Get your API keys

### 2a. LiveKit Cloud (transport + Krisp)
1. Sign up at **https://cloud.livekit.io** and create a **Project**.
2. In the project, open **Settings → Keys** → create an API key.
3. Copy three values:
   - **Project URL** → `LIVEKIT_URL` (looks like `wss://<name>-xxxx.livekit.cloud`)
   - **API Key** → `LIVEKIT_API_KEY`
   - **API Secret** → `LIVEKIT_API_SECRET`

   Krisp/BVC enhanced noise cancellation is enabled automatically for LiveKit Cloud projects —
   nothing else to configure.

### 2b. OpenAI (LLM)
1. Go to **https://platform.openai.com/api-keys**, create a key → `OPENAI_API_KEY`.
2. Ensure the account has credit and access to `gpt-4.1`.

### 2c. Sarvam (STT + TTS)
1. Go to **https://dashboard.sarvam.ai** (Sarvam AI dashboard), create an API key →
   `SARVAM_API_KEY`.
2. This one key covers Saaras (STT) and Bulbul (TTS).

> **For the default `indic_quality` pipeline** you only need LiveKit + OpenAI + Sarvam. To
> **compare other pipelines** you'll also want **Deepgram**, **ElevenLabs**, and **Google /
> Gemini** keys — see the per-pipeline key matrix in `.env.example` and §7A below.
> - Deepgram: https://console.deepgram.com → API key → `DEEPGRAM_API_KEY`
> - ElevenLabs: https://elevenlabs.io → Profile → API key → `ELEVENLABS_API_KEY`
>   (we read this even though the plugin's native var is `ELEVEN_API_KEY`)
> - Google AI Studio: https://aistudio.google.com/apikey → `GOOGLE_API_KEY`

---

## 3. Configure environment (`.env` at the repo root)

Create `.env` in the **repository root** (same folder as `CLAUDE.md`), by copying the example:

**PowerShell**
```powershell
Copy-Item .env.example .env
```
**bash**
```bash
cp .env.example .env
```

Then edit `.env` and fill in the keys:

```dotenv
# --- LiveKit Cloud ---
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# --- LLM ---
OPENAI_API_KEY=sk-...

# --- Speech (Sarvam covers STT + TTS) ---
SARVAM_API_KEY=...

# --- App ---
DATABASE_URL=sqlite:///./opd.db
ACTIVE_PIPELINE=indic_quality
DATA_RETENTION_DAYS=30
STAFF_AUTH_SECRET=choose-a-long-random-string
LOG_LEVEL=INFO
```

Notes:
- The backend reads this **root** `.env` regardless of where you launch it from.
- **`STAFF_AUTH_SECRET`** protects the staff report endpoints — pick something non-trivial.
- **DB location:** `sqlite:///./opd.db` is relative to the working directory. Run **both** the
  API and the worker from `backend/` (instructions below) so they share `backend/opd.db`.
  Prefer an absolute path if you want to be certain, e.g.
  `DATABASE_URL=sqlite:///C:/opd-data/opd.db` (use forward slashes).

---

## 4. Install (skip if already installed)

### 4a. Backend
**PowerShell**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m livekit.agents download-files   # one-time: Silero VAD + turn-detector models
```
**bash (Git Bash / macOS / Linux)**
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python -m livekit.agents download-files
```

### 4b. Frontend
```bash
cd frontend
npm install
```
Optional: `cp .env.example .env.local` if your API runs somewhere other than
`http://localhost:8000` (sets `VITE_API_BASE`).

---

## 5. Run the POC (three terminals)

> Activate the venv in each backend terminal first
> (`.\.venv\Scripts\Activate.ps1` or `source .venv/bin/activate`), and run the two backend
> processes **from the `backend/` folder**.

### Terminal 1 — API (token + staff reports)
```bash
cd backend
uvicorn api.main:app --reload --port 8000
```
Expect: `Uvicorn running on http://127.0.0.1:8000` and an `api_startup_complete` log.
Sanity check: open **http://localhost:8000/health** → `{"status":"ok"}`.

### Terminal 2 — Agent worker (the voice brain)
```bash
cd backend
python -m agent.worker dev
```
Expect: the worker connects to LiveKit Cloud and logs `registered worker`. It now waits for a
patient to join a room. (Leave it running.)

### Terminal 3 — Frontend (patient UI)
```bash
cd frontend
npm run dev
```
Expect: `Local: http://localhost:5173/`.

---

## 6. Use it

1. Open **http://localhost:5173** in Chrome/Edge.
2. Pick a **language** (English or हिन्दी) and click **Start conversation**.
3. **Allow microphone** access when prompted.
4. The assistant greets you and asks for **consent** → say "yes".
5. Talk to it. Watch:
   - **live captions** (you + assistant),
   - the **speaking/listening** indicator,
   - the **Captured so far** panel filling in as fields are saved/confirmed.
6. Try the behaviours:
   - **Clarification:** answer a question with "I don't understand" → it re-asks in simpler
     words with an example.
   - **Read-back:** give a medication/allergy → it repeats it back and asks you to confirm.
   - **Red flag (safety):** say *"I have severe chest pain"* → it calmly tells you to alert
     staff and an **Urgent** banner appears (escalation is logged for staff).
7. When the required fields are captured (or you ask for staff), the session wraps up and a
   report is generated.

---

## 7. See the results (staff side)

Reports are protected by `STAFF_AUTH_SECRET` (sent as the `X-Staff-Secret` header).

**List sessions**
```bash
curl -H "X-Staff-Secret: <your-secret>" http://localhost:8000/api/sessions
```
**Get a structured JSON report** (use a `session_id` from the list)
```bash
curl -H "X-Staff-Secret: <your-secret>" \
  http://localhost:8000/api/sessions/<session_id>/report
```
**Get the doctor-facing Markdown report**
```bash
curl -H "X-Staff-Secret: <your-secret>" \
  http://localhost:8000/api/sessions/<session_id>/report.md
```
The report opens with the disclaimer *"Automated intake summary — not a diagnosis…"*, the
chief complaint in the patient's own words, HPI, medications/allergies, histories, an URGENT
banner if a red flag fired, and the language used.

### Inspect the database / telemetry directly
The SQLite DB is `backend/opd.db`. Per-turn cost/latency lives in the `telemetry` table
(counts, per-component cost, end-to-end latency — **no clinical content**).

**PowerShell (using the venv's Python, no extra installs):**
```powershell
cd backend
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('opd.db'); [print(r) for r in c.execute('select session_id,turn_index,stt_seconds,llm_input_tokens,llm_output_tokens,tts_characters,round(stt_cost+llm_cost+tts_cost,6) as cost_usd,e2e_latency_ms from telemetry order by id desc limit 20')]"
```
You'll also see a `turn_metered` log line (cost + latency) in the worker terminal after each
turn.

---

## 7A. Compare pipelines (cost vs performance) — the comparison goal

The POC ships **six** pipelines (in `backend/config/pipelines.yaml`) so you can compare provider
combinations on cost and latency:

| Pipeline | STT → LLM → TTS | Keys needed (besides LiveKit) |
|---|---|---|
| `indic_quality` (default) | Sarvam Saaras v3 → GPT-4.1 → Sarvam Bulbul | OPENAI, SARVAM |
| `global_stack` | Deepgram Nova-3 → GPT-4.1 → ElevenLabs Flash | OPENAI, DEEPGRAM, ELEVENLABS |
| `low_cost` | Deepgram Nova-3 → Gemini 2.5 Flash-Lite → Sarvam Bulbul | GOOGLE, DEEPGRAM, SARVAM |
| `global_quality` | Deepgram Nova-3 → Gemini 2.5 Flash → ElevenLabs Flash | GOOGLE, DEEPGRAM, ELEVENLABS |
| `translate_bridge` | Saaras v3 (translate→EN) → GPT-4.1-mini → Sarvam Bulbul | OPENAI, SARVAM |
| `whisper_eval` | OpenAI transcribe → GPT-4.1-mini → Sarvam Bulbul | OPENAI, SARVAM |

**How to run a comparison:**
1. Set the pipeline in `.env`: `ACTIVE_PIPELINE=global_stack` (make sure that pipeline's keys
   are filled in).
2. **Restart the agent worker** (Terminal 2) so it picks up the change.
3. Run one or more intake sessions (§6). Each turn is logged to the `telemetry` table **tagged
   with the pipeline**.
4. Repeat for other pipelines (change `ACTIVE_PIPELINE`, restart, run sessions).
5. View the comparison:

   **CLI** (from `backend/`, venv active):
   ```bash
   python -m telemetry.compare          # text table, cheapest first
   python -m telemetry.compare --csv    # CSV
   ```
   **API** (staff-gated):
   ```bash
   curl -H "X-Staff-Secret: <your-secret>" http://localhost:8000/api/compare
   curl -H "X-Staff-Secret: <your-secret>" http://localhost:8000/api/compare.csv
   ```

   You get per pipeline: **sessions, turns, median cost/intake (USD), p50/p95 end-to-end
   latency (ms), avg completion rate** — i.e. the cost-vs-performance picture.

> **Honest caveat:** comparing live sessions carries patient-to-patient variance. The
> identical-input **offline replay harness** (CLAUDE.md §9.5) and the React scatter dashboard
> are still deferred; `compare.py` / `/api/compare` is their data source. Prices in
> `config/pricing.yaml` are dated and verified, but the ElevenLabs $/char is a plan-dependent
> estimate — set your real rate before trusting absolute cost numbers.

## 8. Run the tests / quality checks

```bash
cd backend
# from an activated venv:
pytest -q                 # 41 tests: red flags, consent gate, cost math, telemetry, report, state, Hindi
ruff check .              # lint
black --check .           # formatting

cd ../frontend
npx tsc --noEmit          # frontend type-check
```

---

## 9. Verification checklist (maps to the plan)

| Capability | How to confirm |
|---|---|
| App boots | `/health` returns ok; all three processes start; `pytest` green |
| Live voice loop | Spoken back-and-forth in the browser; captions render; you can interrupt (barge-in) |
| Intake brain | Fields appear in the panel + persist in `intake_fields`; read-back on meds/allergies |
| Clarification | "I don't understand" → simpler re-ask with an example |
| Consent gate | Decline consent → nothing is collected (and `consent_given=0` in DB) |
| Red-flag safety | "chest pain" → calm "alert staff" + Urgent banner + `urgent_flag=1` in `intake_sessions` |
| Telemetry/cost | `telemetry` table rows with tokens/chars/seconds, per-component cost, e2e latency |
| Report | `/report` (JSON) and `/report.md` carry the disclaimer + chief-complaint quote |
| Hindi | Repeat the flow in हिन्दी; the agent replies in Hindi; report labels are Hindi |
| Pipeline comparison | Run sessions under ≥2 `ACTIVE_PIPELINE` values, then `python -m telemetry.compare` / `GET /api/compare` shows cost + latency per pipeline |

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| **Agent never joins / no greeting** | Make sure **Terminal 2 (worker)** is running and shows `registered worker`. Check `LIVEKIT_URL/API_KEY/API_SECRET` are correct and from the **same** project. |
| **`LiveKit API key/secret not configured` (500 on /api/token)** | Fill `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` in the root `.env`; restart the API. |
| **Mic not working / no audio** | Use Chrome/Edge, allow microphone, and use `http://localhost` (browsers block mic on insecure non-localhost origins). |
| **CORS error in browser console** | Run the frontend on **:5173** (the API allows that origin). If you change the port, update `CORSMiddleware` in `api/main.py`. |
| **No noise cancellation** | Krisp/BVC requires **LiveKit Cloud**. On self-hosted LiveKit the worker logs `krisp_unavailable` and continues without NC. |
| **`download-files` / model errors** | Re-run `python -m livekit.agents download-files` from an activated venv with internet access. |
| **Vite won't start on old Node** | The frontend is pinned to Vite 4 for Node 16; if issues persist, install Node 18 LTS. |
| **Two different `opd.db` files** | Run the API and worker **from `backend/`**, or set an absolute `DATABASE_URL`. |
| **Staff endpoints return 401** | Send the `X-Staff-Secret` header equal to `STAFF_AUTH_SECRET` in `.env`. |
| **OpenAI/Sarvam auth errors in the worker** | Verify `OPENAI_API_KEY` / `SARVAM_API_KEY`, account credit, and model access. |
| **Port already in use** | Change `--port` for uvicorn and `server.port` in `frontend/vite.config.ts`. |

---

## 11. Stop / reset

- Stop each process with **Ctrl+C**.
- To wipe local data, delete `backend/opd.db` (it's recreated on next start).
- Secrets live only in `.env` (git-ignored) — never commit it.

---

## 12. Where things live (quick map)

| Area | Path |
|---|---|
| Settings + config | `backend/config/` (`settings.py`, `pricing.yaml`, `pipelines.yaml`, `voices.yaml`) |
| Provider abstraction | `backend/providers/` |
| Agent worker + brain | `backend/agent/` (`worker.py`, `intake_agent.py`, `prompts.py`) |
| Intake schema/state/safety/report | `backend/intake/` |
| Telemetry/cost | `backend/telemetry/` |
| API | `backend/api/` (`main.py`, `tokens.py`, `sessions.py`) |
| Frontend | `frontend/src/` |
| Per-file explainers | `docs/EXPLAINERS/` |
| Architecture + decisions | `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` |
