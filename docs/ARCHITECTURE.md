# Architecture

Cascaded pipeline (STT → LLM → TTS), **not** speech-to-speech — chosen so every provider is
swappable, separately cost-metered, and debuggable (CLAUDE.md §3). POC runs one pipeline
(`indic_quality`) on LiveKit Cloud.

## Pipeline (POC)

```mermaid
flowchart LR
    mic["Patient mic\n(browser)"] -->|WebRTC| room["LiveKit Cloud Room"]
    room --> krisp["Krisp BVC\nnoise cancellation"]
    krisp --> vad["Silero VAD"]
    vad --> turn["Turn Detector\n(MultilingualModel)"]
    turn --> stt["STT\nSarvam Saaras v3"]
    stt -->|transcript| llm["LLM intake brain\nGPT-4.1\n+ save_intake_field\n+ consent / red-flag"]
    llm -->|reply text| tts["TTS\nSarvam Bulbul"]
    tts -->|audio| room
    room -->|audio out| ear["Patient ear"]

    llm -.per-turn.-> meter["Telemetry meter\n(sec / tokens / chars / latency)"]
    meter --> store["SQLite session store"]
    store --> report["JSON + Markdown\nintake report (disclaimer)"]
```

Notes:
- **Krisp BVC** requires LiveKit Cloud (verified 2026-06-14). Applied once on the input track
  via `RoomInputOptions(noise_cancellation=...)`; client-side noise filter is disabled.
- **Languages: en + hi + mr.** The semantic `MultilingualModel` turn detector covers en/hi but
  **not Marathi** (verified against the installed model). So Marathi sessions fall back to
  **VAD endpointing** (`turn_detection="vad"`); STT/TTS handle Marathi natively (Sarvam `mr-IN`).
  Turn handling is configured via `TurnHandlingOptions(endpointing=EndpointingOptions(...))`.
- The meter records counts/cost/latency only — **never clinical content** (§9).

## Conversation state machine (intake brain)

```mermaid
stateDiagram-v2
    [*] --> Greeting
    Greeting --> Consent: introduce as automated assistant
    Consent --> Identity: consent = yes
    Consent --> Handoff: consent = no
    Identity --> ComplaintLoop

    state ComplaintLoop {
        [*] --> Ask
        Ask --> Listen
        Listen --> Clarify: confused / off-topic / silent / low ASR conf
        Clarify --> Listen: re-ask with simpler_prompt + example
        Listen --> Save: answer understood
        Save --> Confirm: critical field (meds / allergies / chief complaint)
        Confirm --> Ask: next field
        Save --> Ask: non-critical field
    }

    ComplaintLoop --> HistoryLoop
    HistoryLoop --> Wrapup: all required fields filled

    Wrapup --> Report
    Report --> [*]

    note right of ComplaintLoop
        Red-flag monitor is ALWAYS on.
        Any red-flag utterance -> RAISE URGENT flag
        + calm "alert staff now" + stop intake-as-usual.
    end note
```

The red-flag monitor and the consent gate are enforced as explicit code paths
(`intake/red_flags.py`, the consent check in `agent/intake_agent.py`), not just prompt text.
