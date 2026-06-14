# Explainer — `frontend/src/lib/livekit.ts`

## Purpose
All LiveKit browser integration: fetch a join token from the backend and own the `Room`
(connect, publish mic, play the agent's audio, collect live captions, track who's speaking).
Built directly on `livekit-client` for a stable, explicit API (see ADR-0005).

## Dependencies & data in/out
- **Imports:** React hooks; `livekit-client` (`Room`, `RoomEvent`, `Track`, types).
- **In:** language code. **Out:** connection status, captions, speaking flags, connect/disconnect.

## Walkthrough
- **`fetchToken(language)`** — `POST /api/token`; returns `{token, url, room, identity, language}`.
- **`useIntakeRoom()`** — the hook the UI uses:
  - holds the `Room` in a ref + state for `status`, `error`, `captions`, `fields`, `urgent`,
    `completed`, `agentSpeaking`, `patientSpeaking`.
  - **`connect(language)`** — fetches a token, creates a `Room`, wires events:
    - `TrackSubscribed` → attach remote audio to a hidden `<audio>` element (agent voice).
    - `TranscriptionReceived` → upsert caption segments by id; speaker = patient if the
      participant identity equals the local identity, else agent.
    - `ActiveSpeakersChanged` → set patient/agent speaking flags.
    - `DataReceived` (topic `intake`) → JSON messages from the agent: `field_update` upserts a
      live field; `urgent` sets the urgent reason; `complete` sets completed; `handoff` sets the
      staff-handoff flag.
    - `Disconnected` / `ConnectionStateChanged` → update status.
    - then `room.connect(url, token)` and `setMicrophoneEnabled(true)`.
  - **`disconnect()`** — disconnects and resets.
  - **cleanup** — disconnects on unmount.

## Gotchas / TODOs
- Caption speaker detection relies on participant identity; agent identity differs from the
  patient's `patient-xxxx`.
- Audio elements are appended to `document.body` (hidden); they're cleaned up when the track
  ends / room disconnects.
- Interim vs final captions come from `segment.final`.
