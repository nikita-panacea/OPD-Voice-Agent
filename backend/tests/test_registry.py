"""Registry tests: all comparison providers registered + every pipeline resolves."""

from config.settings import load_pipelines
from providers import registry


def test_all_comparison_providers_registered() -> None:
    assert {"sarvam", "deepgram", "whisper"} <= set(registry.STT_PROVIDERS)
    assert {"openai", "google"} <= set(registry.LLM_PROVIDERS)
    assert {"sarvam", "elevenlabs"} <= set(registry.TTS_PROVIDERS)


def test_every_pipeline_resolves_its_providers() -> None:
    pipelines = load_pipelines()["pipelines"]
    assert pipelines, "no pipelines configured"
    for cfg in pipelines.values():
        # _resolve raises a clear KeyError if a stage names an unregistered provider.
        registry._resolve(registry.STT_PROVIDERS, cfg["stt"], "STT")
        registry._resolve(registry.LLM_PROVIDERS, cfg["llm"], "LLM")
        registry._resolve(registry.TTS_PROVIDERS, cfg["tts"], "TTS")


def test_unregistered_provider_fails_fast() -> None:
    import pytest

    with pytest.raises(KeyError):
        registry._resolve(registry.STT_PROVIDERS, {"provider": "nope"}, "STT")
