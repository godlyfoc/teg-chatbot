"""OpenAI embedding helpers for semantic chunking."""

from app.services.embedding.dense import (
    DenseEmbeddingClient as EmbeddingClient,
    average_embeddings,
    cosine_similarity,
)

__all__ = ["EmbeddingClient", "average_embeddings", "cosine_similarity"]
