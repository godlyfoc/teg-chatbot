"""Tests for query language detection and language-aware prompts."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.retrieval import RetrievedChunk, RetrievalResult
from app.services.language import detect_query_language
from app.services.rag.prompts import build_rag_system_message
from app.services.retrieval.context import format_retrieval_context
from app.services.retrieval.graph import RetrievalGraphRunner, build_retrieval_graph


def _chunk(content: str, url: str = "https://www.teg.ie/test") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="abc123",
        content=content,
        source_url=url,
        title="Test Page",
        score=0.9,
    )


def test_detect_query_language_english():
    assert detect_query_language("When are the B1 oral exams?") == "en"


def test_detect_query_language_irish():
    assert detect_query_language("Cathain a bhíonn scrúduithe béil B1 ar siúl?") == "ga"


def test_detect_query_language_short_irish():
    assert detect_query_language("Scrúdú TEG") == "ga"


def test_format_retrieval_context_respects_max_chars():
    chunks = [_chunk("x" * 2000), _chunk("y" * 2000)]
    context = format_retrieval_context(chunks, max_chars=500)
    assert len(context) <= 500


def test_build_rag_system_message_english():
    prompt = build_rag_system_message(
        context_chunks=[_chunk("B1 exams run in May.")],
        max_context_chars=6000,
        query_language="en",
    )
    assert "## Sources" in prompt
    assert "Respond in English only" in prompt
    assert "B1 exams run in May." in prompt


def test_build_rag_system_message_irish():
    prompt = build_rag_system_message(
        context_chunks=[_chunk("Bíonn scrúduithe i mí na Bealtaine.")],
        max_context_chars=6000,
        query_language="ga",
    )
    assert "Freagair i nGaeilge amháin" in prompt
    assert "Bíonn scrúduithe i mí na Bealtaine." in prompt


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.retrieval_enabled = True
    settings.retrieval_candidate_k = 20
    settings.retrieval_rerank_top_k = 5
    settings.retrieval_min_rerank_score = 0.15
    settings.retrieval_max_context_chars = 6000
    settings.cohere_api_key = "test-cohere"
    settings.cohere_rerank_model = "rerank-multilingual-v3.0"
    settings.openai_api_key = "test-openai"
    settings.index_embedding_model = "text-embedding-3-small"
    settings.index_embedding_dimensions = 1536
    # Real (non-mock) values so Retriever.__init__ doesn't mistake a MagicMock
    # attribute for a truthy local path and create a stray on-disk Qdrant store.
    settings.qdrant_path = ""
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_api_key = ""
    settings.qdrant_collection = "test_collection"
    return settings


@pytest.fixture
def sample_chunks():
    return [
        RetrievedChunk(
            chunk_id="abc",
            content="B1 exams are held in May.",
            source_url="https://www.teg.ie/exams",
            title="Exams",
            score=0.9,
        )
    ]


def _mock_reranker(sample_chunks):
    reranker = MagicMock()
    reranker.rerank = AsyncMock(return_value=(sample_chunks, 0.05))
    return reranker


@pytest.mark.asyncio
async def test_retrieval_graph_detects_query_language(mock_settings, sample_chunks):
    runner = RetrievalGraphRunner(mock_settings)
    runner._retriever = AsyncMock()
    runner._retriever.retrieve = AsyncMock(
        return_value=RetrievalResult(
            query="Cathain a bhíonn an scrúdú?",
            chunks=sample_chunks,
            elapsed_seconds=0.1,
        )
    )
    runner._reranker = _mock_reranker(sample_chunks)

    result = await runner.run("Cathain a bhíonn an scrúdú?")

    assert result.query_language == "ga"


@pytest.mark.asyncio
async def test_retrieval_graph_runner_returns_reranked_chunks(mock_settings, sample_chunks):
    runner = RetrievalGraphRunner(mock_settings)
    runner._retriever = AsyncMock()
    runner._retriever.retrieve = AsyncMock(
        return_value=RetrievalResult(
            query="B1 exams",
            chunks=sample_chunks,
            elapsed_seconds=0.1,
        )
    )
    runner._reranker = _mock_reranker(sample_chunks)

    result = await runner.run("B1 exams")

    assert len(result.chunks) == 1
    runner._retriever.retrieve.assert_awaited_once()
    runner._reranker.rerank.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrieval_graph_skips_when_disabled(mock_settings):
    runner = RetrievalGraphRunner(mock_settings)
    runner._retriever = AsyncMock()

    result = await runner.run("hello", retrieval_enabled=False)

    assert result.chunks == []
    assert result.query_language in ("en", "ga")
    runner._retriever.retrieve.assert_not_awaited()


def test_build_retrieval_graph_compiles():
    graph = build_retrieval_graph()
    assert graph is not None
