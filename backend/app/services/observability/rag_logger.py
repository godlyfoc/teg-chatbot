"""Structured logging for RAG pipeline requests."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import Settings, get_settings
from app.models.rag import RAGRequestLog

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


def log_rag_request(record: RAGRequestLog, settings: Settings | None = None) -> None:
    """Persist a structured RAG log entry for monitoring and debugging."""
    settings = settings or get_settings()
    payload = record.model_dump()

    logger.info(
        "RAG request query=%r lang=%s validation=%s attempts=%d fallback=%s",
        record.query[:120],
        record.detected_language,
        record.validation_result,
        record.regeneration_attempts,
        record.fallback_returned,
        extra={"rag_request": payload},
    )

    if not settings.rag_log_enabled:
        return

    log_path = _resolve_path(settings.rag_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
