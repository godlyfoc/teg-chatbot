"""Discover all HTML pages (BFS) + PDF links via Crawl4AI."""

import logging
import re
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field

import httpx
from crawl4ai import AsyncWebCrawler

from app.models.document import CrawledDocument
from app.services.crawler.crawl4ai_config import build_browser_config, build_run_config
from app.services.crawler.extractor import crawl4ai_result_to_document
from app.services.crawler.utils import (
    extract_links_from_html,
    is_pdf_url,
    normalize_html_url,
    normalize_pdf_url,
)

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


def _iter_crawl_results(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if hasattr(raw, "_results"):
        return list(raw)
    return [raw]


def _result_url(result) -> str:
    return (result.redirected_url or result.url or "").strip()


def _collect_pdf_links(
    result,
    page_url: str,
    base_url: str,
    allowed_domains: list[str],
    pdf_urls: set[str],
) -> None:
    links = result.links or {}
    for bucket in ("internal", "external"):
        for link in links.get(bucket, []):
            href = link.get("href") if isinstance(link, dict) else getattr(link, "href", None)
            if href and is_pdf_url(href):
                pdf = normalize_pdf_url(href, page_url, allowed_domains)
                if pdf:
                    pdf_urls.add(pdf)

    html = result.html or result.cleaned_html
    if html:
        _, page_pdfs = extract_links_from_html(html, page_url, base_url, allowed_domains)
        pdf_urls.update(page_pdfs)


def _discover_html_links(
    result,
    page_url: str,
    base_url: str,
    allowed_domains: list[str],
) -> set[str]:
    discovered: set[str] = set()
    links = result.links or {}
    for link in links.get("internal", []):
        href = link.get("href") if isinstance(link, dict) else getattr(link, "href", None)
        if not href:
            continue
        page = normalize_html_url(href, page_url, allowed_domains)
        if page:
            discovered.add(page)

    html = result.html or result.cleaned_html
    if html:
        html_links, _ = extract_links_from_html(html, page_url, base_url, allowed_domains)
        discovered.update(html_links)

    return discovered


async def discover_and_extract_html(
    base_url: str,
    allowed_domains: list[str],
    concurrency: int = 25,
    *,
    browser_fallback: bool = True,
    browser_wait_ms: int = 2500,
    max_depth: int = 50,
) -> DiscoveryResult:
    """
    Walk all internal HTML pages (BFS via Crawl4AI), extract text, collect PDF links.
    PDFs are not followed or saved — only their URLs are collected for text extraction.
    """
    result = DiscoveryResult()
    seen_html: set[str] = set()
    depths: dict[str, int] = {}
    queue: deque[str] = deque()

    start = normalize_html_url(base_url, base_url, allowed_domains)
    if not start:
        logger.error("Invalid crawl base URL: %s", base_url)
        return result

    queue.append(start)
    depths[start] = 0

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": "TEG-Chatbot-Crawler/1.0"},
    ) as client:
        for url in await _sitemap_html_urls(client, base_url, allowed_domains):
            if url not in depths:
                queue.append(url)
                depths[url] = 0

    run_config = build_run_config(
        concurrency=concurrency,
        browser_wait_ms=browser_wait_ms,
        browser_fallback=browser_fallback,
    )
    browser_config = build_browser_config()
    processed = 0

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while queue:
            batch: list[tuple[str, int]] = []
            while queue and len(batch) < concurrency:
                url = queue.popleft()
                if url in seen_html:
                    continue
                seen_html.add(url)
                batch.append((url, depths.get(url, 0)))

            if not batch:
                break

            raw = await crawler.arun_many([url for url, _ in batch], config=run_config)
            for crawl_result, (_, parent_depth) in zip(
                _iter_crawl_results(raw), batch, strict=False
            ):
                if not crawl_result.success:
                    result.html_failed += 1

                page_url = _result_url(crawl_result)
                if not page_url:
                    continue

                _collect_pdf_links(
                    crawl_result,
                    page_url,
                    base_url,
                    allowed_domains,
                    result.pdf_urls,
                )

                document = crawl4ai_result_to_document(crawl_result)
                if document:
                    result.html_documents.append(document)

                if parent_depth < max_depth:
                    for link in _discover_html_links(
                        crawl_result,
                        page_url,
                        base_url,
                        allowed_domains,
                    ):
                        if link not in seen_html and link not in depths:
                            queue.append(link)
                            depths[link] = parent_depth + 1

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
