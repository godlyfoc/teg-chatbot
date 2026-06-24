"""Shared text embedding services (dense + sparse)."""

from app.services.embedding.dense import DenseEmbeddingClient, cosine_similarity

__all__ = ["DenseEmbeddingClient", "cosine_similarity"]
