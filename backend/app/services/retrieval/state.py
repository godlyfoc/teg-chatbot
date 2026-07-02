"""LangGraph state for the retrieval pipeline."""

from typing import TypedDict


class RetrievalGraphState(TypedDict, total=False):
    query: str
    top_k: int | None
    retrieval_enabled: bool
    query_language: str
    candidate_chunks: list[dict]
    chunks: list[dict]
    elapsed_seconds: float
    rerank_elapsed_seconds: float
    error: str | None
    context: str
