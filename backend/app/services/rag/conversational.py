"""Detect greetings and small talk that should bypass RAG."""

from __future__ import annotations

import re

from app.services.language import LanguageCode

_GREETING_RE = re.compile(
    r"^(?:"
    r"hi(?:\s+there)?|hello(?:\s+there)?|hey(?:\s+there)?|hiya|howdy|greetings|"
    r"good\s+(?:morning|afternoon|evening|day)|"
    r"how\s+are\s+you|what'?s\s+up|whats\s+up|sup|yo|"
    r"dia\s+dhuit|dia\s+duit|haigh|conas\s+at[aá]\s+t[uú]|sl[aá]n|"
    r"thanks?|thank\s+you|cheers|ok(?:ay)?|bye|goodbye|good\s+bye"
    r")[\s!.?,]*$",
    re.IGNORECASE,
)

_TEG_TOPIC_RE = re.compile(
    r"\b(?:teg|exam|exams|scr[uú]d[úu]|irish|gaeilge|certificate|level|b1|b2|c1|a1|a2|registration|mu\.ie)\b",
    re.IGNORECASE,
)


def is_conversational_query(message: str) -> bool:
    """True for greetings/thanks/goodbye with no substantive TEG question."""
    text = message.strip()
    if not text or len(text) > 60:
        return False
    if _TEG_TOPIC_RE.search(text):
        return False
    return bool(_GREETING_RE.match(text))


def build_conversational_system_message(query_language: LanguageCode) -> str:
    if query_language == "ga":
        return (
            "Is cúntóir AI thú do TEG (Teastas Eorpach na Gaeilge) ar teg.ie. "
            "Freagair beannachtaí agus comhrá gairid go cineálta agus go gonta (1–3 abairt). "
            "Má chuireann an t-úsáideoir ceist faoi scrúduithe nó clárúchán, mol dóibh ceist shonrach a chur faoi TEG. "
            "Ná cum fíricí faoi scrúduithe. Freagair i nGaeilge."
        )
    return (
        "You are the TEG AI Assistant for teg.ie (Teastas Eorpach na Gaeilge — Irish language exams). "
        "Reply warmly and briefly to greetings and casual messages (1–3 sentences). "
        "If the user asks about exams or registration, invite them to ask a specific TEG question. "
        "Do not invent exam dates, fees, or policies. Reply in English."
    )
