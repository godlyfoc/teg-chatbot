"""Response models for the full ingestion pipeline."""

from pydantic import BaseModel

from app.models.chunk import ChunkStats
from app.models.embedding import IndexingStats


class IngestionChangeSummary(BaseModel):
    documents_crawled: int = 0
    documents_changed: int = 0
    documents_added: int = 0
    documents_updated: int = 0
    documents_removed: int = 0
    documents_unchanged: int = 0


class IngestionStageStats(BaseModel):
    elapsed_seconds: float = 0.0
    skipped: bool = False


class IngestionCrawlStage(IngestionStageStats):
    html_count: int = 0
    pdf_count: int = 0
    failed_count: int = 0


class IngestionChunkStage(IngestionStageStats):
    documents_processed: int = 0
    chunks_generated: int = 0
    chunks_reused: int = 0
    stats: ChunkStats | None = None


class IngestionEmbedStage(IngestionStageStats):
    embeddings_generated: int = 0
    stats: IndexingStats | None = None


class IngestionResponse(BaseModel):
    status: str = "completed"
    skipped: bool = False
    message: str = ""
    elapsed_seconds: float = 0.0
    change: IngestionChangeSummary
    crawl: IngestionCrawlStage
    chunk: IngestionChunkStage
    embed: IngestionEmbedStage
