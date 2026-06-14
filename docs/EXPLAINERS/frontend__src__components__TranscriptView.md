# Explainer — `frontend/src/components/TranscriptView.tsx`

## Purpose
Renders the live transcript as ordered patient/agent bubbles; auto-scrolls to the newest line.

## Walkthrough
- **`TranscriptView({captions})`** — empty-state hint when no captions; maps each `Caption` to a
  bubble (`who` label + text, dimmed/italic when interim/not final). A `useEffect` scrolls the
  bottom anchor into view whenever captions change.

## Gotchas / TODOs
- Interim segments update in place (keyed by id) before becoming final.
