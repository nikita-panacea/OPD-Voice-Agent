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
            "en": "Before we begin, do you agree to share your health information with the care team through this automated assistant?",
            "hi": "शुरू करने से पहले, क्या आप इस स्वचालित सहायक के ज़रिए अपनी स्वास्थ्य जानकारी देखभाल टीम के साथ साझा करने के लिए सहमत हैं?",
            "mr": "सुरुवात करण्यापूर्वी, या स्वयंचलित सहाय्यकाद्वारे तुमची आरोग्य माहिती काळजी घेणाऱ्या टीमसोबत सामायिक करण्यास तुमची संमती आहे का?",
        },
        simpler_prompt={
            "en": "Is it okay if I ask you some questions about your health and share your answers with your doctor? Please say yes or no.",
            "hi": "क्या मैं आपके स्वास्थ्य के बारे में कुछ सवाल पूछ सकती हूँ और आपके जवाब आपके डॉक्टर को बता सकती हूँ? कृपया हाँ या ना कहें।",
            "mr": "मी तुम्हाला तुमच्या आरोग्याबद्दल काही प्रश्न विचारले आणि तुमची उत्तरे तुमच्या डॉक्टरांना सांगितली तर चालेल का? कृपया हो किंवा नाही म्हणा.",
        },
    ),
    IntakeField(
        id="identity",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Patient", "hi": "मरीज़", "mr": "रुग्ण"},
        prompt={
            "en": "Can you tell me your name, your age, and your sex?",
            "hi": "क्या आप मुझे अपना नाम, उम्र और लिंग बता सकते हैं?",
            "mr": "तुम्ही मला तुमचे नाव, वय आणि लिंग सांगू शकता का?",
        },
        simpler_prompt={
            "en": "What is your name? And how old are you? For example: 'Asha, 45 years, female'.",
            "hi": "आपका नाम क्या है? और आपकी उम्र कितनी है? उदाहरण के लिए: 'आशा, 45 वर्ष, महिला'।",
            "mr": "तुमचे नाव काय आहे? आणि तुमचे वय किती आहे? उदाहरणार्थ: 'आशा, ४५ वर्षे, स्त्री'.",
        },
    ),
    IntakeField(
        id="chief_complaint",
        ftype=FieldType.FREE_TEXT,
        critical=True,
        label={"en": "Chief complaint", "hi": "मुख्य शिकायत", "mr": "मुख्य तक्रार"},
        prompt={
            "en": "What brought you in today? What is troubling you the most?",
            "hi": "आज आप किस वजह से आए हैं? आपको सबसे ज़्यादा क्या तकलीफ़ है?",
            "mr": "आज तुम्ही कशासाठी आलात? तुम्हाला सर्वात जास्त काय त्रास होतोय?",
        },
        simpler_prompt={
            "en": "What is the main problem you are feeling today? For example, stomach pain, fever, or cough.",
            "hi": "आज आपको सबसे बड़ी तकलीफ़ क्या महसूस हो रही है? जैसे पेट दर्द, बुख़ार, या खांसी।",
            "mr": "आज तुम्हाला जाणवणारी मुख्य समस्या कोणती आहे? जसे पोटदुखी, ताप, किंवा खोकला.",
        },
    ),
    IntakeField(
        id="onset_duration",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Onset / duration", "hi": "शुरुआत / अवधि", "mr": "सुरुवात / कालावधी"},
        prompt={
            "en": "When did this start, and did it begin suddenly or gradually?",
            "hi": "यह कब शुरू हुआ, और क्या यह अचानक शुरू हुआ या धीरे-धीरे?",
            "mr": "हे कधी सुरू झाले, आणि ते अचानक सुरू झाले की हळूहळू?",
        },
        simpler_prompt={
            "en": "How many days or hours ago did this begin? For example, 'two days ago, slowly'.",
            "hi": "यह कितने दिन या घंटे पहले शुरू हुआ? उदाहरण के लिए, 'दो दिन पहले, धीरे-धीरे'।",
            "mr": "हे किती दिवस किंवा तासांपूर्वी सुरू झाले? उदाहरणार्थ, 'दोन दिवसांपूर्वी, हळूहळू'.",
        },
    ),
    IntakeField(
        id="location",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Location", "hi": "स्थान", "mr": "ठिकाण"},
        prompt={
            "en": "Where in your body do you feel it?",
            "hi": "आपको यह शरीर के किस हिस्से में महसूस होता है?",
            "mr": "हे तुम्हाला शरीराच्या कोणत्या भागात जाणवते?",
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
            "en": "What does it feel like?",
            "hi": "यह कैसा महसूस होता है?",
            "mr": "ते कसे वाटते?",
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
            "en": "On a scale of 0 to 10, where 10 is the worst, how bad is it?",
            "hi": "0 से 10 के पैमाने पर, जहाँ 10 सबसे ज़्यादा है, यह कितना तेज़ है?",
            "mr": "0 ते 10 च्या प्रमाणात, जिथे 10 सर्वात जास्त आहे, हे किती तीव्र आहे?",
        },
        simpler_prompt={
            "en": "If 0 means no problem and 10 means the worst you can imagine, what number is it right now?",
            "hi": "अगर 0 का मतलब कोई तकलीफ़ नहीं और 10 का मतलब सबसे ज़्यादा तकलीफ़, तो अभी कितना नंबर है?",
            "mr": "जर 0 म्हणजे काही त्रास नाही आणि 10 म्हणजे सर्वात जास्त त्रास, तर आत्ता किती नंबर आहे?",
        },
    ),
    IntakeField(
        id="timing_pattern",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Timing / pattern", "hi": "समय / पैटर्न", "mr": "वेळ / स्वरूप"},
        prompt={
            "en": "Is it there all the time, or does it come and go? Is it worse at any particular time?",
            "hi": "क्या यह हर समय रहता है, या आता-जाता है? क्या यह किसी ख़ास समय पर ज़्यादा होता है?",
            "mr": "हे सतत असते का, की येते-जाते? कोणत्या विशिष्ट वेळी जास्त होते का?",
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
            "en": "Is there anything that makes it worse or better?",
            "hi": "क्या कोई चीज़ इसे बढ़ाती या कम करती है?",
            "mr": "असे काही आहे का ज्याने हे वाढते किंवा कमी होते?",
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
            "en": "Are you having any other symptoms along with this?",
            "hi": "क्या इसके साथ आपको कोई और लक्षण भी हैं?",
            "mr": "यासोबत तुम्हाला आणखी काही लक्षणे आहेत का?",
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
            "en": "Are you currently taking any medicines? Please include the dose if you know it.",
            "hi": "क्या आप अभी कोई दवा ले रहे हैं? अगर मात्रा पता हो तो वह भी बताएं।",
            "mr": "तुम्ही सध्या काही औषधे घेत आहात का? माहीत असल्यास मात्राही सांगा.",
        },
        simpler_prompt={
            "en": "Do you take any tablets, syrups, or injections regularly? For example, a blood pressure tablet every morning.",
            "hi": "क्या आप कोई गोली, सिरप, या इंजेक्शन नियमित रूप से लेते हैं? जैसे रोज़ सुबह बीपी की गोली।",
            "mr": "तुम्ही नियमित काही गोळ्या, सिरप, किंवा इंजेक्शन घेता का? जसे रोज सकाळी बीपीची गोळी.",
        },
    ),
    IntakeField(
        id="allergies",
        ftype=FieldType.LIST,
        critical=True,
        red_flag_check=True,
        label={"en": "Allergies", "hi": "एलर्जी", "mr": "ॲलर्जी"},
        prompt={
            "en": "Do you have any allergies to medicines or foods?",
            "hi": "क्या आपको किसी दवा या भोजन से एलर्जी है?",
            "mr": "तुम्हाला कोणत्या औषधाची किंवा अन्नाची ॲलर्जी आहे का?",
        },
        simpler_prompt={
            "en": "Does any medicine or food cause a reaction like rash, swelling, or trouble breathing?",
            "hi": "क्या किसी दवा या भोजन से आपको चकत्ते, सूजन, या साँस लेने में दिक़्क़त होती है?",
            "mr": "एखाद्या औषधाने किंवा अन्नाने तुम्हाला पुरळ, सूज, किंवा श्वास घेण्यास त्रास होतो का?",
        },
    ),
    IntakeField(
        id="past_medical_history",
        ftype=FieldType.FREE_TEXT,
        label={"en": "Past medical history", "hi": "पुरानी बीमारियाँ", "mr": "जुने आजार"},
        prompt={
            "en": "Do you have any long-term illnesses, or have you had this problem before?",
            "hi": "क्या आपको कोई पुरानी बीमारी है, या यह समस्या पहले भी हुई है?",
            "mr": "तुम्हाला काही दीर्घकालीन आजार आहेत का, किंवा ही समस्या आधीही झाली आहे का?",
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
            "en": "Have you ever had any surgery or been admitted to a hospital?",
            "hi": "क्या आपकी कभी कोई सर्जरी हुई है या आप अस्पताल में भर्ती हुए हैं?",
            "mr": "तुमची कधी काही शस्त्रक्रिया झाली आहे का किंवा तुम्ही रुग्णालयात भरती झाला आहात का?",
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
            "en": "Do any illnesses run in your family?",
            "hi": "क्या आपके परिवार में कोई बीमारी चलती है?",
            "mr": "तुमच्या कुटुंबात काही आजार चालत आले आहेत का?",
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
            "en": "Do you use tobacco or alcohol, and what work do you do?",
            "hi": "क्या आप तंबाकू या शराब का सेवन करते हैं, और आप क्या काम करते हैं?",
            "mr": "तुम्ही तंबाखू किंवा दारूचे सेवन करता का, आणि तुम्ही काय काम करता?",
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
            "mr": "डॉक्टरांना सांगू इच्छिता असे आणखी काही आहे का?",
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
