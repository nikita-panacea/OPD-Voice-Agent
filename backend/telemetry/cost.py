"""Cost math (CLAUDE.md §9.2): billable units × dated unit prices from `pricing.yaml`.

Data-driven so updating a price never touches code, and historical sessions can be re-costed.
Missing prices resolve to 0.0 with a warning (e.g. Sarvam-LLM tokens / ElevenLabs $/char are
unset TODOs in the POC). Pure Python, unit-testable.
"""

from __future__ import annotations

from config.settings import load_pricing
from logging_setup import get_logger

log = get_logger(__name__)


def _price(section: str, pricing_key: str, unit_field: str) -> float:
    """Look up a unit price; warn + return 0.0 if missing/null."""
    entry = load_pricing().get(section, {}).get(pricing_key)
    if not entry or entry.get(unit_field) is None:
        log.warning("price_missing", section=section, key=pricing_key, field=unit_field)
        return 0.0
    return float(entry[unit_field])


def _cached_input_price(pricing_key: str, default: float) -> float:
    """Cached-input price for an LLM; falls back to `default` (full input) if unset.

    No warning on miss — `usd_per_1m_cached_input` is optional (not every model is cached).
    """
    entry = load_pricing().get("llm", {}).get(pricing_key)
    if not entry or entry.get("usd_per_1m_cached_input") is None:
        return default
    return float(entry["usd_per_1m_cached_input"])


def stt_cost(seconds: float, pricing_key: str) -> float:
    """USD cost for STT audio seconds."""
    return round(seconds * _price("stt", pricing_key, "usd_per_second"), 8)


def llm_cost(
    input_tokens: int,
    output_tokens: int,
    pricing_key: str,
    cached_tokens: int = 0,
) -> float:
    """USD cost for LLM tokens, applying the prompt-cache discount.

    `cached_tokens` is the portion of `input_tokens` served from the prompt cache (LiveKit's
    `prompt_tokens` is the total input, `prompt_cached_tokens` the cached subset). Cached tokens
    are billed at `usd_per_1m_cached_input` (≈0.25x input for OpenAI, ≈0.10x for Gemini); the
    remaining fresh input tokens at the full input price. `cached_tokens=0` reproduces the
    no-caching cost, so callers/tests that omit it are unaffected.
    """
    in_price = _price("llm", pricing_key, "usd_per_1m_input")
    out_price = _price("llm", pricing_key, "usd_per_1m_output")
    cached_price = _cached_input_price(pricing_key, in_price)
    cached = max(0, min(cached_tokens, input_tokens))
    fresh = input_tokens - cached
    total = fresh * in_price + cached * cached_price + output_tokens * out_price
    return round(total / 1_000_000, 8)


def tts_cost(characters: int, pricing_key: str) -> float:
    """USD cost for TTS characters synthesized."""
    return round(characters * _price("tts", pricing_key, "usd_per_character"), 8)


def livekit_cost(
    session_seconds: float,
    human_participants: int = 1,
    pricing_key: str = "livekit/cloud",
) -> float:
    """USD LiveKit Cloud transport cost for one session.

    Cost = minutes * (agent_session_minute + human_participants * participant_minute). One
    agent + one patient is the default. Per-minute, so it scales with session length, not turns.
    """
    minutes = session_seconds / 60.0
    agent_rate = _price("livekit", pricing_key, "usd_per_agent_minute")
    participant_rate = _price("livekit", pricing_key, "usd_per_participant_minute")
    return round(minutes * (agent_rate + human_participants * participant_rate), 8)
