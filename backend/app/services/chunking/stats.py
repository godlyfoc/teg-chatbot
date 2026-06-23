"""Chunk generation statistics and logging."""

import logging

from app.models.chunk import Chunk, ChunkStats

logger = logging.getLogger(__name__)


def build_chunk_stats(
    *,
    total_documents: int,
    documents_chunked: int,
    documents_skipped_empty: int,
    documents_skipped_duplicate: int,
    recursive_chunks: int,
    semantic_merges: int,
    chunks: list[Chunk],
) -> ChunkStats:
    sizes = [len(chunk.content) for chunk in chunks]
    return ChunkStats(
        total_documents=total_documents,
        documents_chunked=documents_chunked,
        documents_skipped_empty=documents_skipped_empty,
        documents_skipped_duplicate=documents_skipped_duplicate,
        total_chunks=len(chunks),
        recursive_chunks=recursive_chunks,
        semantic_merges=semantic_merges,
        avg_chunk_size=round(sum(sizes) / len(sizes), 1) if sizes else 0.0,
        min_chunk_size=min(sizes) if sizes else 0,
        max_chunk_size=max(sizes) if sizes else 0,
        total_content_chars=sum(sizes),
    )


def log_chunk_stats(stats: ChunkStats) -> None:
    logger.info("Chunking complete")
    logger.info("  Documents total:     %d", stats.total_documents)
    logger.info("  Documents chunked:   %d", stats.documents_chunked)
    logger.info("  Skipped (empty):     %d", stats.documents_skipped_empty)
    logger.info("  Skipped (duplicate): %d", stats.documents_skipped_duplicate)
    logger.info("  Recursive chunks:    %d", stats.recursive_chunks)
    logger.info("  Semantic merges:     %d", stats.semantic_merges)
    logger.info("  Final chunks:        %d", stats.total_chunks)
    logger.info("  Avg chunk size:      %.1f chars", stats.avg_chunk_size)
    logger.info("  Min / max size:      %d / %d chars", stats.min_chunk_size, stats.max_chunk_size)
