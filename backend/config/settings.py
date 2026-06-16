"""Environment-driven settings + YAML config loaders for the OPD intake backend.

This module is the single source of truth for runtime configuration:
  * secrets / env vars  -> `Settings` (pydantic-settings, reads the project-root `.env`)
  * pricing / pipelines / voices -> YAML files in this directory, loaded + cached here

Everything else imports `get_settings()` and the `load_*` helpers rather than reading
env vars or YAML directly, so configuration stays centralized and testable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# config/ dir (this file) and the project root (two levels up: backend/ -> root).
CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parents[1]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Typed view over environment variables (documented in `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LiveKit Cloud (transport; Krisp BVC requires Cloud) ---
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # --- LLM providers ---
    openai_api_key: str = ""
    google_api_key: str = ""  # optional in POC (Gemini alt brain)
    sarvam_api_key: str = ""

    # --- Speech providers available but deferred in POC ---
    deepgram_api_key: str = ""
    elevenlabs_api_key: str = ""

    # --- App ---
    database_url: str = "sqlite:///./opd.db"
    active_pipeline: str = "indic_quality"
    data_retention_days: int = 30
    staff_auth_secret: str = "dev-staff-secret"  # POC only; not production-secure
    log_level: str = "INFO"
    persist_transcript: bool = True  # store the full conversation transcript (PHI). See §9.


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide `Settings` singleton (cached)."""
    return Settings()


def _load_yaml(name: str) -> dict[str, Any]:
    """Load and parse a YAML file from the config directory."""
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache
def load_pricing() -> dict[str, Any]:
    """Return parsed `pricing.yaml` (dated unit prices per provider/model)."""
    return _load_yaml("pricing.yaml")


@lru_cache
def load_pipelines() -> dict[str, Any]:
    """Return parsed `pipelines.yaml` (named STT/LLM/TTS triples)."""
    return _load_yaml("pipelines.yaml")


@lru_cache
def load_voices() -> dict[str, Any]:
    """Return parsed `voices.yaml` (per-language TTS voice IDs)."""
    return _load_yaml("voices.yaml")


def get_pipeline(name: str) -> dict[str, Any]:
    """Return the config block for a named pipeline, or raise if it is unknown."""
    pipelines = load_pipelines().get("pipelines", {})
    if name not in pipelines:
        known = ", ".join(sorted(pipelines)) or "<none>"
        raise KeyError(f"Unknown pipeline '{name}'. Known pipelines: {known}")
    return pipelines[name]


def get_voice(language: str) -> dict[str, Any]:
    """Return the voice config for a language, falling back to `default`."""
    voices = load_voices()
    return voices.get("voices", {}).get(language) or voices.get("default", {})
