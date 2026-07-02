"""Irish / English language detection for teg.ie content and chat."""

import re
from typing import Literal

LanguageCode = Literal["en", "ga", "mixed"]

# Irish-specific characters and words (Gaeilge)
GA_CHARS = re.compile(r"[áéíóúÁÉÍÓÚ]")
GA_WORDS = re.compile(
    r"\b(agus|an|na|ar|le|do|go|ní|bhí|atá|scrúdú|gaeilge|teastas|iarrthóir|múinteoir)\b",
    re.IGNORECASE,
)

URL_GA_MARKERS = (
    "/nuacht/",
    "maidir-le-scr",
    "eolas-molta",
    "leibheil-scr",
    "láibheil",
    "éanadh",
    "polasaí",
    "náisc-",
    "ceisteanna-coitianta",
    "séanadh",
    "cóipcheart",
)

URL_EN_MARKERS = (
    "/english/",
    "/news/",
    "/about-exams",
    "/info-advice/",
    "/resources/",
    "/exam-levels",
    "/faqs",
    "/cookie-policy",
    "/site-map",
    "/mailing-list",
)


def language_from_url(url: str) -> LanguageCode:
    lower = url.lower()
    ga = sum(1 for m in URL_GA_MARKERS if m in lower)
    en = sum(1 for m in URL_EN_MARKERS if m in lower)
    if ga > en:
        return "ga"
    if en > ga:
        return "en"
    return "mixed"


def detect_language(text: str, url: str = "") -> LanguageCode:
    """Detect en / ga / mixed from text, with URL fallback for short content."""
    sample = text.strip()
    if len(sample) < 30:
        return language_from_url(url)

    ga_chars = len(GA_CHARS.findall(sample))
    ga_words = len(GA_WORDS.findall(sample))
    en_words = len(re.findall(
        r"\b(the|and|for|with|exam|about|information|register|application)\b",
        sample,
        re.I,
    ))

    # Strong Irish signals override langdetect (common on teg.ie)
    if ga_chars >= 2 or ga_words >= 2:
        if ga_chars + ga_words * 2 >= en_words + 1:
            return "ga"

    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        scores = detect_langs(sample)
        if not scores:
            return language_from_url(url)

        top = {lang.lang: lang.prob for lang in scores[:3]}
        ga_prob = top.get("ga", 0.0)
        en_prob = top.get("en", 0.0)

        if ga_prob > 0.45 and en_prob < 0.35:
            return "ga"
        if en_prob > 0.45 and ga_prob < 0.35:
            return "en"
        if ga_prob > 0.25 and en_prob > 0.25:
            return "mixed"
        if ga_prob >= en_prob:
            return "ga"
        return "en"
    except Exception:
        pass

    if ga_chars + ga_words * 2 > en_words:
        return "ga"
    if en_words > ga_chars:
        return "en"
    return language_from_url(url) if url else "mixed"


def detect_query_language(message: str) -> Literal["en", "ga"]:
    """Detect the language of a user query (en or ga) using langdetect."""
    text = message.strip()
    if not text:
        return "en"

    ga_chars = len(GA_CHARS.findall(text))
    ga_words = len(GA_WORDS.findall(text))

    # Short Irish queries may be below langdetect's reliable threshold.
    if ga_chars >= 1 or ga_words >= 1:
        en_words = len(
            re.findall(
                r"\b(the|and|for|with|exam|about|information|register|application|when|what|how)\b",
                text,
                re.I,
            )
        )
        if ga_chars + ga_words * 2 >= en_words:
            return "ga"

    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        scores = detect_langs(text)
        if scores:
            top = {lang.lang: lang.prob for lang in scores[:3]}
            ga_prob = top.get("ga", 0.0)
            en_prob = top.get("en", 0.0)
            if ga_prob > en_prob:
                return "ga"
            return "en"
    except Exception:
        pass

    if ga_chars + ga_words * 2 > 0:
        return "ga"
    return "en"


def detect_user_language(message: str) -> LanguageCode:
    """Detect language of a user chat message (en or ga preferred)."""
    return detect_query_language(message)


def bilingual_system_prompt(user_language: LanguageCode) -> str:
    base = (
        "You are the AI assistant for Teastas Eorpach na Gaeilge (TEG) at teg.ie. "
        "Answer questions about TEG exams, Irish language qualifications, registration, "
        "exam levels, and related services. Be clear, accurate, and helpful."
    )
    if user_language == "ga":
        return (
            f"{base} "
            "The user wrote in Irish (Gaeilge). You MUST respond entirely in Irish (Gaeilge). "
            "Do not respond in English. Use natural, standard Irish suitable for learners and exam candidates."
        )
    return (
        f"{base} "
        "The user wrote in English. You MUST respond entirely in English. "
        "If source excerpts are in Irish, translate the facts into English in your answer. "
        "Do not respond in Irish unless quoting a short Irish phrase from a source."
    )


def no_context_message(user_language: LanguageCode) -> str:
    if user_language == "ga":
        return (
            "Níor aimsíodh aon ábhar ábhartha ar teg.ie don cheist seo. "
            "Mura bhfuil an freagra agat ó eolas ginearálta faoi TEG, abair go soiléir nach bhfuil "
            "an t-eolas sin agat agus mol cuairt a thabhairt ar teg.ie nó teagmháil a dhéanamh le TEG."
        )
    return (
        "No relevant content was retrieved from teg.ie for this question. "
        "If you cannot answer from general TEG knowledge, say you do not have "
        "that information and suggest visiting teg.ie or contacting TEG directly."
    )
