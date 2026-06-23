"""Normalize crawled page text and remove site boilerplate."""

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.document import CrawledDocument, CrawlResult, CrawlStats
from app.services.language import detect_language

MIN_CONTENT_LENGTH = 50
WHITESPACE_RE = re.compile(r"[ \t]+")
MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

COOKIE_PHRASES = (
    "Ionad Sainroghanna Príobháideachais",
    "Sainroghanna Príobháideachais",
    "Fianáin Feidhmiúcháin",
    "Fianáin Fhíor-riachtanacha",
    "Glac le Fianáin",
    "Ceadaigh Gach Ceann",
    "cookiepedia.co.uk",
)

# Blog post metadata: "By tegadmin , Monday, 12th February 2024 | 0 comments"
POST_META_RE = re.compile(
    r"\s*By\s+\w+\s*,\s*"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"\d+(?:st|nd|rd|th)?\s+\w+\s+\d{4}\s*\|\s*\d+\s*comments\s*",
    re.IGNORECASE,
)

# Blog listing pages: "By tegadmin 06/03/2026 | 0 comments"
POST_META_SHORT_RE = re.compile(
    r"\s*By\s+\w+\s+\d{1,2}/\d{1,2}/\d{4}\s*\|\s*\d+\s*comments\s*",
    re.IGNORECASE,
)

BLOG_CATEGORY_RE = re.compile(
    r"^Select Blog Category(?:\s+Category\s+\d+)*\s*",
    re.IGNORECASE,
)

RSS_FOOTER_RE = re.compile(r"\s*RSS\s+Feed\s*Perma\s+Link\s*#\d+\s*$", re.IGNORECASE)
MAP_ALT_RE = re.compile(
    r"\s*click to (?:view|open|print)(?:\s+or\s+print)?(?:\s+via)?\s+[\w.]+\s*$",
    re.IGNORECASE,
)

BOILERPLATE_LINE_RE = re.compile(
    r"^(?:"
    r"RSS\s+Feed|Perma\s+Link|Skip to (?:main )?content|"
    r"Share (?:on )?(?:Facebook|Twitter|LinkedIn)|"
    r"click to (?:view|open|print|download).*|"
    r"(?:View|Print) (?:on )?googlemaps\.com"
    r")$",
    re.IGNORECASE,
)


def _strip_cookie_noise(text: str) -> str:
    for phrase in COOKIE_PHRASES:
        idx = text.find(phrase)
        if idx != -1:
            text = text[:idx]
    return text.strip()


def _strip_leading_title(text: str, title: str) -> str:
    """Drop duplicated page title from the start of body text."""
    if not title:
        return text
    stripped_title = title.strip()
    if not stripped_title:
        return text
    if text.startswith(stripped_title):
        return text[len(stripped_title) :].lstrip()
    return text


def _strip_boilerplate_lines(text: str) -> str:
    lines = text.split("\n")
    kept = [line for line in lines if line.strip() and not BOILERPLATE_LINE_RE.match(line.strip())]
    return "\n".join(kept)


def clean_content(text: str, *, title: str = "") -> str:
    """Remove navigation noise, metadata, and normalize whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _strip_cookie_noise(text)
    text = _strip_leading_title(text, title)
    text = BLOG_CATEGORY_RE.sub("", text)
    text = POST_META_RE.sub("", text)
    text = POST_META_SHORT_RE.sub("", text)
    text = RSS_FOOTER_RE.sub("", text)
    text = MAP_ALT_RE.sub("", text)
    text = _strip_boilerplate_lines(text)
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    text = "\n".join(lines)
    return MULTI_NEWLINE_RE.sub("\n\n", text).strip()


def clean_documents(
    documents: list[CrawledDocument],
    ingested_at: datetime,
) -> list[CrawledDocument]:
    seen: set[str] = set()
    cleaned: list[CrawledDocument] = []

    for doc in documents:
        if doc.url in seen:
            continue
        content = clean_content(doc.content, title=doc.title)
        if len(content) < MIN_CONTENT_LENGTH:
            continue
        seen.add(doc.url)
        cleaned.append(
            doc.model_copy(
                update={
                    "content": content,
                    "language": detect_language(content, doc.url),
                    "ingested_at": ingested_at,
                }
            )
        )

    return cleaned


def build_stats(documents: list[CrawledDocument], failed_count: int) -> CrawlStats:
    return CrawlStats(
        html_count=sum(1 for d in documents if d.type == "html"),
        pdf_count=sum(1 for d in documents if d.type == "pdf"),
        failed_count=failed_count,
        total_content_chars=sum(len(d.content) for d in documents),
    )


def cleanup_crawl_result(result: CrawlResult) -> CrawlResult:
    """Re-clean all documents in a crawl result (e.g. after rule updates)."""
    ingested_at = result.ingested_at or datetime.now(timezone.utc)
    documents = [
        CrawledDocument(
            url=raw.url,
            title=raw.title,
            content=raw.content,
            type=raw.type,
            content_type=raw.content_type,
            language=raw.language,
            ingested_at=raw.ingested_at,
            metadata=raw.metadata,
        )
        for raw in result.documents
    ]
    cleaned = clean_documents(documents, ingested_at=ingested_at)
    failed_count = result.stats.failed_count + (len(result.documents) - len(cleaned))
    return result.model_copy(
        update={
            "documents": cleaned,
            "stats": build_stats(cleaned, failed_count),
        }
    )


def _write_json_atomic(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp"
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def cleanup_crawled_file(path: Path) -> CrawlResult:
    """Load crawled_content.json, apply cleanup rules, and overwrite the file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    result = CrawlResult.model_validate(data)
    cleaned = cleanup_crawl_result(result)
    _write_json_atomic(path, cleaned.model_dump(mode="json"))
    return cleaned
