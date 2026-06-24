"""Pipeline APIs — crawl, chunk, and embed/index."""

import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.ingestion import IngestionResponse
from app.models.pipeline import ChunkJobResponse, CrawlJobResponse, EmbedJobResponse
from app.services.chunking.pipeline import run_chunking
from app.services.crawler.pipeline import run_crawl
from app.services.embedding.pipeline import run_indexing
from app.services.ingestion.pipeline import run_ingestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


@router.post("/crawl", response_model=CrawlJobResponse)
async def run_crawl_job(settings: Settings = Depends(get_settings)):
    started = time.perf_counter()
    try:
        result = await run_crawl(settings)
    except Exception as exc:
        logger.exception("Crawl failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = time.perf_counter() - started
    output_path = _resolve_path(settings.crawl_output_path)

    return CrawlJobResponse(
        output_path=str(output_path),
        elapsed_seconds=round(elapsed, 1),
        html_count=result.stats.html_count,
        pdf_count=result.stats.pdf_count,
        failed_count=result.stats.failed_count,
        total_content_chars=result.stats.total_content_chars,
    )


@router.post("/chunk", response_model=ChunkJobResponse)
async def run_chunk_job(settings: Settings = Depends(get_settings)):
    crawl_path = _resolve_path(settings.crawl_output_path)
    if not crawl_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Crawled content not found at {crawl_path}. Run POST /api/pipeline/crawl first.",
        )

    started = time.perf_counter()
    try:
        result = await run_chunking(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chunking failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = time.perf_counter() - started
    return ChunkJobResponse(
        output_path=str(_resolve_path(settings.chunk_output_path)),
        elapsed_seconds=round(elapsed, 1),
        stats=result.stats,
    )


@router.post("/embed", response_model=EmbedJobResponse)
async def run_embed_job(settings: Settings = Depends(get_settings)):
    """Load chunks from chunks.json, embed them, and upsert into Qdrant."""
    chunk_path = _resolve_path(settings.chunk_output_path)
    if not chunk_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Chunks not found at {chunk_path}.",
        )

    started = time.perf_counter()
    try:
        stats = await run_indexing(settings)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Embedding/indexing failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    elapsed = time.perf_counter() - started
    storage = settings.qdrant_storage

    if not stats.validation_passed:
        raise HTTPException(
            status_code=500,
            detail={"message": "Indexing validation failed", "errors": stats.validation_errors},
        )

    return EmbedJobResponse(
        output_path=storage,
        qdrant_collection=settings.qdrant_collection,
        elapsed_seconds=round(elapsed, 1),
        stats=stats,
    )


@router.post("/ingest", response_model=IngestionResponse)
async def run_ingestion_job(settings: Settings = Depends(get_settings)):
    """
    Run the full ingestion pipeline: crawl → chunk → embed → Qdrant.

    Compares crawled content against the previous run and skips chunking /
    embedding when nothing meaningful changed.
    """
    try:
        return await run_ingestion(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Ingestion pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
