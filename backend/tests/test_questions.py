"""Schema integrity tests for the §8.1 intake field set."""

from intake.questions import (
    INTAKE_FIELDS,
    FieldType,
    critical_field_ids,
    get_field,
    localized,
    required_field_ids,
)

POC_LANGUAGES = ["en", "hi", "mr"]


def test_ids_are_unique() -> None:
    ids = [f.id for f in INTAKE_FIELDS]
    assert len(ids) == len(set(ids))


def test_all_fields_have_both_languages() -> None:
    for f in INTAKE_FIELDS:
        for lang in POC_LANGUAGES:
            assert f.label.get(lang), f"{f.id} missing {lang} label"
            assert f.prompt.get(lang), f"{f.id} missing {lang} prompt"
            assert f.simpler_prompt.get(lang), f"{f.id} missing {lang} simpler_prompt"


def test_translations_marked_for_clinical_review() -> None:
    # POC decision: the whole §8.1 set is used as-is and flagged for clinical review.
    assert all(f.needs_clinical_review for f in INTAKE_FIELDS)


def test_consent_is_the_gate() -> None:
    consent = get_field("consent")
    assert consent is not None
    assert consent.is_consent_gate
    assert consent.ftype == FieldType.YES_NO


def test_critical_fields_present() -> None:
    assert critical_field_ids() == {"chief_complaint", "medications", "allergies"}


def test_required_includes_chief_complaint() -> None:
    assert "chief_complaint" in required_field_ids()


def test_localized_falls_back_to_english() -> None:
    f = get_field("severity")
    assert f is not None
    assert localized(f.prompt, "ta") == f.prompt["en"]  # Tamil not present -> English fallback
