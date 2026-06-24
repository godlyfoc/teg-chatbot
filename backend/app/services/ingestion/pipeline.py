"""Orchestrate crawl → chunk → embed with incremental change detection."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.models.chunk import Chunk, ChunkResult
from app.models.document import CrawlResult
from app.models.ingestion import (
    IngestionChangeSummary,
    IngestionChunkStage,
    IngestionCrawlStage,
    IngestionEmbedStage,
    IngestionResponse,
)
from app.services.chunking.pipeline import chunk_documents, save_chunk_result
from app.services.chunking.settings import ChunkingConfig
from app.services.chunking.stats import build_chunk_stats, log_chunk_stats
from app.services.crawler.pipeline import run_crawl, save_crawl_result
from app.services.embedding.pipeline import run_indexing
from app.services.ingestion.change_detection import compare_crawl_documents

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


def _load_crawl_result(path: Path) -> CrawlResult | None:
    if not path.is_file():
        return None
    return CrawlResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _load_chunk_result(path: Path) -> ChunkResult | None:
    if not path.is_file():
        return None
    return ChunkResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _change_summary(report) -> IngestionChangeSummary:
    return IngestionChangeSummary(
        documents_crawled=report.documents_crawled,
        documents_changed=report.documents_changed,
        documents_added=report.documents_added,
        documents_updated=report.documents_updated,
        documents_removed=report.documents_removed,
        documents_unchanged=report.documents_unchanged,
    )


async def run_ingestion(settings: Settings | None = None) -> IngestionResponse:
    """
    Run the full ingestion pipeline with change detection.

    Crawls the configured site, compares against the previous crawl, and only
    rechunks / re-embeds content that was added or updated. Unchanged documents
    reuse existing chunks and cached dense embeddings.
    """
    settings = settings or get_settings()
    pipeline_started = time.perf_counter()

    crawl_path = _resolve_path(settings.crawl_output_path)
    chunk_path = _resolve_path(settings.chunk_output_path)

    previous_crawl = _load_crawl_result(crawl_path)
    previous_chunks = _load_chunk_result(chunk_path)

    # --- Stage 1: Crawl ---
    logger.info("Ingestion stage 1/3: crawling %s", settings.crawl_base_url)
    crawl_started = time.perf_counter()
    try:
        crawl_result = await run_crawl(settings, save=False)
    except Exception:
        logger.exception("Ingestion failed during crawl")
        raise

    if not isinstance(crawl_result, CrawlResult):
        raise RuntimeError("Unexpected crawl result")

    crawl_stage = IngestionCrawlStage(
        elapsed_seconds=round(time.perf_counter() - crawl_started, 1),
        html_count=crawl_result.stats.html_count,
        pdf_count=crawl_result.stats.pdf_count,
        failed_count=crawl_result.stats.failed_count,
    )
    logger.info(
        "Crawl complete in %.1fs — %d HTML, %d PDF",
        crawl_stage.elapsed_seconds,
        crawl_stage.html_count,
        crawl_stage.pdf_count,
    )

    change_report = compare_crawl_documents(
        previous_crawl.documents if previous_crawl else [],
        crawl_result.documents,
    )

    if not change_report.has_changes:
        logger.info(
            "No content changes detected (%d documents unchanged) — skipping chunking and embedding",
            change_report.documents_unchanged,
        )
        return IngestionResponse(
            status="skipped",
            skipped=True,
            message="No content changes detected. Chunking and embedding were skipped.",
            elapsed_seconds=round(time.perf_counter() - pipeline_started, 1),
            change=_change_summary(change_report),
            crawl=crawl_stage,
            chunk=IngestionChunkStage(skipped=True),
            embed=IngestionEmbedStage(skipped=True),
        )

    logger.info(
        "Content changes detected — added=%d updated=%d removed=%d unchanged=%d",
        change_report.documents_added,
        change_report.documents_updated,
        change_report.documents_removed,
        change_report.documents_unchanged,
    )

    try:
        save_crawl_result(crawl_result, settings, output_path=crawl_path)
    except Exception:
        logger.exception("Ingestion failed while saving crawl output")
        raise

    # --- Stage 2: Chunk (incremental) ---
    chunk_stage = IngestionChunkStage()
    embed_stage = IngestionEmbedStage()
    config = ChunkingConfig.from_settings(settings)

    urls_to_process = change_report.added_urls | change_report.updated_urls
    is_full_chunk = previous_chunks is None or not change_report.unchanged_urls

    logger.info("Ingestion stage 2/3: chunking")
    chunk_started = time.perf_counter()

    try:
        if is_full_chunk:
            documents_to_chunk = crawl_result.documents
            kept_chunks: list[Chunk] = []
            logger.info("Full chunking — processing all %d documents", len(documents_to_chunk))
        else:
            documents_to_chunk = [
                document
                for document in crawl_result.documents
                if document.url in urls_to_process
            ]
            kept_chunks = [
                chunk
                for chunk in previous_chunks.chunks
                if chunk.source_url in change_report.unchanged_urls
            ]
            logger.info(
                "Incremental chunking — %d changed documents, %d chunks reused",
                len(documents_to_chunk),
                len(kept_chunks),
            )

        (
            new_chunks,
            documents_chunked,
            documents_skipped_empty,
            documents_skipped_duplicate,
            total_recursive_chunks,
            total_semantic_merges,
        ) = await chunk_documents(documents_to_chunk, settings)

        all_chunks = kept_chunks + new_chunks
        chunk_stats = build_chunk_stats(
            total_documents=len(crawl_result.documents),
            documents_chunked=documents_chunked,
            documents_skipped_empty=documents_skipped_empty,
            documents_skipped_duplicate=documents_skipped_duplicate,
            recursive_chunks=total_recursive_chunks,
            semantic_merges=total_semantic_merges,
            chunks=all_chunks,
        )
        log_chunk_stats(chunk_stats)

        try:
            source_display = str(crawl_path.relative_to(_backend_root()))
        except ValueError:
            source_display = str(crawl_path)

        chunk_result = ChunkResult(
            ingested_at=datetime.now(timezone.utc),
            source_file=source_display,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            semantic_similarity_threshold=config.semantic_similarity_threshold,
            stats=chunk_stats,
            chunks=all_chunks,
        )
        save_chunk_result(chunk_result, settings, output_path=chunk_path)
    except Exception:
        logger.exception("Ingestion failed during chunking")
        raise

    chunk_stage = IngestionChunkStage(
        elapsed_seconds=round(time.perf_counter() - chunk_started, 1),
        documents_processed=len(urls_to_process) if not is_full_chunk else len(crawl_result.documents),
        chunks_generated=len(new_chunks),
        chunks_reused=len(kept_chunks),
        stats=chunk_stats,
    )
    logger.info(
        "Chunking complete in %.1fs — %d new chunks, %d reused",
        chunk_stage.elapsed_seconds,
        chunk_stage.chunks_generated,
        chunk_stage.chunks_reused,
    )

    # --- Stage 3: Embed + index ---
    logger.info("Ingestion stage 3/3: embedding and indexing")
    embed_started = time.perf_counter()

    embed_chunk_ids = {chunk.chunk_id for chunk in new_chunks}
    try:
        index_stats = await run_indexing(
            settings,
            embed_chunk_ids=embed_chunk_ids if not is_full_chunk else None,
        )
    except Exception:
        logger.exception("Ingestion failed during embedding/indexing")
        raise

    if not index_stats.validation_passed:
        raise RuntimeError(
            f"Indexing validation failed: {', '.join(index_stats.validation_errors)}"
        )

    embed_stage = IngestionEmbedStage(
        elapsed_seconds=round(time.perf_counter() - embed_started, 1),
        embeddings_generated=index_stats.embeddings_generated,
        stats=index_stats,
    )
    logger.info(
        "Embedding complete in %.1fs — %d embeddings generated, %d Qdrant points",
        embed_stage.elapsed_seconds,
        embed_stage.embeddings_generated,
        index_stats.qdrant_points,
    )

    return IngestionResponse(
        status="completed",
        skipped=False,
        message="Ingestion pipeline completed successfully.",
        elapsed_seconds=round(time.perf_counter() - pipeline_started, 1),
        change=_change_summary(change_report),
        crawl=crawl_stage,
        chunk=chunk_stage,
        embed=embed_stage,
    )
