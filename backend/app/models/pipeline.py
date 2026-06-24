"""API models for crawl, chunk, and embed pipelines."""

from pydantic import BaseModel

from app.models.chunk import ChunkStats
from app.models.embedding import IndexingStats


class CrawlJobResponse(BaseModel):
    status: str = "completed"
    output_path: str = ""
    elapsed_seconds: float = 0.0
    html_count: int = 0
    pdf_count: int = 0
    failed_count: int = 0
    total_content_chars: int = 0


class ChunkJobResponse(BaseModel):
    status: str = "completed"
    output_path: str = ""
    elapsed_seconds: float = 0.0
    stats: ChunkStats


class EmbedJobResponse(BaseModel):
    status: str = "completed"
    output_path: str = ""
    qdrant_collection: str = ""
    elapsed_seconds: float = 0.0
    stats: IndexingStats
