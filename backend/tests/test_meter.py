"""Tests for the pure-Python ProviderMeter (no LiveKit needed)."""

from providers.base import BillableUnits, ProviderMeter, Stage


class _FakeSTTMetrics:
    audio_duration = 3.5


class _FakeLLMMetrics:
    prompt_tokens = 120
    completion_tokens = 45
    prompt_cached_tokens = 100


class _FakeTTSMetrics:
    characters_count = 88


def test_stt_meter_extracts_seconds() -> None:
    meter = ProviderMeter(Stage.STT, "sarvam", "saaras:v3", "sarvam/saaras:v3")
    units = meter.billable_units(_FakeSTTMetrics())
    assert units == BillableUnits(stage=Stage.STT, stt_seconds=3.5)


def test_llm_meter_extracts_tokens() -> None:
    meter = ProviderMeter(Stage.LLM, "openai", "gpt-4.1", "openai/gpt-4.1")
    units = meter.billable_units(_FakeLLMMetrics())
    assert units.llm_input_tokens == 120
    assert units.llm_output_tokens == 45
    assert units.llm_cached_tokens == 100


def test_tts_meter_extracts_characters() -> None:
    meter = ProviderMeter(Stage.TTS, "sarvam", "bulbul:v2", "sarvam/bulbul:v2")
    units = meter.billable_units(_FakeTTSMetrics())
    assert units.tts_characters == 88


def test_meter_accepts_dict_metrics_and_defaults_zero() -> None:
    meter = ProviderMeter(Stage.LLM, "openai", "gpt-4.1", "openai/gpt-4.1")
    # alternate field name + missing fields -> defaults to 0
    units = meter.billable_units({"input_tokens": 10})
    assert units.llm_input_tokens == 10
    assert units.llm_output_tokens == 0
    assert units.llm_cached_tokens == 0
