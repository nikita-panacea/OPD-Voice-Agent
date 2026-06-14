# Explainer — `frontend/src/components/MicIndicator.tsx`

## Purpose
Visual state of the conversation: assistant speaking, listening to the patient, or idle.

## Walkthrough
- **`MicIndicator({agentSpeaking, patientSpeaking})`** — picks a label + CSS dot class from the
  two booleans (agent speaking > patient speaking > idle) and renders an animated dot + text.

## Gotchas / TODOs
- Driven by `ActiveSpeakersChanged`; brief flicker is possible at turn boundaries.
