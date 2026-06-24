"""Crawl all HTML pages + PDF text → crawled_content.json."""

import json
import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings, get_settings
from app.models.document import CrawlResult
from app.services.crawler.cleaner import build_stats, clean_documents
from app.services.crawler.discovery import discover_and_extract_html
from app.services.crawler.extractor import extract_pdf_texts

logger = logging.getLogger(__name__)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _backend_root() / path


def _write_json_atomic(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp"
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _save_result(result: CrawlResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(output_path, result.model_dump(mode="json"))


async def run_crawl(
    settings: Settings | None = None,
    *,
    dry_run: bool = False,
    save: bool = True,
) -> CrawlResult | dict:
    settings = settings or get_settings()
    base_url = settings.crawl_base_url
    allowed_domains = settings.crawl_allowed_domains
    concurrency = settings.crawl_concurrency

    started = time.perf_counter()
    ingested_at = datetime.now(timezone.utc)

    discovery = await discover_and_extract_html(base_url, allowed_domains, concurrency)

    if dry_run:
        return {
            "html_count": len(discovery.html_documents),
            "pdf_count": len(discovery.pdf_urls),
        }

    pdf_urls = sorted(discovery.pdf_urls)
    logger.info("Extracting text from %d PDFs (in-memory)...", len(pdf_urls))
    pdf_docs, pdf_failed = await extract_pdf_texts(pdf_urls, concurrency)

    all_docs = discovery.html_documents + pdf_docs
    failed = discovery.html_failed + pdf_failed
    cleaned = clean_documents(all_docs, ingested_at=ingested_at)
    stats = build_stats(cleaned, failed)

    result = CrawlResult(
        ingested_at=ingested_at,
        base_url=base_url,
        stats=stats,
        documents=cleaned,
    )

    output_path = _resolve_path(settings.crawl_output_path)
    if save:
        _save_result(result, output_path)

    elapsed = time.perf_counter() - started
    logger.info(
        "Done in %.1fs — %d HTML, %d PDF%s",
        elapsed,
        stats.html_count,
        stats.pdf_count,
        f" → {output_path}" if save else " (not saved)",
    )
    return result


def save_crawl_result(
    result: CrawlResult,
    settings: Settings | None = None,
    *,
    output_path: Path | None = None,
) -> Path:
    """Persist a crawl result to crawled_content.json."""
    settings = settings or get_settings()
    target = output_path or _resolve_path(settings.crawl_output_path)
    _save_result(result, target)
    return target
