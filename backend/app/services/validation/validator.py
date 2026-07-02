"""Validate grounded responses and citation integrity."""

from __future__ import annotations

import json
import logging
import re

from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.models.rag import Citation, ValidationResult
from app.models.retrieval import RetrievedChunk
from app.services.language import LanguageCode

logger = logging.getLogger(__name__)

_CITATION_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def extract_citations(response: str) -> list[Citation]:
    """Parse markdown citations from the Sources section."""
    sources_idx = response.lower().find("## sources")
    search_text = response[sources_idx:] if sources_idx >= 0 else response
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for match in _CITATION_PATTERN.finditer(search_text):
        title = match.group(1).strip()
        url = match.group(2).strip().rstrip(".,;")
        key = (title.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)
        citations.append(Citation(title=title, url=url))
    return citations


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def validate_citations(
    response: str,
    context_chunks: list[RetrievedChunk],
) -> ValidationResult:
    """Rule-based citation URL/title checks."""
    errors: list[str] = []
    citations = extract_citations(response)

    if "## answer" not in response.lower():
        errors.append("Response is missing the required '## Answer' section.")

    if not citations:
        errors.append("Response is missing citations in the '## Sources' section.")

    allowed_by_url: dict[str, set[str]] = {}
    for chunk in context_chunks:
        url_key = _normalize_url(chunk.source_url)
        allowed_by_url.setdefault(url_key, set()).add(_normalize_title(chunk.title or "Untitled"))

    for citation in citations:
        url_key = _normalize_url(citation.url)
        if url_key not in allowed_by_url:
            errors.append(f"Cited URL not found in retrieved context: {citation.url}")
            continue
        allowed_titles = allowed_by_url[url_key]
        cited_title = _normalize_title(citation.title)
        if cited_title not in allowed_titles and not any(
            cited_title in title or title in cited_title for title in allowed_titles
        ):
            errors.append(
                f"Cited title '{citation.title}' does not match retrieved title(s) for {citation.url}",
            )

    return ValidationResult(passed=not errors, errors=errors)


class ResponseValidator:
    """Automated validation for grounded responses."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def validate(
        self,
        *,
        response: str,
        context_chunks: list[RetrievedChunk],
        context_text: str,
        query_language: LanguageCode,
    ) -> ValidationResult:
        citation_result = validate_citations(response, context_chunks)
        if not citation_result.passed:
            return citation_result

        grounding_result = await self._validate_grounding(
            response=response,
            context_text=context_text,
            query_language=query_language,
        )
        if not grounding_result.passed:
            return ValidationResult(
                passed=False,
                errors=citation_result.errors + grounding_result.errors,
            )
        return ValidationResult(passed=True)

    async def _validate_grounding(
        self,
        *,
        response: str,
        context_text: str,
        query_language: LanguageCode,
    ) -> ValidationResult:
        prompt = (
            "You are a strict fact-checking validator for a RAG chatbot.\n"
            "Given SOURCE EXCERPTS and an ASSISTANT RESPONSE, decide whether every factual "
            "statement in the Answer section is directly supported by the excerpts.\n"
            "Ignore the Sources section when judging support; only judge factual claims in Answer.\n"
            "Return JSON only: {\"passed\": true|false, \"errors\": [\"...\"]}\n"
            "Fail if any unsupported, speculative, or hallucinated claim is present."
        )
        if query_language == "ga":
            prompt += "\nThe response should be in Irish, but return validator errors in English."

        completion = await self._client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"SOURCE EXCERPTS:\n{context_text}\n\nASSISTANT RESPONSE:\n{response}",
                },
            ],
        )
        raw = completion.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
            passed = bool(parsed.get("passed"))
            errors = [str(item) for item in parsed.get("errors", [])]
            return ValidationResult(passed=passed, errors=errors)
        except json.JSONDecodeError:
            logger.warning("Validator returned non-JSON output: %s", raw[:200])
            return ValidationResult(passed=False, errors=["Validator returned invalid JSON"])
