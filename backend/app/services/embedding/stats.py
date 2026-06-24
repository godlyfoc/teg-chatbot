"""Indexing statistics logging."""

import logging

from app.models.embedding import IndexingStats

logger = logging.getLogger(__name__)


def log_indexing_stats(stats: IndexingStats) -> None:
    logger.info("Indexing complete")
    logger.info("  Chunks total:          %d", stats.chunks_total)
    logger.info("  Chunks indexed:        %d", stats.chunks_indexed)
    logger.info("  Chunks failed:         %d", stats.chunks_failed)
    logger.info("  Chunks removed:        %d", stats.chunks_removed)
    logger.info("  Embeddings generated:%d", stats.embeddings_generated)
    logger.info("  Dense dimensions:      %d", stats.dense_dimensions)
    logger.info("  Sparse vocabulary:     %d", stats.sparse_vocabulary_size)
    logger.info("  Avg sparse terms/chunk:%.1f", stats.avg_sparse_terms)
    logger.info("  Qdrant points:         %d", stats.qdrant_points)
    logger.info("  Validation passed:     %s", stats.validation_passed)
    if stats.validation_errors:
        for error in stats.validation_errors:
            logger.warning("  Validation: %s", error)
