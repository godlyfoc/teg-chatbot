"""Shared LLM prompts."""

from app.models.retrieval import RetrievedChunk
from app.services.language import (
    LanguageCode,
    bilingual_system_prompt,
    detect_query_language,
    no_context_message,
)
from app.services.retrieval.context import format_retrieval_context


def build_system_message(
    user_message: str,
    *,
    context_chunks: list[RetrievedChunk] | None = None,
    max_context_chars: int = 6000,
    query_language: LanguageCode | None = None,
) -> str:
    user_lang: LanguageCode = query_language or detect_query_language(user_message)
    base = bilingual_system_prompt(user_lang)

    if not context_chunks:
        return f"{base}\n\n{no_context_message(user_lang)}"

    context = format_retrieval_context(context_chunks, max_chars=max_context_chars)
    if user_lang == "ga":
        instruction = (
            "Úsáid NA habhairtí seo a leanas ó teg.ie chun freagra a thabhairt ar cheist an úsáideora. "
            "Mura bhfuil go leor eolais sna habhairtí, abair go soiléir é sin — ná cum fíricí. "
            "Más fiú, lua cén leathanach a tháinig an t-eolas as. "
            "Freagair i nGaeilge amháin."
        )
    else:
        instruction = (
            "Use ONLY the following excerpts from teg.ie to answer the user's question. "
            "If the excerpts do not contain enough information, say so clearly — do not invent facts. "
            "When helpful, mention which page the information comes from. "
            "Respond in English only."
        )

    return f"{base}\n\n{instruction}\n\n---\n{context}\n---"
