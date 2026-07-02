"""LangSmith tracing setup for LangGraph retrieval and OpenAI chat."""

from __future__ import annotations

import logging
import os

from app.config import Settings

logger = logging.getLogger(__name__)


def configure_langsmith(settings: Settings) -> bool:
    """
    Enable LangSmith tracing via environment variables.

    LangGraph and LangChain read LANGSMITH_* / LANGCHAIN_* at runtime.
    Call this once during application startup before handling requests.
    """
    if not settings.langsmith_tracing:
        return False

    api_key = settings.langsmith_api_key.strip()
    if not api_key:
        logger.warning("LANGSMITH_TRACING is enabled but LANGSMITH_API_KEY is not set")
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint.strip():
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint.strip()

    # Legacy names still used by some LangChain / LangGraph versions.
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    logger.info("LangSmith tracing enabled (project=%s)", settings.langsmith_project)
    return True


def is_langsmith_enabled(settings: Settings) -> bool:
    return settings.langsmith_tracing and bool(settings.langsmith_api_key.strip())
