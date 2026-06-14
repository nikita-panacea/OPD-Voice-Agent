"""Cost-math tests against the dated prices in config/pricing.yaml."""

import pytest

from telemetry.cost import llm_cost, stt_cost, tts_cost


def test_stt_cost_per_second() -> None:
    # Sarvam Saaras v3 = $0.000092/sec
    assert stt_cost(60, "sarvam/saaras:v3") == pytest.approx(60 * 0.000092)


def test_llm_cost_input_and_output() -> None:
    # GPT-4.1 = $2/M in, $8/M out
    assert llm_cost(1_000_000, 0, "openai/gpt-4.1") == pytest.approx(2.00)
    assert llm_cost(0, 1_000_000, "openai/gpt-4.1") == pytest.approx(8.00)
    assert llm_cost(1000, 500, "openai/gpt-4.1") == pytest.approx((1000 * 2 + 500 * 8) / 1e6)


def test_tts_cost_per_character() -> None:
    # Sarvam Bulbul = $0.0000165/char
    assert tts_cost(10_000, "sarvam/bulbul:v2") == pytest.approx(10_000 * 0.0000165)


def test_missing_price_returns_zero() -> None:
    # Sarvam LLM token price is intentionally null in pricing.yaml (TODO).
    assert llm_cost(1000, 1000, "sarvam/sarvam-30b") == 0.0
    # Unknown key also resolves to 0 (with a warning).
    assert stt_cost(10, "nonexistent/model") == 0.0
