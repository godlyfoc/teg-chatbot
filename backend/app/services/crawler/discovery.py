"""Discover all HTML pages (BFS) + PDF links; extract HTML in the same pass."""

import logging
import re
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field

import httpx

from app.models.document import CrawledDocument
from app.services.crawler.extractor import html_to_document
from app.services.crawler.utils import extract_links_from_html, normalize_html_url

logger = logging.getLogger(__name__)

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


@dataclass
class DiscoveryResult:
    html_documents: list[CrawledDocument] = field(default_factory=list)
    pdf_urls: set[str] = field(default_factory=set)
    html_failed: int = 0


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    return response.text.lstrip("\ufeff")


def _parse_locs(xml_text: str) -> list[str]:
    urls: list[str] = []
    try:
        root = ET.fromstring(xml_text)
        for loc in root.findall(".//sm:loc", SITEMAP_NS):
            if loc.text:
                urls.append(loc.text.strip())
        if not urls:
            for loc in root.iter():
                if loc.tag.endswith("loc") and loc.text:
                    urls.append(loc.text.strip())
    except ET.ParseError:
        urls = [m.strip() for m in LOC_RE.findall(xml_text)]
    return urls


async def _sitemap_html_urls(
    client: httpx.AsyncClient,
    base_url: str,
    allowed_domains: list[str],
) -> set[str]:
    sitemap_url = f"{base_url.rstrip('/')}/sitemap.xml"
    urls: set[str] = set()

    try:
        root_xml = await _fetch_text(client, sitemap_url)
        locs = _parse_locs(root_xml)

        if "sitemapindex" in root_xml.lower():
            for child in [u for u in locs if u.endswith(".xml")]:
                try:
                    locs.extend(_parse_locs(await _fetch_text(client, child)))
                except httpx.HTTPError as exc:
                    logger.warning("Child sitemap failed %s: %s", child, exc)

        for raw in locs:
            normalized = normalize_html_url(raw, base_url, allowed_domains)
            if normalized:
                urls.add(normalized)

        logger.info("Sitemap seed: %d HTML URLs", len(urls))
    except httpx.HTTPError as exc:
        logger.warning("Sitemap unavailable: %s", exc)

    return urls


async def discover_and_extract_html(
    base_url: str,
    allowed_domains: list[str],
    concurrency: int = 25,
) -> DiscoveryResult:
    """
    Walk all internal HTML pages (BFS via httpx), extract text, collect PDF links.
    PDFs are not followed or saved — only their URLs are collected for text extraction.
    """
    import asyncio

    result = DiscoveryResult()
    seen_html: set[str] = set()
    queue: deque[str] = deque()

    start = normalize_html_url(base_url, base_url, allowed_domains)
    if start:
        queue.append(start)

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": "TEG-Chatbot-Crawler/1.0"},
    ) as client:
        for url in await _sitemap_html_urls(client, base_url, allowed_domains):
            queue.append(url)

        processed = 0
        while queue:
            batch: list[str] = []
            while queue and len(batch) < concurrency:
                url = queue.popleft()
                if url in seen_html:
                    continue
                seen_html.add(url)
                batch.append(url)

            if not batch:
                break

            async def fetch_one(url: str) -> tuple[str, str | None]:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        return url, None
                    return url, response.text
                except httpx.HTTPError as exc:
                    logger.debug("Fetch failed %s: %s", url, exc)
                    return url, None

            responses = await asyncio.gather(*[fetch_one(url) for url in batch])

            for url, html in responses:
                if not html:
                    result.html_failed += 1
                    continue

                doc = html_to_document(url, html)
                if doc:
                    result.html_documents.append(doc)

                link_html, link_pdfs = extract_links_from_html(
                    html, url, base_url, allowed_domains
                )
                result.pdf_urls.update(link_pdfs)
                for link in link_html:
                    if link not in seen_html:
                        queue.append(link)

                processed += 1
                if processed % 50 == 0:
                    logger.info(
                        "Crawling: %d HTML done, %d PDF links found, queue %d",
                        len(result.html_documents),
                        len(result.pdf_urls),
                        len(queue),
                    )

    logger.info(
        "HTML crawl complete: %d pages, %d PDF links found, %d failed",
        len(result.html_documents),
        len(result.pdf_urls),
        result.html_failed,
    )
    return result
