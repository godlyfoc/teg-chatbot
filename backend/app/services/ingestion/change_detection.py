"""Detect meaningful content changes between crawl runs."""

import hashlib
from dataclasses import dataclass, field

from app.models.document import CrawledDocument


def document_content_hash(content: str) -> str:
    normalized = " ".join(content.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _index_documents(documents: list[CrawledDocument]) -> dict[str, str]:
    """Map URL → content hash, keeping the first occurrence per URL."""
    indexed: dict[str, str] = {}
    for document in documents:
        if document.url in indexed:
            continue
        indexed[document.url] = document_content_hash(document.content)
    return indexed


@dataclass
class CrawlChangeReport:
    documents_crawled: int
    documents_added: int
    documents_updated: int
    documents_removed: int
    documents_unchanged: int
    documents_changed: int
    has_changes: bool
    added_urls: set[str] = field(default_factory=set)
    updated_urls: set[str] = field(default_factory=set)
    removed_urls: set[str] = field(default_factory=set)
    unchanged_urls: set[str] = field(default_factory=set)


def compare_crawl_documents(
    previous: list[CrawledDocument],
    current: list[CrawledDocument],
) -> CrawlChangeReport:
    """Compare two crawl document lists by URL and normalized content hash."""
    previous_by_url = _index_documents(previous)
    current_by_url = _index_documents(current)

    previous_urls = set(previous_by_url)
    current_urls = set(current_by_url)

    added_urls = current_urls - previous_urls
    removed_urls = previous_urls - current_urls
    common_urls = previous_urls & current_urls
    updated_urls = {
        url for url in common_urls if previous_by_url[url] != current_by_url[url]
    }
    unchanged_urls = common_urls - updated_urls

    documents_changed = len(added_urls) + len(updated_urls) + len(removed_urls)
    has_changes = documents_changed > 0 or not previous_by_url

    return CrawlChangeReport(
        documents_crawled=len(current_by_url),
        documents_added=len(added_urls),
        documents_updated=len(updated_urls),
        documents_removed=len(removed_urls),
        documents_unchanged=len(unchanged_urls),
        documents_changed=documents_changed,
        has_changes=has_changes,
        added_urls=added_urls,
        updated_urls=updated_urls,
        removed_urls=removed_urls,
        unchanged_urls=unchanged_urls,
    )
