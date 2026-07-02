"""Tests for citation validation and RAG pipeline behaviour."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.rag import ValidationResult
from app.models.retrieval import RetrievedChunk, RetrievalResult
from app.services.rag.pipeline import RAGPipeline
from app.services.validation.validator import extract_citations, validate_citations


def _chunk(
    content: str,
    *,
    title: str = "Exams",
    url: str = "https://www.teg.ie/exams",
    score: float = 0.9,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        content=content,
        source_url=url,
        title=title,
        score=score,
    )


def test_extract_citations_from_sources_section():
    response = (
        "## Answer\nB1 exams are held in May.\n\n"
        "## Sources\n"
        "- [Exams](https://www.teg.ie/exams)"
    )
    citations = extract_citations(response)
    assert len(citations) == 1
    assert citations[0].title == "Exams"
    assert citations[0].url == "https://www.teg.ie/exams"


def test_validate_citations_rejects_unknown_url():
    response = (
        "## Answer\nSome fact.\n\n"
        "## Sources\n"
        "- [Other](https://www.example.com/page)"
    )
    result = validate_citations(response, [_chunk("B1 exams are held in May.")])
    assert result.passed is False
    assert any("not found" in error for error in result.errors)


def test_validate_citations_accepts_matching_source():
    response = (
        "## Answer\nB1 exams are held in May.\n\n"
        "## Sources\n"
        "- [Exams](https://www.teg.ie/exams)"
    )
    result = validate_citations(response, [_chunk("B1 exams are held in May.")])
    assert result.passed is True


@pytest.fixture
def rag_settings():
    settings = MagicMock()
    settings.retrieval_enabled = True
    settings.cohere_api_key = "test-cohere"
    settings.retrieval_max_context_chars = 6000
    settings.validation_max_retries = 1
    settings.rag_log_enabled = False
    settings.rag_log_path = "data/rag_requests.jsonl"
    return settings


@pytest.mark.asyncio
async def test_rag_pipeline_returns_fallback_without_reranked_chunks(rag_settings):
    pipeline = RAGPipeline(rag_settings)
    pipeline.retrieval_graph = AsyncMock()
    pipeline.retrieval_graph.run = AsyncMock(
        return_value=RetrievalResult(
            query="What is TEG?",
            candidate_chunks=[_chunk("candidate only")],
            chunks=[],
            query_language="en",
            context="",
        )
    )

    result = await pipeline.execute("What is TEG?")

    assert result.is_fallback is True
    assert "not available on the TEG website" in result.response
    assert result.log.fallback_returned is True


@pytest.mark.asyncio
async def test_rag_pipeline_returns_validated_response(rag_settings):
    pipeline = RAGPipeline(rag_settings)
    chunks = [_chunk("TEG offers Irish language exams at multiple levels.")]
    pipeline.retrieval_graph = AsyncMock()
    pipeline.retrieval_graph.run = AsyncMock(
        return_value=RetrievalResult(
            query="What is TEG?",
            candidate_chunks=chunks,
            chunks=chunks,
            query_language="en",
            context="[1] Exams (https://www.teg.ie/exams)\nTEG offers Irish language exams at multiple levels.",
        )
    )
    pipeline.llm.generate = AsyncMock(
        return_value=(
            "## Answer\nTEG offers Irish language exams at multiple levels.\n\n"
            "## Sources\n"
            "- [Exams](https://www.teg.ie/exams)"
        )
    )
    pipeline.validator.validate = AsyncMock(return_value=ValidationResult(passed=True))

    result = await pipeline.execute("What is TEG?")

    assert result.is_fallback is False
    assert result.validation_passed is True
    assert len(result.citations) == 1
    assert result.log.validation_result == "pass"
    assert "### Sources" in result.response
    assert "## Answer" not in result.response


@pytest.mark.asyncio
async def test_rag_pipeline_fallback_after_validation_failures(rag_settings):
    pipeline = RAGPipeline(rag_settings)
    chunks = [_chunk("TEG offers Irish language exams at multiple levels.")]
    pipeline.retrieval_graph = AsyncMock()
    pipeline.retrieval_graph.run = AsyncMock(
        return_value=RetrievalResult(
            query="What is TEG?",
            candidate_chunks=chunks,
            chunks=chunks,
            query_language="en",
            context="context",
        )
    )
    pipeline.llm.generate = AsyncMock(return_value="## Answer\nBad unsupported claim.\n\n## Sources\n- [Exams](https://www.teg.ie/exams)")
    pipeline.validator.validate = AsyncMock(
        return_value=ValidationResult(passed=False, errors=["Unsupported claim"]),
    )

    result = await pipeline.execute("What is TEG?")

    assert result.is_fallback is True
    assert result.log.validation_result == "fail"
    assert pipeline.llm.generate.await_count == 2


def test_format_response_for_display_strips_internal_headers():
    from app.services.rag.formatting import format_response_for_display

    raw = (
        "## Answer\n"
        "TEG offers **Irish language exams** at multiple levels [1].\n\n"
        "- Level A1 for beginners [1]\n"
        "- Level C1 for advanced speakers [1]\n\n"
        "## Sources\n"
        "1. [Exams](https://www.teg.ie/exams)"
    )
    display = format_response_for_display(raw, "en")
    assert "## Answer" not in display
    assert "**Irish language exams**" in display
    assert "[1](https://www.teg.ie/exams)" in display
    assert "### Sources" in display
    assert "1. [Exams](https://www.teg.ie/exams)" in display


def test_format_response_injects_inline_citation_links():
    from app.services.rag.formatting import format_response_for_display

    raw = (
        "## Answer\n"
        "TEG was established in 2005 [1] and offers B1 exams [2].\n\n"
        "## Sources\n"
        "1. [About](https://www.teg.ie/about)\n"
        "2. [Exams](https://www.teg.ie/exams)"
    )
    display = format_response_for_display(raw, "en")
    assert "2005 [1](https://www.teg.ie/about)" in display
    assert "exams [2](https://www.teg.ie/exams)" in display
    assert "1. [About](https://www.teg.ie/about)" in display
    assert "2. [Exams](https://www.teg.ie/exams)" in display
