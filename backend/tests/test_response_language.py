"""Tests for response language alignment."""

from app.services.rag.response_language import _response_body, needs_translation


def test_needs_translation_irish_response_for_english_user():
    irish = (
        "Cuireann TEG scrúduithe Gaeilge ar fáil ag leibhéil éagsúla. "
        "Tá an clár oscailte gach bliain."
    )
    assert needs_translation(irish, "en") is True


def test_needs_translation_english_response_for_english_user():
    english = (
        "TEG offers Irish language exams at multiple levels. "
        "Registration opens each year."
    )
    assert needs_translation(english, "en") is False


def test_response_body_strips_sources_section():
    text = "TEG offers exams.\n\n---\n\n### Sources\n\n1. [Exams](https://www.teg.ie/exams)"
    assert "Sources" not in _response_body(text)
    assert "TEG offers exams" in _response_body(text)
