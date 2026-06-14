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


def stt_cost(seconds: float, pricing_key: str) -> float:
    """USD cost for STT audio seconds."""
    return round(seconds * _price("stt", pricing_key, "usd_per_second"), 8)


def llm_cost(input_tokens: int, output_tokens: int, pricing_key: str) -> float:
    """USD cost for LLM input + output tokens (per-1M pricing)."""
    in_price = _price("llm", pricing_key, "usd_per_1m_input")
    out_price = _price("llm", pricing_key, "usd_per_1m_output")
    return round((input_tokens * in_price + output_tokens * out_price) / 1_000_000, 8)


def tts_cost(characters: int, pricing_key: str) -> float:
    """USD cost for TTS characters synthesized."""
    return round(characters * _price("tts", pricing_key, "usd_per_character"), 8)
