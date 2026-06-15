"""Deterministic red-flag detection (CLAUDE.md §2.2) — the mandatory safety backstop.

The LLM is instructed to call `flag_urgent` on emergencies, but we do NOT rely on that alone.
This module scans every patient utterance (en + hi + mr + common code-mix terms) for red-flag
phrases and triggers escalation independently. It deliberately errs toward escalation: missing
an emergency is far worse than a false alarm, and the LLM path handles nuance.

Pure Python (no LiveKit), so it is thoroughly unit-tested (`tests/test_red_flags.py`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RedFlag:
    """A detected red flag: the clinical category + the phrase that matched."""

    category: str
    term: str
    advice: str


# Localized, calm "alert staff now" messages (spoken by the agent on escalation).
ESCALATION_MESSAGE = {
    "en": (
        "This may need urgent attention. Please alert the hospital staff next to you right now, "
        "or call for immediate help. I've flagged this for the care team."
    ),
    "hi": (
        "इस पर तुरंत ध्यान देने की ज़रूरत हो सकती है। कृपया अभी अपने पास मौजूद अस्पताल के स्टाफ़ को बताएं "
        "या तुरंत मदद के लिए पुकारें। मैंने इसे देखभाल टीम के लिए चिह्नित कर दिया है।"
    ),
    "mr": (
        "याकडे तातडीने लक्ष देण्याची गरज असू शकते. कृपया लगेच तुमच्या जवळच्या रुग्णालयातील "
        "कर्मचाऱ्यांना सांगा किंवा तातडीच्या मदतीसाठी हाक मारा. मी हे काळजी घेणाऱ्या टीमसाठी "
        "चिन्हांकित केले आहे."
    ),
}

# Category -> list of lowercase trigger phrases (English + Hindi + Marathi + Romanized code-mix).
RED_FLAG_TERMS: dict[str, list[str]] = {
    "chest_pain": [
        "chest pain",
        "pain in my chest",
        "chest is tight",
        "tightness in my chest",
        "pressure in my chest",
        "crushing",
        "सीने में दर्द",
        "छाती में दर्द",
        "seene mein dard",
        "chhati mein dard",
        # Marathi (short roots so common intensifiers like "खूप" between words still match)
        "छातीत दुख",
        "छातीत खूप दुख",
        "छाती दुख",
        "छातीवर दाब",
        "chhatit dukh",
    ],
    "breathing": [
        "can't breathe",
        "cannot breathe",
        "can not breathe",
        "trouble breathing",
        "difficulty breathing",
        "short of breath",
        "breathless",
        "gasping",
        "choking",
        "साँस नहीं",
        "सांस लेने में",
        "दम घुट",
        "saans nahi",
        "dam ghut",
        # Marathi
        "श्वास घेता येत नाही",
        "दम लागतोय",
        "धाप लागते",
        "धाप लागतेय",
        "shvas gheta yet nahi",
    ],
    "stroke": [
        "face drooping",
        "slurred speech",
        "can't speak",
        "weakness on one side",
        "one side of my body",
        "numb on one side",
        "लकवा",
        "चेहरा टेढ़ा",
        "बोलने में दिक्कत",
        "ek taraf",
        "lakwa",
        # Marathi
        "चेहरा वाकडा",
        "एका बाजूला अशक्तपणा",
        "बोलता येत नाही",
        "एका बाजूला बधिर",
    ],
    "severe_bleeding": [
        "bleeding heavily",
        "lot of blood",
        "won't stop bleeding",
        "blood won't stop",
        "बहुत खून",
        "खून बंद नहीं",
        "bahut khoon",
        # Marathi
        "खूप रक्त",
        "रक्त थांबत नाही",
        "रक्तस्राव",
        "khup rakt",
    ],
    "anaphylaxis": [
        "throat closing",
        "throat is closing",
        "can't swallow",
        "swelling of my face",
        "face is swelling",
        "tongue swelling",
        "anaphylaxis",
        "गला बंद",
        "गला बंद हो",
        "gala band",
        # Marathi
        "घसा बंद",
        "घसा आवळतोय",
        "चेहरा सुजला",
        "जीभ सुजली",
        "ghsa band",
    ],
    "loss_of_consciousness": [
        "passed out",
        "fainted",
        "blacked out",
        "unconscious",
        "बेहोश",
        "behosh",
        # Marathi
        "बेशुद्ध",
        "चक्कर येऊन पडलो",
        "शुद्ध हरपली",
        "beshuddha",
    ],
    "self_harm": [
        "kill myself",
        "end my life",
        "suicide",
        "suicidal",
        "hurt myself",
        "harm myself",
        "don't want to live",
        "जान देना",
        "खुदकुशी",
        "आत्महत्या",
        "khudkushi",
        "jaan dena",
        # Marathi
        "स्वतःला संपवाव",
        "जगावंसं वाटत नाही",
        "आत्महत्या करावी",
        "स्वतःला इजा",
    ],
}


def detect(text: str, language: str = "en") -> RedFlag | None:
    """Return the first red flag found in `text`, or None.

    Conservative: any trigger phrase present anywhere is a hit (no negation handling — see
    module docstring). Matching is case-insensitive substring (works for Latin + Devanagari).
    """
    if not text:
        return None
    low = text.lower()
    advice = ESCALATION_MESSAGE.get(language, ESCALATION_MESSAGE["en"])
    for category, terms in RED_FLAG_TERMS.items():
        for term in terms:
            if term.lower() in low:
                return RedFlag(category=category, term=term, advice=advice)
    return None
