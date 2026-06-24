"""Embedding / indexing models."""

from pydantic import BaseModel, Field


class IndexingStats(BaseModel):
    chunks_total: int = 0
    chunks_indexed: int = 0
    chunks_failed: int = 0
    chunks_removed: int = 0
    embeddings_generated: int = 0
    dense_batches: int = 0
    dense_dimensions: int = 0
    sparse_vocabulary_size: int = 0
    avg_sparse_terms: float = 0.0
    qdrant_points: int = 0
    validation_passed: bool = False
    validation_errors: list[str] = Field(default_factory=list)
