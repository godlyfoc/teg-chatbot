"""Crawled document models."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

LanguageCode = Literal["en", "ga", "mixed"]


class CrawledDocument(BaseModel):
    url: str
    title: str = ""
    content: str
    type: str = "html"
    content_type: str = "text/html"
    language: LanguageCode = "mixed"
    ingested_at: datetime | None = None  # set in clean_documents() before save
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrawlStats(BaseModel):
    html_count: int = 0
    pdf_count: int = 0
    failed_count: int = 0
    total_content_chars: int = 0


class CrawlResult(BaseModel):
    ingested_at: datetime
    base_url: str
    stats: CrawlStats
    documents: list[CrawledDocument]
