from intake.prompt_audio import PromptAudioResolver


def test_resolves_existing_prompt_audio(tmp_path) -> None:
    out_dir = tmp_path / "en"
    out_dir.mkdir()
    (out_dir / "q01_consent.wav").write_bytes(b"wav")

    prompt = PromptAudioResolver(tmp_path).resolve("consent", "en")

    assert prompt is not None
    assert prompt.field_id == "consent"
    assert prompt.variant == "prompt"
    assert prompt.url == "/audio/en/q01_consent.wav"
    assert "automated assistant" in prompt.text.lower()


def test_resolves_simpler_variant_with_suffix(tmp_path) -> None:
    out_dir = tmp_path / "en"
    out_dir.mkdir()
    (out_dir / "q07_severity_simpler.wav").write_bytes(b"wav")

    prompt = PromptAudioResolver(tmp_path).resolve("severity", "en", "simpler")

    assert prompt is not None
    assert prompt.url == "/audio/en/q07_severity_simpler.wav"
    assert prompt.variant == "simpler"


def test_missing_prompt_audio_returns_none(tmp_path) -> None:
    assert PromptAudioResolver(tmp_path).resolve("consent", "mr") is None
    assert PromptAudioResolver(tmp_path).resolve("unknown", "en") is None
    assert PromptAudioResolver(tmp_path).resolve("consent", "en", "repeat") is None
