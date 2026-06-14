# Explainer — `frontend/src/components/LanguagePicker.tsx`

## Purpose
Pre-join language selector (POC: English + Hindi).

## Walkthrough
- **`LANGUAGES`** — exported list of `{code,label}` (en, hi). Single source for the dropdown.
- **`LanguagePicker({value,onChange,disabled})`** — controlled `<select>`; calls `onChange`
  with the chosen code.

## Gotchas / TODOs
- Add `mr` here when Marathi is supported (post-POC).
