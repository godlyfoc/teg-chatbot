"""Extract PDF text in memory (no files saved to disk)."""

import asyncio
import logging
from io import BytesIO

import httpx
from bs4 import BeautifulSoup, Tag
from pypdf import PdfReader

from app.models.document import CrawledDocument

logger = logging.getLogger(__name__)

COOKIE_SELECTORS = [
    "#onetrust-banner-sdk",
    "#onetrust-consent-sdk",
    ".ot-sdk-container",
    "[id*='cookie']",
    "[class*='cookie']",
    "[id*='consent']",
    "[class*='consent']",
]

REMOVE_TAGS = [
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "img",
    "picture",
    "figure",
    "figcaption",
    "video",
    "audio",
    "source",
    "canvas",
    "map",
    "link",
    "meta",
]

# teg.ie wraps pages in <form>; never decompose form tags globally.
NAV_BOILERPLATE_SELECTORS = [
    "header",
    "footer",
    "nav",
    "aside",
    "[role='banner']",
    "[role='navigation']",
    "[role='contentinfo']",
    "#PhoneNav",
    "#MainNav",
    ".navbar",
    ".navbar-inverse",
    ".navbar-inner",
    ".navbar-collapse",
    ".nav-collapse",
    ".nav-desktop",
    ".NavHorizontal",
    ".navigation",
    ".site-header",
    ".site-footer",
    ".skip-link",
    ".sr-only",
    ".visually-hidden",
]

TEG_MAIN_SELECTORS = [
    "section#middle",
    ".BlogContent",
    ".BlogArticle",
    "#content",
]


def _decompose_matching(root: Tag, selectors: list[str]) -> None:
    for selector in selectors:
        for node in root.select(selector):
            node.decompose()


def _remove_tags(root: Tag, tag_names: list[str]) -> None:
    for tag in root.find_all(tag_names):
        tag.decompose()


def _extract_text(main: Tag) -> str:
    return main.get_text(separator="\n", strip=True)


def _find_main_content(soup: BeautifulSoup) -> Tag | None:
    for selector in TEG_MAIN_SELECTORS:
        node = soup.select_one(selector)
        if node and len(node.get_text(strip=True)) >= 30:
            return node

    return (
        soup.find("main")
        or soup.find(class_="content")
        or soup.find("article")
        or soup.body
    )


def _strip_navigation(main: Tag) -> None:
    _decompose_matching(main, NAV_BOILERPLATE_SELECTORS)
    for tag_name in ("button", "input", "select", "textarea"):
        for node in main.find_all(tag_name):
            node.decompose()


def html_to_document(url: str, html: str) -> CrawledDocument | None:
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    _remove_tags(soup, REMOVE_TAGS)
    _decompose_matching(soup, COOKIE_SELECTORS)

    main = _find_main_content(soup)
    if not main:
        return None

    _strip_navigation(main)
    _remove_tags(main, REMOVE_TAGS)

    content = _extract_text(main)
    if len(content.strip()) < 50:
        return None

    return CrawledDocument(url=url, title=title, content=content, type="html")


async def extract_pdf_texts(
    urls: list[str],
    concurrency: int = 25,
) -> tuple[list[CrawledDocument], int]:
    """Stream PDF bytes and extract text in memory — nothing written to disk."""
    if not urls:
        return [], 0

    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)

    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": "TEG-Chatbot-Crawler/1.0"},
    ) as client:

        async def fetch_pdf(url: str) -> CrawledDocument | None:
            async with semaphore:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    reader = PdfReader(BytesIO(response.content))
                    pages = [page.extract_text() or "" for page in reader.pages]
                    content = "\n\n".join(part.strip() for part in pages if part.strip())
                    if len(content) < 50:
                        return None

                    info = reader.metadata or {}
                    title = str(info.get("/Title", "") or "").strip()
                    metadata: dict = {"page_count": len(reader.pages)}
                    if info.get("/Author"):
                        metadata["author"] = str(info["/Author"])

                    return CrawledDocument(
                        url=url,
                        title=title,
                        content=content,
                        type="pdf",
                        content_type="application/pdf",
                        metadata=metadata,
                    )
                except Exception as exc:
                    logger.warning("PDF failed %s: %s", url, exc)
                    return None

        results = await asyncio.gather(*[fetch_pdf(url) for url in urls])

    documents = [doc for doc in results if doc is not None]
    failed = len(urls) - len(documents)
    logger.info("PDF text extracted %d/%d (in-memory only)", len(documents), len(urls))
    return documents, failed
