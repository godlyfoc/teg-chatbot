"""Tests for teg.ie HTML extraction."""

import httpx
import pytest

from app.services.crawler.extractor import html_to_document


@pytest.mark.parametrize(
    "url,min_chars",
    [
        ("https://www.teg.ie/", 200),
        ("https://www.teg.ie/news/teg-b1-exam-for-mie-b-oid-applicants.902.html", 200),
    ],
)
def test_html_to_document_extracts_teg_pages(url: str, min_chars: int):
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": "TEG-Chatbot-Crawler/1.0"},
    )
    response.raise_for_status()
    document = html_to_document(url, response.text)
    assert document is not None
    assert len(document.content) >= min_chars
