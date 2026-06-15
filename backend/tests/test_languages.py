"""Multilingual wiring (en/hi/mr): codes, voice, prompts, report labels, turn detection."""

import uuid

from agent.prompts import build_instructions, greeting_instructions
from config.settings import get_voice
from intake.report import build_report
from intake.state import IntakeState
from providers.registry import supports_turn_detector
from providers.stt_sarvam import _LANG_CODES as STT_CODES
from providers.tts_sarvam import _LANG_CODES as TTS_CODES
from store.db import init_db


def test_sarvam_language_codes_for_hindi() -> None:
    assert STT_CODES["hi"] == "hi-IN"
    assert TTS_CODES["hi"] == "hi-IN"
    assert STT_CODES["en"] == "en-IN"


def test_hindi_voice_configured() -> None:
    voice = get_voice("hi")
    assert voice.get("speaker")


def test_hindi_instructions_are_in_hindi() -> None:
    instr = build_instructions("hi")
    assert "Hindi" in instr  # "Speak ONLY in Hindi"
    # Contains a Hindi (Devanagari) checklist prompt.
    assert "आज आप किस वजह से आए हैं" in instr
    # Greeting instruction references Hindi too.
    assert "Hindi" in greeting_instructions("hi")


def test_report_uses_hindi_labels() -> None:
    init_db()
    state = IntakeState(session_id=f"hi-{uuid.uuid4().hex[:8]}", language="hi")
    state.persist_session()
    state.set_consent(True)
    state.save_field("severity", "8")
    report = build_report(state.session_id)
    # HPI item label for severity should be the Hindi label.
    severity_items = [i for i in report.hpi if i.field_id == "severity"]
    assert severity_items and "गंभीरता" in severity_items[0].label


# --------------------------------------------------------------------- Marathi
def test_sarvam_language_codes_for_marathi() -> None:
    assert STT_CODES["mr"] == "mr-IN"
    assert TTS_CODES["mr"] == "mr-IN"


def test_marathi_voice_configured() -> None:
    assert get_voice("mr").get("speaker")


def test_marathi_instructions_are_in_marathi() -> None:
    instr = build_instructions("mr")
    assert "Marathi" in instr  # "Speak ONLY in Marathi"
    # Contains a Marathi (Devanagari) checklist prompt (chief complaint).
    assert "आज तुम्ही कशासाठी आलात" in instr
    assert "Marathi" in greeting_instructions("mr")


def test_marathi_uses_vad_turn_detection_fallback() -> None:
    # Semantic turn detector covers en/hi but NOT mr -> VAD endpointing fallback.
    assert supports_turn_detector("en") is True
    assert supports_turn_detector("hi") is True
    assert supports_turn_detector("mr") is False


def test_report_uses_marathi_labels() -> None:
    init_db()
    state = IntakeState(session_id=f"mr-{uuid.uuid4().hex[:8]}", language="mr")
    state.persist_session()
    state.set_consent(True)
    state.save_field("severity", "8")
    report = build_report(state.session_id)
    severity_items = [i for i in report.hpi if i.field_id == "severity"]
    assert severity_items and "तीव्रता" in severity_items[0].label
