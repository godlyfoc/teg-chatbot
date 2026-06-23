"""Chunking configuration."""

from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class ChunkingConfig:
    """Tunable chunking parameters (also exposed via environment variables)."""

    chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_size: int = 80
    max_chunk_size: int = 1200
    semantic_similarity_threshold: float = 0.75
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 64
    enable_semantic: bool = True

    @classmethod
    def from_settings(cls, settings: Settings) -> "ChunkingConfig":
        return cls(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            min_chunk_size=settings.chunk_min_size,
            max_chunk_size=settings.chunk_max_size,
            semantic_similarity_threshold=settings.chunk_semantic_similarity_threshold,
            embedding_model=settings.chunk_embedding_model,
            embedding_batch_size=settings.chunk_embedding_batch_size,
            enable_semantic=settings.chunk_enable_semantic,
        )
