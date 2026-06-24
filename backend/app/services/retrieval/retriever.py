"""Hybrid dense + sparse retrieval against Qdrant."""

import json
import logging
import time
from pathlib import Path

from app.config import Settings, get_settings
from app.models.chunk import ChunkResult
from app.models.retrieval import RetrievedChunk, RetrievalResult
from app.services.embedding.dense import DenseEmbeddingClient
from app.services.embedding.sparse import BM25SparseEncoder
from app.services.vectorstore.qdrant import QdrantStore

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


class _SparseEncoderCache:
    """In-memory BM25 encoder fitted on chunks.json, invalidated on file change."""

    def __init__(self) -> None:
        self._encoder: BM25SparseEncoder | None = None
        self._source_mtime: float | None = None

    def get(self, settings: Settings) -> BM25SparseEncoder:
        chunk_path = _resolve_path(settings.chunk_output_path)
        if not chunk_path.is_file():
            raise FileNotFoundError(f"Chunks not found at {chunk_path}")

        mtime = chunk_path.stat().st_mtime
        if self._encoder is not None and self._source_mtime == mtime:
            return self._encoder

        chunk_data = json.loads(chunk_path.read_text(encoding="utf-8"))
        chunks = ChunkResult.model_validate(chunk_data).chunks
        texts = [chunk.content for chunk in chunks]

        encoder = BM25SparseEncoder(max_terms=settings.index_sparse_max_terms)
        encoder.fit(texts)
        self._encoder = encoder
        self._source_mtime = mtime
        logger.info("Fitted BM25 sparse encoder on %d chunks for retrieval", len(texts))
        return encoder


_sparse_cache = _SparseEncoderCache()


def _qdrant_store(settings: Settings) -> QdrantStore:
    local_path = settings.qdrant_path.strip()
    return QdrantStore(
        collection=settings.qdrant_collection,
        path=str(_resolve_path(local_path)) if local_path else "",
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        dense_dimensions=settings.index_embedding_dimensions,
    )


def _payload_to_chunk(payload: dict, score: float) -> RetrievedChunk | None:
    content = payload.get("content")
    chunk_id = payload.get("chunkId")
    source_url = payload.get("sourceUrl")
    if not content or not chunk_id or not source_url:
        return None

    return RetrievedChunk(
        chunk_id=str(chunk_id),
        content=str(content),
        source_url=str(source_url),
        title=str(payload.get("title") or ""),
        score=score,
        language=str(payload.get("language") or "mixed"),
    )


class Retriever:
    """Retrieve relevant chunks using hybrid dense + BM25 sparse search."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._dense_client = DenseEmbeddingClient(
            api_key=self.settings.openai_api_key,
            model=self.settings.index_embedding_model,
            batch_size=1,
        )

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> RetrievalResult:
        started = time.perf_counter()
        settings = self.settings
        limit = top_k or settings.retrieval_top_k

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for retrieval")

        store = _qdrant_store(settings)
        if not store.client.collection_exists(settings.qdrant_collection):
            logger.warning("Qdrant collection %s does not exist", settings.qdrant_collection)
            return RetrievalResult(query=query, chunks=[], elapsed_seconds=0.0)

        if store.count_points() == 0:
            logger.warning("Qdrant collection %s is empty", settings.qdrant_collection)
            return RetrievalResult(query=query, chunks=[], elapsed_seconds=0.0)

        dense_vectors = await self._dense_client.embed_texts([query])
        dense_vector = dense_vectors[0]

        sparse_encoder = _sparse_cache.get(settings)
        sparse_vector = sparse_encoder.encode(query)

        hits = store.hybrid_search(
            dense_vector=dense_vector,
            sparse_indices=sparse_vector.indices,
            sparse_values=sparse_vector.values,
            limit=limit,
            prefetch_limit=settings.retrieval_prefetch_limit,
        )

        chunks: list[RetrievedChunk] = []
        seen_ids: set[str] = set()
        for payload, score in hits:
            chunk = _payload_to_chunk(payload, score)
            if chunk is None or chunk.chunk_id in seen_ids:
                continue
            seen_ids.add(chunk.chunk_id)
            chunks.append(chunk)

        elapsed = round(time.perf_counter() - started, 3)
        logger.info(
            "Retrieved %d chunks for query (%.3fs): %r",
            len(chunks),
            elapsed,
            query[:80],
        )
        return RetrievalResult(query=query, chunks=chunks, elapsed_seconds=elapsed)
