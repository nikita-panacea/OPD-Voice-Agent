# Explainer — `backend/api/tokens.py`

## Purpose
Mints short-lived LiveKit join tokens for the browser client and embeds the chosen language so
the worker can pick the right STT/TTS language. The agent auto-dispatches to any room, so no
explicit dispatch is needed.

## Dependencies & data in/out
- **Imports:** `fastapi` (APIRouter/HTTPException), `livekit.api` (AccessToken/VideoGrants),
  `pydantic`, `config.settings`.
- **In:** `POST /api/token {language, room?}`. **Out:** `{token, url, room, identity, language}`.

## Walkthrough
- **`TokenRequest` / `TokenResponse`** — Pydantic request/response models.
- **`create_access_token(room, identity, language)`** — validates LiveKit key/secret are set
  (500 if not); builds `VideoGrants(room_join=True, room=..., can_publish, can_subscribe)`;
  constructs `AccessToken(...).with_identity().with_name().with_grants().with_attributes(
  {"language": language}).with_ttl(30 min).to_jwt()`. Verified against `livekit-api 1.1.0`.
- **`issue_token(req)`** (`POST /api/token`) — clamps language to supported set; generates a
  random room (`opd-intake-xxxx`) + identity (`patient-xxxx`) unless a room is provided; mints
  and returns the token + `LIVEKIT_URL`.

## Gotchas / TODOs
- 30-minute TTL is fine for one intake; lengthen for very long sessions.
- No patient auth in the POC — anyone who can reach the API can get a token. Phase 9 hardening.
- `with_attributes` is how the worker learns the language (see `worker._resolve_language`).
