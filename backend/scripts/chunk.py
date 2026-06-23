#!/usr/bin/env python3
"""Chunk crawled_content.json using hybrid recursive + semantic splitting."""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings, get_settings
from app.services.chunking.pipeline import run_chunking


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hybrid chunking for crawled_content.json → chunks.json"
    )
    parser.add_argument("--input", help="Input crawled_content.json path")
    parser.add_argument("--output", help="Output chunks.json path")
    parser.add_argument(
        "--recursive-only",
        action="store_true",
        help="Skip semantic merging (no embedding API calls)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Compute statistics without writing chunks.json",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    settings = get_settings()
    if args.recursive_only:
        settings = Settings(**{**settings.model_dump(), "chunk_enable_semantic": False})

    input_path = Path(args.input) if args.input else None
    output_path = Path(args.output) if args.output else None

    started = time.perf_counter()
    result = await run_chunking(
        settings,
        input_path=input_path,
        output_path=output_path,
        save=not args.stats_only,
    )
    elapsed = time.perf_counter() - started

    stats = result.stats
    print()
    print("Chunking summary")
    print("----------------")
    print(f"Documents total:      {stats.total_documents}")
    print(f"Documents chunked:    {stats.documents_chunked}")
    print(f"Skipped (empty):      {stats.documents_skipped_empty}")
    print(f"Skipped (duplicate):  {stats.documents_skipped_duplicate}")
    print(f"Recursive chunks:     {stats.recursive_chunks}")
    print(f"Semantic merges:      {stats.semantic_merges}")
    print(f"Final chunks:         {stats.total_chunks}")
    print(f"Avg chunk size:       {stats.avg_chunk_size:.1f} chars")
    print(f"Min / max chunk size: {stats.min_chunk_size} / {stats.max_chunk_size} chars")
    print(f"Completed in {elapsed:.1f}s")
    if not args.stats_only:
        print(f"Output: {args.output or settings.chunk_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
