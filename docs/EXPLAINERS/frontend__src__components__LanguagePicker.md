# Explainer — `frontend/src/components/LanguagePicker.tsx`

## Purpose
Pre-join language selector (English, Hindi, Marathi).

## Walkthrough
- **`LANGUAGES`** — exported list of `{code,label}` (en, hi, mr). Single source for the dropdown.
- **`LanguagePicker({value,onChange,disabled})`** — controlled `<select>`; calls `onChange`
  with the chosen code.

## Gotchas / TODOs
- Keep this list in sync with `SUPPORTED_LANGUAGES` in the worker + token API.
