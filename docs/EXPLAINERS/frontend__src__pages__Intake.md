# Explainer — `frontend/src/pages/Intake.tsx`

## Purpose
The patient-facing screen: pick a language, connect, and converse with the agent. Shows the
consent/identity disclaimer, live captions, a speaking/listening indicator, and the
captured-fields panel.

## Dependencies & data in/out
- **Imports:** `useIntakeRoom` (lib/livekit), `LanguagePicker`, `MicIndicator`,
  `TranscriptView`, `FieldPanel`.

## Walkthrough
- **`Intake()`** — local `language` state; pulls `status`, `error`, `captions`,
  `agentSpeaking`, `patientSpeaking`, `connect`, `disconnect` from `useIntakeRoom()`.
  - Always renders the header + **disclaimer** (honesty/consent framing, §2).
  - **Pre-join** (not connected): `LanguagePicker` + Start button (calls `connect(language)`);
    shows errors.
  - **In session** (connected): `MicIndicator`, `TranscriptView`, an End button
    (`disconnect`), and the `FieldPanel`.
  - `fields` is empty in Phase C (live field updates wired in Phase D).

## Gotchas / TODOs
- The on-screen disclaimer complements (does not replace) the agent's spoken consent gate
  (Phase E).
- Phase D feeds real captured fields into `FieldPanel` from the agent's data channel.
