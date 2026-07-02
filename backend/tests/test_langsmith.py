"""Tests for LangSmith configuration."""

import os

from app.config import Settings
from app.observability.langsmith import configure_langsmith, is_langsmith_enabled


def test_configure_langsmith_sets_env(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key="test-key",
        langsmith_project="test-project",
    )
    assert configure_langsmith(settings) is True
    assert os.environ["LANGSMITH_API_KEY"] == "test-key"
    assert os.environ["LANGSMITH_PROJECT"] == "test-project"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"


def test_configure_langsmith_disabled_without_key():
    settings = Settings(langsmith_tracing=True, langsmith_api_key="")
    assert configure_langsmith(settings) is False


def test_is_langsmith_enabled():
    enabled = Settings(langsmith_tracing=True, langsmith_api_key="abc")
    disabled = Settings(langsmith_tracing=False, langsmith_api_key="abc")
    assert is_langsmith_enabled(enabled) is True
    assert is_langsmith_enabled(disabled) is False
