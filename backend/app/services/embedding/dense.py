"""OpenAI dense embedding client."""

import logging
from collections.abc import Sequence

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def average_embeddings(left: Sequence[float], right: Sequence[float]) -> list[float]:
    """Average two embeddings (used after merging adjacent chunks)."""
    return [(a + b) / 2 for a, b in zip(left, right, strict=True)]


class DenseEmbeddingClient:
    """Batch dense embedding client backed by OpenAI."""

    def __init__(self, api_key: str, model: str, batch_size: int = 64):
        self.client = AsyncOpenAI(api_key=api_key, timeout=20.0)
        self.model = model
        self.batch_size = batch_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = await self.client.embeddings.create(model=self.model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend(item.embedding for item in ordered)
            logger.debug("Dense embedded batch %d-%d", start, start + len(batch))

        return vectors
