"""LiveKit access-token minting for the browser client.

The frontend calls `POST /api/token` with the chosen language; we return a short-lived JWT
that lets the patient join a fresh room. The chosen language is stored in the participant's
attributes so the agent worker (`_resolve_language`) can pick the right STT/TTS language.

The agent worker auto-dispatches to any room (ServerType.ROOM), so no explicit agent dispatch
is needed here.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from livekit import api
from pydantic import BaseModel

from config.settings import get_settings

router = APIRouter(prefix="/api", tags=["tokens"])

SUPPORTED_LANGUAGES = {"en", "hi"}


class TokenRequest(BaseModel):
    """Body for a token request."""

    language: str = "en"
    room: str | None = None


class TokenResponse(BaseModel):
    """A LiveKit join token + the room/identity it is scoped to."""

    token: str
    url: str
    room: str
    identity: str
    language: str


def create_access_token(room: str, identity: str, language: str) -> str:
    """Mint a LiveKit JWT scoped to `room`, embedding `language` in participant attributes."""
    settings = get_settings()
    if not (settings.livekit_api_key and settings.livekit_api_secret):
        raise HTTPException(status_code=500, detail="LiveKit API key/secret not configured")

    grants = api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True)
    return (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name("Patient")
        .with_grants(grants)
        .with_attributes({"language": language})
        .with_ttl(timedelta(minutes=30))
        .to_jwt()
    )


@router.post("/token", response_model=TokenResponse)
def issue_token(req: TokenRequest) -> TokenResponse:
    """Issue a join token for a new (or named) intake room."""
    language = req.language if req.language in SUPPORTED_LANGUAGES else "en"
    room = req.room or f"opd-intake-{uuid.uuid4().hex[:8]}"
    identity = f"patient-{uuid.uuid4().hex[:8]}"
    token = create_access_token(room, identity, language)
    return TokenResponse(
        token=token,
        url=get_settings().livekit_url,
        room=room,
        identity=identity,
        language=language,
    )
