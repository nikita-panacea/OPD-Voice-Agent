# Explainer — `frontend/src/components/FieldPanel.tsx`

## Purpose
Live "captured so far" panel. Phase C placeholder (empty state); Phase D feeds it real-time
field updates from the agent's `save_intake_field` via the LiveKit data channel.

## Walkthrough
- **`CapturedField`** — exported type `{id,label,value,confirmed}`.
- **`FieldPanel({fields})`** — empty-state hint, else a list of label/value rows with a ✓ when
  the field is confirmed.

## Gotchas / TODOs
- Phase D: subscribe to data-channel messages and map them to `CapturedField[]`.
