#!/usr/bin/env python3
"""Re-clean crawled_content.json without re-crawling the site."""

import argparse
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.crawler.cleaner import cleanup_crawled_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove boilerplate from crawled_content.json (headers, footers, RSS, etc.)"
    )
    parser.add_argument(
        "--input",
        help="Path to crawled_content.json (default: CRAWL_OUTPUT_PATH from settings)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = get_settings()
    path = Path(args.input) if args.input else BACKEND_ROOT / settings.crawl_output_path
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    before = path.stat().st_size
    result = cleanup_crawled_file(path)
    after = path.stat().st_size

    print(f"Cleaned {len(result.documents)} documents")
    print(f"HTML: {result.stats.html_count} | PDF: {result.stats.pdf_count}")
    print(f"Total chars: {result.stats.total_content_chars:,}")
    print(f"File size: {before:,} -> {after:,} bytes")
    print(f"Output: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
