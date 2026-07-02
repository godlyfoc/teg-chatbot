"""Ensure assistant responses match the user's query language."""

from __future__ import annotations

import logging
import re
from typing import Literal

from app.services.language import LanguageCode, detect_language

logger = logging.getLogger(__name__)

UserLanguage = Literal["en", "ga"]


def _response_body(text: str) -> str:
    """Use answer body only when judging response language."""
    body = text.strip()
    if not body:
        return body
    parts = re.split(r"\n\s*---\s*\n", body, maxsplit=1)
    answer = parts[0]
    answer = re.sub(r"^#{1,3}\s*sources\s*$", "", answer, flags=re.I | re.M).strip()
    return answer


def needs_translation(text: str, target: UserLanguage) -> bool:
    """True when the response body is clearly in the wrong language."""
    body = _response_body(text)
    if len(body) < 15:
        return False
    detected = detect_language(body)
    if target == "en":
        return detected == "ga"
    if target == "ga":
        return detected == "en"
    return False


async def ensure_response_language(
    text: str,
    target: LanguageCode,
    *,
    translate,
) -> str:
    """Translate *text* when it does not match the user's language."""
    if target not in ("en", "ga") or not text.strip():
        return text
    if not needs_translation(text, target):
        return text
    logger.info("Response language mismatch — translating to %s", target)
    return await translate(text, target)
