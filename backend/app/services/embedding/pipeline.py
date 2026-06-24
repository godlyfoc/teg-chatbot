"""Index chunks.json into Qdrant with dense + sparse embeddings."""

import json
import logging
import random
from pathlib import Path

from qdrant_client.http import models

from app.config import Settings, get_settings
from app.models.chunk import Chunk, ChunkResult
from app.models.embedding import IndexingStats
from app.services.embedding.cache import EmbeddingCache, load_cache, save_cache
from app.services.embedding.dense import DenseEmbeddingClient
from app.services.embedding.sparse import BM25SparseEncoder
from app.services.embedding.stats import log_indexing_stats
from app.services.vectorstore.qdrant import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    QdrantStore,
    chunk_id_to_uuid,
)

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


def _qdrant_store(settings: Settings, *, dense_dimensions: int) -> QdrantStore:
    local_path = settings.qdrant_path.strip()
    return QdrantStore(
        collection=settings.qdrant_collection,
        path=str(_resolve_path(local_path)) if local_path else "",
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        dense_dimensions=dense_dimensions,
        upsert_batch_size=settings.index_upsert_batch_size,
    )


def _build_payload(chunk: Chunk) -> dict:
    metadata = dict(chunk.metadata)
    return {
        "chunkId": chunk.chunk_id,
        "content": chunk.content,
        "sourceUrl": chunk.source_url,
        "title": chunk.title,
        "chunkIndex": chunk.chunk_index,
        "language": metadata.get("language", "mixed"),
        "document_type": metadata.get("document_type", "html"),
        "content_type": metadata.get("content_type", "text/html"),
        "section": metadata.get("section"),
        "document_chunk_count": metadata.get("document_chunk_count", 0),
        "char_count": metadata.get("char_count", len(chunk.content)),
        "chunking_strategy": metadata.get("chunking_strategy", "hybrid"),
    }


def _validate_indexed(
    store: QdrantStore,
    chunks: list[Chunk],
    *,
    dense_dimensions: int,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    qdrant_count = store.count_points()
    if qdrant_count != len(chunks):
        errors.append(f"Point count mismatch: qdrant={qdrant_count}, chunks={len(chunks)}")

    sample_size = min(3, len(chunks))
    if sample_size:
        for chunk in random.sample(chunks, sample_size):
            payload = store.get_payload(chunk.chunk_id)
            if payload is None:
                errors.append(f"Missing point for chunkId={chunk.chunk_id}")
                continue
            if payload.get("content") != chunk.content:
                errors.append(f"Content mismatch for chunkId={chunk.chunk_id}")
            if payload.get("sourceUrl") != chunk.source_url:
                errors.append(f"sourceUrl mismatch for chunkId={chunk.chunk_id}")

    if dense_dimensions <= 0:
        errors.append("Invalid dense_dimensions")

    return len(errors) == 0, errors


def _upsert_to_qdrant(
    settings: Settings,
    chunks: list[Chunk],
    dense_vectors: list[list[float]],
    sparse_vectors: list,
    *,
    dense_dimensions: int,
    recreate: bool,
) -> tuple[int, int, int, int, bool, list[str]]:
    store = _qdrant_store(settings, dense_dimensions=dense_dimensions)
    store.ensure_collection(recreate=recreate or settings.index_recreate_collection)

    points: list[models.PointStruct] = []
    failed = 0
    for chunk, dense_vector, sparse_vector in zip(chunks, dense_vectors, sparse_vectors, strict=True):
        try:
            points.append(
                models.PointStruct(
                    id=chunk_id_to_uuid(chunk.chunk_id),
                    vector={
                        DENSE_VECTOR_NAME: dense_vector,
                        SPARSE_VECTOR_NAME: models.SparseVector(
                            indices=sparse_vector.indices,
                            values=sparse_vector.values,
                        ),
                    },
                    payload=_build_payload(chunk),
                )
            )
        except Exception as exc:
            failed += 1
            logger.warning("Failed to build point for %s: %s", chunk.chunk_id, exc)

    upserted = store.upsert_points(points)
    current_chunk_ids = {chunk.chunk_id for chunk in chunks}
    removed = store.delete_stale_points(current_chunk_ids)
    passed, errors = _validate_indexed(store, chunks, dense_dimensions=dense_dimensions)
    return upserted, failed, removed, store.count_points(), passed, errors


async def run_indexing(
    settings: Settings | None = None,
    *,
    input_path: Path | None = None,
    dry_run: bool = False,
    recreate: bool = False,
    from_cache: bool = False,
    embed_chunk_ids: set[str] | None = None,
) -> IndexingStats:
    settings = settings or get_settings()

    source_path = input_path or _resolve_path(settings.chunk_output_path)
    cache_path = _resolve_path(settings.index_cache_path)
    chunk_data = json.loads(source_path.read_text(encoding="utf-8"))
    chunk_result = ChunkResult.model_validate(chunk_data)
    chunks = chunk_result.chunks
    source_mtime = source_path.stat().st_mtime
    chunk_ids = [chunk.chunk_id for chunk in chunks]

    dense_vectors: list[list[float]]
    sparse_vectors: list
    dense_batches = 0
    dense_dimensions = settings.index_embedding_dimensions
    sparse_vocabulary_size = 0
    avg_sparse = 0.0
    embeddings_generated = 0

    cache = load_cache(cache_path) if cache_path.is_file() else None
    cache_valid = (
        cache is not None
        and cache.chunks_source_mtime == source_mtime
        and cache.chunk_ids == chunk_ids
    )
    incremental = embed_chunk_ids is not None

    if from_cache:
        if cache is None:
            raise FileNotFoundError(f"Embedding cache not found: {cache_path}")
        if not cache_valid:
            raise ValueError("chunks.json changed since cache was built — re-run without --from-cache")
        dense_vectors = cache.dense_vectors
        sparse_vectors = cache.sparse_vectors
        dense_dimensions = cache.dense_dimensions
        sparse_vocabulary_size = cache.sparse_vocabulary_size
        avg_sparse = cache.avg_sparse_terms
        embeddings_generated = 0
        logger.info("Loaded embeddings from cache (%s)", cache_path)
    elif cache_valid and not incremental:
        dense_vectors = cache.dense_vectors
        sparse_vectors = cache.sparse_vectors
        dense_dimensions = cache.dense_dimensions
        sparse_vocabulary_size = cache.sparse_vocabulary_size
        avg_sparse = cache.avg_sparse_terms
        embeddings_generated = 0
        logger.info("chunks.json unchanged — reusing embedding cache (%s)", cache_path)
    else:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for dense embedding")

        texts = [chunk.content for chunk in chunks]
        sparse_encoder = BM25SparseEncoder(max_terms=settings.index_sparse_max_terms)
        logger.info("Fitting BM25 on %d chunks...", len(texts))
        sparse_encoder.fit(texts)
        sparse_vectors = sparse_encoder.encode_batch(texts)
        avg_sparse = sparse_encoder.avg_nonzero_terms(texts)
        sparse_vocabulary_size = sparse_encoder.vocabulary_size

        cache_map: dict[str, list[float]] = {}
        if cache is not None and cache.chunk_ids:
            cache_map = dict(zip(cache.chunk_ids, cache.dense_vectors, strict=False))

        ids_to_embed = embed_chunk_ids if incremental else {chunk.chunk_id for chunk in chunks}
        texts_to_embed: list[str] = []
        embed_indices: list[int] = []
        for index, chunk in enumerate(chunks):
            if chunk.chunk_id in ids_to_embed or chunk.chunk_id not in cache_map:
                texts_to_embed.append(chunk.content)
                embed_indices.append(index)

        dense_vectors: list[list[float]] = [[] for _ in chunks]
        embeddings_generated = len(texts_to_embed)

        if texts_to_embed:
            dense_client = DenseEmbeddingClient(
                api_key=settings.openai_api_key,
                model=settings.index_embedding_model,
                batch_size=settings.index_embedding_batch_size,
            )
            if incremental:
                logger.info(
                    "Generating dense embeddings for %d changed chunks with %s...",
                    len(texts_to_embed),
                    settings.index_embedding_model,
                )
            else:
                logger.info("Generating dense embeddings with %s...", settings.index_embedding_model)
            new_dense_vectors = await dense_client.embed_texts(texts_to_embed)
            dense_batches = (len(texts_to_embed) + settings.index_embedding_batch_size - 1) // max(
                settings.index_embedding_batch_size, 1
            )
            for index, vector in zip(embed_indices, new_dense_vectors, strict=True):
                dense_vectors[index] = vector

        for index, chunk in enumerate(chunks):
            if dense_vectors[index]:
                continue
            cached = cache_map.get(chunk.chunk_id)
            if cached is None:
                raise ValueError(f"Missing embedding for chunk {chunk.chunk_id}")
            dense_vectors[index] = cached

        dense_dimensions = (
            len(dense_vectors[0]) if dense_vectors else settings.index_embedding_dimensions
        )

        save_cache(
            cache_path,
            EmbeddingCache(
                chunk_ids=chunk_ids,
                chunks_source_mtime=source_mtime,
                dense_vectors=dense_vectors,
                sparse_vectors=sparse_vectors,
                dense_dimensions=dense_dimensions,
                sparse_vocabulary_size=sparse_vocabulary_size,
                avg_sparse_terms=round(avg_sparse, 1),
            ),
        )
        logger.info("Saved embedding cache to %s", cache_path)

    stats = IndexingStats(
        chunks_total=len(chunks),
        dense_batches=dense_batches,
        dense_dimensions=dense_dimensions,
        sparse_vocabulary_size=sparse_vocabulary_size,
        avg_sparse_terms=round(avg_sparse, 1),
        embeddings_generated=embeddings_generated,
    )

    if dry_run:
        stats.chunks_indexed = len(chunks)
        stats.validation_passed = True
        log_indexing_stats(stats)
        return stats

    upserted, failed, removed, qdrant_points, passed, errors = _upsert_to_qdrant(
        settings,
        chunks,
        dense_vectors,
        sparse_vectors,
        dense_dimensions=dense_dimensions,
        recreate=recreate,
    )

    stats.chunks_indexed = upserted
    stats.chunks_failed = failed
    stats.chunks_removed = removed
    stats.qdrant_points = qdrant_points
    stats.validation_passed = passed
    stats.validation_errors = errors

    log_indexing_stats(stats)
    return stats
