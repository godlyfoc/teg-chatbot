"""Tests for ingestion change detection."""

from app.models.document import CrawledDocument
from app.services.ingestion.change_detection import compare_crawl_documents, document_content_hash


def _doc(url: str, content: str) -> CrawledDocument:
    return CrawledDocument(url=url, title="Test", content=content)


def test_document_content_hash_normalizes_whitespace():
    assert document_content_hash("hello  world") == document_content_hash("hello world")


def test_compare_detects_no_changes():
    docs = [_doc("https://example.com/a", "Alpha content")]
    report = compare_crawl_documents(docs, [_doc("https://example.com/a", "Alpha content")])
    assert report.has_changes is False
    assert report.documents_changed == 0
    assert report.documents_unchanged == 1


def test_compare_detects_added_updated_removed():
    previous = [
        _doc("https://example.com/a", "Alpha"),
        _doc("https://example.com/b", "Beta"),
    ]
    current = [
        _doc("https://example.com/a", "Alpha updated"),
        _doc("https://example.com/c", "Gamma"),
    ]
    report = compare_crawl_documents(previous, current)
    assert report.has_changes is True
    assert report.documents_added == 1
    assert report.documents_updated == 1
    assert report.documents_removed == 1
    assert "https://example.com/c" in report.added_urls
    assert "https://example.com/a" in report.updated_urls
    assert "https://example.com/b" in report.removed_urls


def test_compare_first_run_has_changes():
    current = [_doc("https://example.com/a", "Alpha")]
    report = compare_crawl_documents([], current)
    assert report.has_changes is True
    assert report.documents_added == 1
