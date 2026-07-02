"""Retrieval models for RAG."""

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    chunk_id: str
    content: str
    source_url: str
    title: str = ""
    score: float = 0.0
    language: str = "mixed"


class RetrievalResult(BaseModel):
    query: str
    candidate_chunks: list[RetrievedChunk] = Field(default_factory=list)
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    rerank_elapsed_seconds: float = 0.0
    query_language: str = "en"
    context: str = ""


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = None
