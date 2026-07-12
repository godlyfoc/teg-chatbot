"""Cohere reranking for retrieved document candidates."""

from __future__ import annotations

import logging
import time

import cohere

from app.config import Settings, get_settings
from app.models.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


def vector_order_fallback(
    chunks: list[RetrievedChunk],
    *,
    top_n: int,
) -> list[RetrievedChunk]:
    """Use vector-search order when Cohere reranking is unavailable."""
    return chunks[:top_n]


class CohereReranker:
    """Rerank vector-retrieved chunks with Cohere Rerank."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if not self.settings.cohere_api_key.strip():
            raise ValueError("COHERE_API_KEY is required for reranking")
        self._client = cohere.AsyncClientV2(api_key=self.settings.cohere_api_key, timeout=20.0)

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        top_n: int | None = None,
    ) -> tuple[list[RetrievedChunk], float]:
        if not chunks:
            return [], 0.0

        limit = top_n or self.settings.retrieval_rerank_top_k
        documents = [f"Title: {chunk.title}\nURL: {chunk.source_url}\n\n{chunk.content}" for chunk in chunks]

        started = time.perf_counter()
        response = await self._client.rerank(
            model=self.settings.cohere_rerank_model,
            query=query,
            documents=documents,
            top_n=min(limit, len(chunks)),
        )
        elapsed = round(time.perf_counter() - started, 3)

        reranked: list[RetrievedChunk] = []
        for result in response.results:
            source = chunks[result.index]
            reranked.append(
                source.model_copy(update={"score": float(result.relevance_score)}),
            )

        logger.info(
            "Cohere reranked %d candidates to %d chunks (%.3fs)",
            len(chunks),
            len(reranked),
            elapsed,
        )
        return reranked, elapsed
