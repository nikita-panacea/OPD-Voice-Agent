"""Intake field schema (CLAUDE.md §8.1) — the goal-driven checklist the agent fills.

Each field has a canonical English `prompt` + a plain-language `simpler_prompt` (with an
example) used when the patient is confused, plus Hindi and Marathi translations. Per §7,
English is canonical and the hi/mr translations are LLM-authored and marked
`needs_clinical_review` — a Hindi/Marathi-speaking clinician must review medical phrasing before
real use. The whole §8.1 set is also marked for clinical review (per the POC decision).

This module is pure data + helpers (no LiveKit), so it is unit-testable.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FieldType(StrEnum):
    """How an answer is captured (drives validation + UI hints)."""

    FREE_TEXT = "free_text"
    SCALE_0_10 = "scale_0_10"
    YES_NO = "yes_no"
    ENUM = "enum"
    LIST = "list"


class IntakeField(BaseModel):
    """One item on the intake checklist."""

    id: str
    ftype: FieldType
    required: bool = True
    critical: bool = False  # read back + confirm (medications, allergies, chief complaint)
    is_consent_gate: bool = False
    red_flag_check: bool = False
    needs_clinical_review: bool = True
    label: dict[str, str]  # short label for the UI field panel
    prompt: dict[str, str]  # how the agent asks (per language)
    simpler_prompt: dict[str, str]  # plain re-ask with an example (per language)
    enum_options: list[str] = Field(default_factory=list)


def localized(d: dict[str, str], language: str) -> str:
    """Return the language variant, falling back to English."""
    return d.get(language) or d["en"]


# ---------------------------------------------------------------------------
# The 17-field default OPD intake set (§8.1). en + hi + mr; all need clinical review.
# ---------------------------------------------------------------------------
INTAKE_FIELDS: list[IntakeField] = [
    IntakeField(
        id="consent",
        ftype=FieldType.YES_NO,
        is_consent_gate=True,
        label={"en": "Consent", "hi": "सहमति", "mr": "संमती"},
         prompt={
            "en": "Hello, I am Dhara, an automated assistant collecting your intake information for "
            "the care team. Your answers are recorded and transcribed for the doctor. Do you "
            "agree to continue? Please press the button and say yes or no.",
            "hi": "नमस्ते, मैं धारा हूँ, एक स्वचालित सहायिका जो देखभाल टीम के लिए आपकी जानकारी एकत्र कर रही हूँ। "
            "आपके उत्तर रिकॉर्ड और लिखे जाते हैं। क्या आप जारी रखने के लिए सहमत हैं? बटन दबाकर हाँ या ना कहें।",
            "mr": "नमस्कार, मी धारा, एक स्वयंचलित सहाय्यिका जी काळजी पथकासाठी तुमची माहिती गोळा करत आहे. "
            "तुमची उत्तरे रेकॉर्ड व लिहिली जातात. तुम्ही पुढे जाण्यास सहमत आहात का? बटण दाबून हो किंवा नाही म्हणा.",
        },
        simpler_prompt={
            "en": "Is it okay for me to ask you some health questions and save your answers for "
            "the doctor? Please press the button and say yes or no.",
            "hi": "क्या मैं आपसे कुछ स्वास्थ्य प्रश्न पूछ सकती हूँ और उत्तर डॉक्टर के लिए सहेज सकती हूँ? हाँ या ना कहें।",
            "mr": "मी तुम्हाला काही आरोग्यविषयक प्रश्न विचारू का आणि उत्तरे डॉक्टरांसाठी जतन करू का? हो किंवा नाही म्हणा.",
        },
    ),
    IntakeField(
        id="identity",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Patient", "hi": "मरीज़", "mr": "रुग्ण"},
         prompt={
            "en": "Please tell me your full name and age.",
            "hi": "कृपया मुझे अपना पूरा नाम और उम्र बताएं।",
            "mr": "कृपया तुमचे पूर्ण नाव आणि वय सांगा.",
        },
        simpler_prompt={
            "en": "What is your name, and how old are you? For example: 'Asha Patil, 45 years'.",
            "hi": "आपका नाम क्या है, और आपकी उम्र कितनी है? उदाहरण: 'आशा पाटिल, 45 वर्ष'।",
            "mr": "तुमचे नाव काय आहे आणि तुमचे वय किती आहे? उदाहरण: 'आशा पाटील, ४५ वर्षे'.",
        },
    ),
    IntakeField(
        id="chief_complaint",
        ftype=FieldType.FREE_TEXT,
        critical=True,
        label={"en": "Chief complaint", "hi": "मुख्य शिकायत", "mr": "मुख्य तक्रार"},
        prompt={
            "en": "What is the main issue that brought you in today?",
            "hi": "आज आप किस मुख्य समस्या के कारण आए हैं?",
            "mr": "आज तुम्ही कोणत्या मुख्य त्रासामुळे आला आहात?",
        },
        simpler_prompt={
            "en": "What is bothering you the most? For example: 'chest pain' or 'fever for 3 days'.",
            "hi": "आपको सबसे ज़्यादा क्या परेशान कर रहा है? उदाहरण: 'सीने में दर्द' या '3 दिन से बुखार'।",
            "mr": "तुम्हाला सर्वात जास्त काय त्रास होतोय? उदाहरण: 'छातीत दुखणे' किंवा '३ दिवसांपासून ताप'.",
        },
    ),
    IntakeField(
        id="onset_duration",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Onset / duration", "hi": "शुरुआत / अवधि", "mr": "सुरुवात / कालावधी"},
        prompt={
            "en": "When did this start, and how long has it been going on?",
            "hi": "यह कब शुरू हुआ, और कब से हो रहा है?",
            "mr": "हे कधी सुरू झाले आणि किती काळापासून आहे?",
        },
        simpler_prompt={
            "en": "Did it start today, a few days ago, or longer? For example: 'since this morning'.",
            "hi": "क्या यह आज शुरू हुआ, कुछ दिन पहले, या उससे पहले? उदाहरण: 'आज सुबह से'।",
            "mr": "हे आज सुरू झाले, काही दिवसांपूर्वी, की त्याहून आधी? उदाहरण: 'आज सकाळपासून'.",
        },
    ),
    IntakeField(
        id="location",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Location", "hi": "स्थान", "mr": "ठिकाण"},
       prompt={
            "en": "Where in your body do you feel it? Please point in words.",
            "hi": "आप इसे शरीर में कहाँ महसूस करते हैं? कृपया शब्दों में बताएं।",
            "mr": "हे तुम्हाला शरीरात कुठे जाणवते? कृपया शब्दांत सांगा.",
        },
        simpler_prompt={
            "en": "Can you tell me where it hurts? For example, the upper belly, the chest, or the lower back.",
            "hi": "क्या आप बता सकते हैं कि दर्द कहाँ है? जैसे ऊपर पेट में, सीने में, या कमर के नीचे।",
            "mr": "दुखणे कुठे आहे ते सांगू शकता का? जसे वरच्या पोटात, छातीत, किंवा कंबरेच्या खाली.",
        },
    ),
    IntakeField(
        id="character",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Character", "hi": "प्रकृति", "mr": "स्वरूप"},
         prompt={
            "en": "How would you describe it? For example: sharp, dull, burning, or cramping.",
            "hi": "आप इसे कैसे बताएंगे? उदाहरण: तेज़, हल्का, जलन, या ऐंठन।",
            "mr": "तुम्ही ते कसे सांगाल? उदाहरण: तीव्र, मंद, जळजळ, किंवा पिळवटणे.",
        },
        simpler_prompt={
            "en": "Is it more like a sharp poke, a dull ache, or a burning feeling?",
            "hi": "क्या यह तेज़ चुभन जैसा है, हल्के दर्द जैसा है, या जलन जैसा है?",
            "mr": "ते तीक्ष्ण टोचल्यासारखे आहे, मंद दुखण्यासारखे आहे, की जळजळल्यासारखे आहे?",
        },
    ),
    IntakeField(
        id="severity",
        ftype=FieldType.SCALE_0_10,
        label={"en": "Severity (0-10)", "hi": "गंभीरता (0-10)", "mr": "तीव्रता (0-10)"},
       prompt={
            "en": "On a scale of 0 to 10, how bad is it, where 10 is the worst?",
            "hi": "0 से 10 के पैमाने पर, यह कितना बुरा है, जहाँ 10 सबसे ज़्यादा है?",
            "mr": "० ते १० च्या प्रमाणात, हे किती तीव्र आहे, जिथे १० सर्वात जास्त आहे?",
        },
        simpler_prompt={
            "en": "Please say a number from 0 to 10. 0 means no pain, 10 means the worst pain.",
            "hi": "कृपया 0 से 10 तक एक संख्या कहें। 0 का मतलब कोई दर्द नहीं, 10 का मतलब सबसे ज़्यादा दर्द।",
            "mr": "कृपया ० ते १० मधील एक संख्या सांगा. ० म्हणजे त्रास नाही, १० म्हणजे सर्वाधिक त्रास.",
        },
    ),
    IntakeField(
        id="timing_pattern",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Timing / pattern", "hi": "समय / पैटर्न", "mr": "वेळ / स्वरूप"},
         prompt={
            "en": "Is it there all the time, or does it come and go?",
            "hi": "क्या यह हर समय रहता है, या आता-जाता है?",
            "mr": "हे सतत असते, की येते-जाते?",
        },
        simpler_prompt={
            "en": "Does it stay constant, or does it come in waves? For example, worse after eating or at night.",
            "hi": "क्या यह लगातार रहता है, या रुक-रुक कर आता है? जैसे खाने के बाद या रात में ज़्यादा।",
            "mr": "हे सतत राहते का, की थांबून थांबून येते? जसे जेवणानंतर किंवा रात्री जास्त.",
        },
    ),
    IntakeField(
        id="aggravating_relieving",
        ftype=FieldType.FREE_TEXT,
        label={
            "en": "Aggravating / relieving",
            "hi": "बढ़ाने / घटाने वाले कारण",
            "mr": "वाढवणारे / कमी करणारे घटक",
        },
        prompt={
            "en": "What makes it better or worse?",
            "hi": "इससे क्या बेहतर या बदतर होता है?",
            "mr": "कशामुळे ते कमी होते किंवा वाढते?",
        },
        simpler_prompt={
            "en": "Does anything make it worse, like movement or food? Does anything help, like rest or medicine?",
            "hi": "क्या कोई चीज़ इसे बढ़ाती है, जैसे हिलना-डुलना या खाना? क्या कोई चीज़ राहत देती है, जैसे आराम या दवा?",
            "mr": "हालचाल किंवा अन्नासारख्या कशाने ते वाढते का? आराम किंवा औषधासारख्या कशाने आराम मिळतो का?",
        },
    ),
    IntakeField(
        id="associated_symptoms",
        ftype=FieldType.FREE_TEXT,
        red_flag_check=True,
        label={"en": "Associated symptoms", "hi": "साथ के लक्षण", "mr": "सोबतची लक्षणे"},
        prompt={
            "en": "Do you have any other symptoms along with this? For example fever, vomiting, "
            "breathlessness, or weakness.",
            "hi": "क्या इसके साथ कोई और लक्षण हैं? उदाहरण: बुखार, उल्टी, साँस फूलना, या कमज़ोरी।",
            "mr": "याबरोबर इतर काही लक्षणे आहेत का? उदाहरण: ताप, उलटी, धाप लागणे, किंवा अशक्तपणा.",
        },
        simpler_prompt={
            "en": "Any other problems too? For example, fever, vomiting, breathlessness, or dizziness.",
            "hi": "कोई और तकलीफ़ भी? जैसे बुख़ार, उल्टी, साँस फूलना, या चक्कर आना।",
            "mr": "आणखी काही त्रास? जसे ताप, उलटी, धाप लागणे, किंवा चक्कर येणे.",
        },
    ),
    IntakeField(
        id="medications",
        ftype=FieldType.LIST,
        critical=True,
        label={"en": "Current medications", "hi": "मौजूदा दवाइयाँ", "mr": "सध्याची औषधे"},
        prompt={
            "en": "What medicines are you currently taking? Please include the names if you know them.",
            "hi": "आप वर्तमान में कौन सी दवाइयाँ ले रहे हैं? यदि नाम पता हों तो बताएं।",
            "mr": "तुम्ही सध्या कोणती औषधे घेत आहात? नावे माहीत असल्यास सांगा.",
        },
        simpler_prompt={
            "en": "Are you taking any tablets, injections, or syrups regularly? Please say their "
            "names slowly. For example: 'Metformin 500'.",
            "hi": "क्या आप नियमित रूप से कोई गोली, इंजेक्शन या सिरप ले रहे हैं? कृपया नाम धीरे-धीरे बताएं।",
            "mr": "तुम्ही नियमित कोणत्या गोळ्या, इंजेक्शन किंवा सिरप घेता का? कृपया नावे हळू सांगा.",
        },
    ),
    IntakeField(
        id="allergies",
        ftype=FieldType.LIST,
        critical=True,
        red_flag_check=True,
        label={"en": "Allergies", "hi": "एलर्जी", "mr": "ॲलर्जी"},
          prompt={
            "en": "Are you allergic to any medicines or foods? If yes, please name them.",
            "hi": "क्या आपको किसी दवा या भोजन से एलर्जी है? यदि हाँ, तो नाम बताएं।",
            "mr": "तुम्हाला कोणत्या औषधाची किंवा अन्नाची ॲलर्जी आहे का? असल्यास नावे सांगा.",
        },
        simpler_prompt={
            "en": "Has any medicine ever caused you a rash, swelling, or trouble breathing? Please "
            "say which one. If none, say 'no allergies'.",
            "hi": "क्या किसी दवा से कभी चकत्ते, सूजन या साँस की दिक्कत हुई है? कौन सी, बताएं। नहीं तो 'कोई एलर्जी नहीं' कहें।",
            "mr": "कोणत्या औषधामुळे कधी पुरळ, सूज किंवा श्वासाचा त्रास झाला का? कोणते ते सांगा. नसल्यास 'ॲलर्जी नाही' म्हणा.",
        },
    ),
    IntakeField(
        id="past_medical_history",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Past medical history", "hi": "पुरानी बीमारियाँ", "mr": "जुने आजार"},
         prompt={
            "en": "Do you have any ongoing health conditions, like diabetes, blood pressure, or "
            "heart or lung problems?",
            "hi": "क्या आपको कोई पुरानी बीमारी है, जैसे मधुमेह, रक्तचाप, या हृदय या फेफड़ों की समस्या?",
            "mr": "तुम्हाला मधुमेह, रक्तदाब, किंवा हृदय वा फुफ्फुसाचा त्रास यांसारखा काही जुना आजार आहे का?",
        },
        simpler_prompt={
            "en": "Any ongoing conditions like diabetes, blood pressure, or asthma?",
            "hi": "कोई पुरानी बीमारी जैसे शुगर (डायबिटीज़), बीपी, या दमा?",
            "mr": "मधुमेह, रक्तदाब, किंवा दम्यासारखा काही दीर्घकालीन आजार आहे का?",
        },
    ),
    IntakeField(
        id="past_surgical_history",
        ftype=FieldType.FREE_TEXT,
        label={
            "en": "Past surgeries / hospital stays",
            "hi": "पिछली सर्जरी / अस्पताल में भर्ती",
            "mr": "मागील शस्त्रक्रिया / रुग्णालयात भरती",
        },
        prompt={
            "en": "Have you had any surgeries or hospital stays before?",
            "hi": "क्या आपकी पहले कोई सर्जरी या अस्पताल में भर्ती हुई है?",
            "mr": "तुमची आधी कोणती शस्त्रक्रिया किंवा रुग्णालयात भरती झाली आहे का?",
        },
        simpler_prompt={
            "en": "Any operations in the past, or times you stayed overnight in a hospital?",
            "hi": "क्या पहले कभी कोई ऑपरेशन हुआ है, या आप अस्पताल में रात भर रुके हैं?",
            "mr": "पूर्वी कधी काही ऑपरेशन झाले आहे का, किंवा तुम्ही रुग्णालयात रात्रभर राहिला आहात का?",
        },
    ),
    IntakeField(
        id="family_history",
        ftype=FieldType.FREE_TEXT,
        required=False,
        label={"en": "Family history", "hi": "पारिवारिक इतिहास", "mr": "कौटुंबिक इतिहास"},
        prompt={
            "en": "Do any illnesses run in your family, like diabetes, heart disease, or cancer?",
            "hi": "क्या आपके परिवार में कोई बीमारी चलती है, जैसे मधुमेह, हृदय रोग, या कैंसर?",
            "mr": "तुमच्या कुटुंबात मधुमेह, हृदयरोग, किंवा कर्करोग असे काही आजार आहेत का?",
        },
        simpler_prompt={
            "en": "Do your parents or siblings have conditions like heart disease, diabetes, or cancer?",
            "hi": "क्या आपके माता-पिता या भाई-बहन को दिल की बीमारी, शुगर, या कैंसर जैसी कोई बीमारी है?",
            "mr": "तुमच्या आई-वडिलांना किंवा भावंडांना हृदयविकार, मधुमेह, किंवा कर्करोगासारखे आजार आहेत का?",
        },
    ),
    IntakeField(
        id="social_history",
        ftype=FieldType.FREE_TEXT,
        required=False,
        label={"en": "Social history", "hi": "सामाजिक इतिहास", "mr": "सामाजिक इतिहास"},
        prompt={
            "en": "Do you use tobacco or alcohol? And what work do you do?",
            "hi": "क्या आप तंबाकू या शराब का उपयोग करते हैं? और आप क्या काम करते हैं?",
            "mr": "तुम्ही तंबाखू किंवा दारू वापरता का? आणि तुम्ही काय काम करता?",
        },
        simpler_prompt={
            "en": "Do you smoke, chew tobacco, or drink alcohol? And what is your job?",
            "hi": "क्या आप धूम्रपान करते हैं, तंबाकू खाते हैं, या शराब पीते हैं? और आपका काम क्या है?",
            "mr": "तुम्ही धूम्रपान करता, तंबाखू खाता, किंवा दारू पिता का? आणि तुमचे काम काय आहे?",
        },
    ),
    IntakeField(
        id="additional_info",
        ftype=FieldType.FREE_TEXT,
        required=False,
        label={"en": "Anything else", "hi": "कुछ और", "mr": "आणखी काही"},
        prompt={
            "en": "Is there anything else you would like the doctor to know?",
            "hi": "क्या कुछ और है जो आप डॉक्टर को बताना चाहेंगे?",
            "mr": "डॉक्टरांना सांगण्यासारखे आणखी काही आहे का?",
        },
        simpler_prompt={
            "en": "Anything else on your mind that the doctor should know before you meet?",
            "hi": "मिलने से पहले कुछ और जो डॉक्टर को पता होना चाहिए?",
            "mr": "भेटण्यापूर्वी डॉक्टरांना माहीत असावे असे आणखी काही?",
        },
    ),
]

_BY_ID: dict[str, IntakeField] = {f.id: f for f in INTAKE_FIELDS}


def get_field(field_id: str) -> IntakeField | None:
    """Return the field by id, or None if unknown."""
    return _BY_ID.get(field_id)


def required_field_ids() -> list[str]:
    """Ids of all required fields (used for completion-rate math)."""
    return [f.id for f in INTAKE_FIELDS if f.required]


def critical_field_ids() -> set[str]:
    """Ids of fields that must be read back and confirmed."""
    return {f.id for f in INTAKE_FIELDS if f.critical}
