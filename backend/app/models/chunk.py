"""Chunk models for RAG indexing."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChunkMetadata(BaseModel):
    """Per-chunk metadata preserved from the source document and chunking pass."""

    model_config = ConfigDict(extra="allow")

    language: str = "mixed"
    document_type: str = "html"
    content_type: str = "text/html"
    section: str | None = None
    separator_level: str | None = None
    document_ingested_at: datetime | None = None
    document_chunk_count: int = 0
    char_count: int = 0
    chunking_strategy: str = "hybrid"


class Chunk(BaseModel):
    """A single text chunk ready for embedding and vector storage."""

    model_config = ConfigDict(populate_by_name=True)

    chunk_id: str = Field(alias="chunkId")
    content: str
    source_url: str = Field(alias="sourceUrl")
    title: str = ""
    chunk_index: int = Field(alias="chunkIndex")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkStats(BaseModel):
    total_documents: int = 0
    documents_chunked: int = 0
    documents_skipped_empty: int = 0
    documents_skipped_duplicate: int = 0
    total_chunks: int = 0
    recursive_chunks: int = 0
    semantic_merges: int = 0
    avg_chunk_size: float = 0.0
    min_chunk_size: int = 0
    max_chunk_size: int = 0
    total_content_chars: int = 0


class ChunkResult(BaseModel):
    ingested_at: datetime
    source_file: str
    chunk_size: int
    chunk_overlap: int
    semantic_similarity_threshold: float
    stats: ChunkStats
    chunks: list[Chunk]
