"""Persist embedding cache for upsert-only reruns."""

import pickle
from dataclasses import dataclass
from pathlib import Path

from app.services.embedding.sparse import SparseVector


@dataclass
class EmbeddingCache:
    chunk_ids: list[str]
    chunks_source_mtime: float
    dense_vectors: list[list[float]]
    sparse_vectors: list[SparseVector]
    dense_dimensions: int
    sparse_vocabulary_size: int
    avg_sparse_terms: float


def save_cache(path: Path, cache: EmbeddingCache) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(cache, handle)


def load_cache(path: Path) -> EmbeddingCache:
    with path.open("rb") as handle:
        return pickle.load(handle)
