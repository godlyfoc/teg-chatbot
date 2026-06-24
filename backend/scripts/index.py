#!/usr/bin/env python3
"""Index chunks.json into Qdrant with OpenAI dense + BM25 sparse embeddings."""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.embedding.pipeline import run_indexing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hybrid indexing: chunks.json → Qdrant (OpenAI dense + BM25 sparse)"
    )
    parser.add_argument("--input", help="Input chunks.json path")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the Qdrant collection before indexing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Encode only — no Qdrant writes",
    )
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help="Upsert from saved embedding cache (skip OpenAI/BM25 re-encode)",
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
    input_path = Path(args.input) if args.input else None

    started = time.perf_counter()
    try:
        stats = await run_indexing(
            settings,
            input_path=input_path,
            dry_run=args.dry_run,
            recreate=args.recreate,
            from_cache=args.from_cache,
        )
    except Exception as exc:
        print(f"Indexing failed: {exc}", file=sys.stderr)
        return 1

    elapsed = time.perf_counter() - started

    print()
    print("Indexing summary")
    print("----------------")
    print(f"Chunks total:           {stats.chunks_total}")
    print(f"Chunks indexed:         {stats.chunks_indexed}")
    print(f"Chunks failed:          {stats.chunks_failed}")
    print(f"Dense model dims:       {stats.dense_dimensions}")
    print(f"Sparse vocabulary:      {stats.sparse_vocabulary_size}")
    print(f"Avg sparse terms/chunk: {stats.avg_sparse_terms}")
    if not args.dry_run:
        print(f"Qdrant points:          {stats.qdrant_points}")
        print(f"Validation passed:      {stats.validation_passed}")
        if stats.validation_errors:
            print("Validation errors:")
            for error in stats.validation_errors:
                print(f"  - {error}")
    print(f"Completed in {elapsed:.1f}s")
    return 0 if stats.validation_passed or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
