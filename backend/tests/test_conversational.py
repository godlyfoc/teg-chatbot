"""Tests for conversational query detection."""

from app.services.rag.conversational import is_conversational_query


def test_hi_is_conversational():
    assert is_conversational_query("Hi") is True
    assert is_conversational_query("hello!") is True
    assert is_conversational_query("Hey there") is True
    assert is_conversational_query("Hi there") is True


def test_greeting_with_teg_topic_is_not_conversational():
    assert is_conversational_query("Hi what is TEG") is False
    assert is_conversational_query("Hello, when are the B1 exams?") is False


def test_irish_greetings():
    assert is_conversational_query("Dia dhuit") is True
    assert is_conversational_query("Haigh!") is True
