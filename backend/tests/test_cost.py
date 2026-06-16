"""Cost-math tests against the dated prices in config/pricing.yaml."""

import pytest

from telemetry.cost import livekit_cost, llm_cost, stt_cost, tts_cost


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


def test_llm_cost_applies_cached_discount() -> None:
    # GPT-4.1-mini: input $0.40, cached $0.10 per 1M. 1000 input, 800 cached, 0 output.
    expected = (200 * 0.40 + 800 * 0.10) / 1e6
    assert llm_cost(1000, 0, "openai/gpt-4.1-mini", cached_tokens=800) == pytest.approx(expected)


def test_cached_zero_matches_full_input_price() -> None:
    # cached_tokens=0 (the default) must reproduce the no-caching cost.
    assert llm_cost(1000, 500, "openai/gpt-4.1-mini", cached_tokens=0) == llm_cost(
        1000, 500, "openai/gpt-4.1-mini"
    )


def test_caching_is_cheaper_than_no_caching() -> None:
    no_cache = llm_cost(10_000, 100, "google/gemini-2.5-flash")
    with_cache = llm_cost(10_000, 100, "google/gemini-2.5-flash", cached_tokens=8_000)
    assert with_cache < no_cache


def test_livekit_cost_per_minute() -> None:
    # $0.01/agent-min + $0.0004/participant-min; 60s = 1 min, 1 patient.
    assert livekit_cost(60) == pytest.approx(0.01 + 0.0004)
    assert livekit_cost(120) == pytest.approx(2 * (0.01 + 0.0004))
    assert livekit_cost(0) == 0.0


def test_cached_tokens_capped_at_input() -> None:
    # cached can't exceed input — overshoot is clamped.
    capped = llm_cost(1000, 0, "google/gemini-2.5-flash", cached_tokens=5000)
    all_cached = llm_cost(1000, 0, "google/gemini-2.5-flash", cached_tokens=1000)
    assert capped == all_cached == pytest.approx(1000 * 0.03 / 1e6)
