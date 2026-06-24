"""Orchestrate hybrid chunking over crawled documents."""

import hashlib
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.models.chunk import Chunk, ChunkResult
from app.models.document import CrawlResult, CrawledDocument
from app.services.chunking.embeddings import EmbeddingClient
from app.services.chunking.postprocess import coalesce_small_chunks
from app.services.chunking.recursive import recursive_chunk_document
from app.services.chunking.semantic import optimize_chunk_boundaries
from app.services.chunking.settings import ChunkingConfig
from app.services.chunking.stats import build_chunk_stats, log_chunk_stats

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


def _write_json_atomic(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp"
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _content_hash(content: str) -> str:
    normalized = " ".join(content.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _make_chunk_id(source_url: str, chunk_index: int, content: str) -> str:
    digest = hashlib.sha256(f"{source_url}:{chunk_index}:{content}".encode("utf-8")).hexdigest()
    return digest[:32]


def _build_chunk_metadata(
    document: CrawledDocument,
    *,
    section: str | None,
    separator_level: str | None,
    document_chunk_count: int,
    content: str,
    chunking_strategy: str,
) -> dict:
    metadata = dict(document.metadata)
    metadata.update(
        {
            "language": document.language,
            "document_type": document.type,
            "content_type": document.content_type,
            "section": section,
            "separator_level": separator_level,
            "document_ingested_at": document.ingested_at.isoformat() if document.ingested_at else None,
            "document_chunk_count": document_chunk_count,
            "char_count": len(content),
            "chunking_strategy": chunking_strategy,
        }
    )
    return metadata


def _finalize_chunks(
    document: CrawledDocument,
    pieces: list,
    *,
    chunking_strategy: str,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for index, piece in enumerate(pieces):
        content = piece.content.strip()
        if not content:
            continue
        chunks.append(
            Chunk(
                chunk_id=_make_chunk_id(document.url, index, content),
                content=content,
                source_url=document.url,
                title=document.title,
                chunk_index=index,
                metadata=_build_chunk_metadata(
                    document,
                    section=piece.section,
                    separator_level=piece.separator_level,
                    document_chunk_count=0,
                    content=content,
                    chunking_strategy=chunking_strategy,
                ),
            )
        )

    total = len(chunks)
    for chunk in chunks:
        chunk.metadata["document_chunk_count"] = total
    return chunks


async def chunk_document(
    document: CrawledDocument,
    config: ChunkingConfig,
    embedder: EmbeddingClient | None,
) -> tuple[list[Chunk], int, int]:
    """Chunk a single document using recursive splitting and optional semantic merging."""
    recursive_pieces = recursive_chunk_document(
        document.content,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        max_chunk_size=config.max_chunk_size,
    )
    recursive_count = len(recursive_pieces)
    semantic_merges = 0
    strategy = "recursive"

    if config.enable_semantic and embedder and len(recursive_pieces) > 1:
        recursive_pieces, merge_stats = await optimize_chunk_boundaries(
            recursive_pieces,
            embedder=embedder,
            similarity_threshold=config.semantic_similarity_threshold,
            min_chunk_size=config.min_chunk_size,
            max_chunk_size=config.max_chunk_size,
        )
        semantic_merges = merge_stats.merges
        strategy = "hybrid"

    recursive_pieces = coalesce_small_chunks(
        recursive_pieces,
        min_chunk_size=config.min_chunk_size,
        max_chunk_size=config.max_chunk_size,
    )

    chunks = _finalize_chunks(document, recursive_pieces, chunking_strategy=strategy)
    return chunks, recursive_count, semantic_merges


async def chunk_documents(
    documents: list[CrawledDocument],
    settings: Settings | None = None,
) -> tuple[list[Chunk], int, int, int, int]:
    """
    Chunk a list of crawled documents.

    Returns (chunks, documents_chunked, documents_skipped_empty,
    documents_skipped_duplicate, recursive_chunks, semantic_merges).
    """
    settings = settings or get_settings()
    config = ChunkingConfig.from_settings(settings)

    embedder: EmbeddingClient | None = None
    if config.enable_semantic:
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for semantic chunking. "
                "Set CHUNK_ENABLE_SEMANTIC=false to use recursive chunking only."
            )
        embedder = EmbeddingClient(
            api_key=settings.openai_api_key,
            model=config.embedding_model,
            batch_size=config.embedding_batch_size,
        )

    all_chunks: list[Chunk] = []
    seen_urls: set[str] = set()
    seen_content_hashes: set[str] = set()
    documents_chunked = 0
    documents_skipped_empty = 0
    documents_skipped_duplicate = 0
    total_recursive_chunks = 0
    total_semantic_merges = 0

    for document in documents:
        if document.url in seen_urls:
            documents_skipped_duplicate += 1
            continue
        seen_urls.add(document.url)

        content = document.content.strip()
        if not content:
            documents_skipped_empty += 1
            continue

        content_hash = _content_hash(content)
        if content_hash in seen_content_hashes:
            documents_skipped_duplicate += 1
            continue
        seen_content_hashes.add(content_hash)

        doc_chunks, recursive_count, semantic_merges = await chunk_document(
            document, config, embedder
        )
        if not doc_chunks:
            documents_skipped_empty += 1
            continue

        all_chunks.extend(doc_chunks)
        documents_chunked += 1
        total_recursive_chunks += recursive_count
        total_semantic_merges += semantic_merges

    return (
        all_chunks,
        documents_chunked,
        documents_skipped_empty,
        documents_skipped_duplicate,
        total_recursive_chunks,
        total_semantic_merges,
    )


async def run_chunking(
    settings: Settings | None = None,
    *,
    input_path: Path | None = None,
    output_path: Path | None = None,
    save: bool = True,
) -> ChunkResult:
    """
    Load crawled_content.json, apply hybrid chunking, and optionally write chunks.json.

    Does not modify the crawl pipeline or crawled_content.json.
    """
    settings = settings or get_settings()
    config = ChunkingConfig.from_settings(settings)

    source_path = input_path or _resolve_path(settings.crawl_output_path)
    target_path = output_path or _resolve_path(settings.chunk_output_path)

    crawl_data = json.loads(source_path.read_text(encoding="utf-8"))
    crawl_result = CrawlResult.model_validate(crawl_data)

    (
        all_chunks,
        documents_chunked,
        documents_skipped_empty,
        documents_skipped_duplicate,
        total_recursive_chunks,
        total_semantic_merges,
    ) = await chunk_documents(crawl_result.documents, settings)

    stats = build_chunk_stats(
        total_documents=len(crawl_result.documents),
        documents_chunked=documents_chunked,
        documents_skipped_empty=documents_skipped_empty,
        documents_skipped_duplicate=documents_skipped_duplicate,
        recursive_chunks=total_recursive_chunks,
        semantic_merges=total_semantic_merges,
        chunks=all_chunks,
    )

    try:
        source_display = str(source_path.relative_to(_backend_root()))
    except ValueError:
        source_display = str(source_path)

    result = ChunkResult(
        ingested_at=datetime.now(timezone.utc),
        source_file=source_display,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        semantic_similarity_threshold=config.semantic_similarity_threshold,
        stats=stats,
        chunks=all_chunks,
    )

    log_chunk_stats(stats)

    if save:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(target_path, result.model_dump(mode="json", by_alias=True))
        logger.info("Wrote %d chunks to %s", len(all_chunks), target_path)

    return result


def save_chunk_result(
    result: ChunkResult,
    settings: Settings | None = None,
    *,
    output_path: Path | None = None,
) -> Path:
    """Persist a chunk result to chunks.json."""
    settings = settings or get_settings()
    target = output_path or _resolve_path(settings.chunk_output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(target, result.model_dump(mode="json", by_alias=True))
    logger.info("Wrote %d chunks to %s", len(result.chunks), target)
    return target
