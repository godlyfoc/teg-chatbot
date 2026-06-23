#!/usr/bin/env python3
"""Crawl teg.ie → data/crawled_content.json"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.crawler.pipeline import run_crawl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl teg.ie into crawled_content.json")
    parser.add_argument("--dry-run", action="store_true", help="Discovery only, show counts")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    settings = get_settings()
    started = time.perf_counter()
    result = await run_crawl(settings, dry_run=args.dry_run)
    elapsed = time.perf_counter() - started

    if args.dry_run:
        print(f"HTML pages: {result['html_count']}")
        print(f"PDF links:  {result['pdf_count']}")
        print(f"Completed in {elapsed:.1f}s")
        return 0

    print(f"Crawl complete in {elapsed:.1f}s")
    print(f"HTML: {result.stats.html_count} | PDF: {result.stats.pdf_count}")
    print(f"Failed: {result.stats.failed_count}")
    print(f"Output: {settings.crawl_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
