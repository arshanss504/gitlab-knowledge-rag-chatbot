#!/usr/bin/env python3
"""
scripts/ingest_cli.py
CLI tool to run the ingestion pipeline directly (without the FastAPI server).

Usage:
    python scripts/ingest_cli.py                        # ingest defaults
    python scripts/ingest_cli.py --force                # force re-ingest all
    python scripts/ingest_cli.py --url https://...      # custom URL
    python scripts/ingest_cli.py --stats                # show collection stats
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_ingest(urls: list[str], force: bool):
    from backend.core.logging import configure_logging

    configure_logging()

    from backend.core.logging import get_logger

    logger = get_logger("ingest_cli")

    from backend.services.ingest import get_ingest_pipeline

    pipeline = get_ingest_pipeline()
    logger.info("Starting ingestion", urls=urls, force=force)

    print(f"\nIngesting {len(urls)} source URL(s)...")
    await pipeline.run(source_urls=urls, force_reingest=force)
    print("\nIngestion complete.")


async def show_stats():
    from backend.core.logging import configure_logging

    configure_logging()
    from backend.db.chroma import get_chroma_store

    store = get_chroma_store()
    info = store.collection_info()
    print(f"\nChromaDB Collection: {info['name']}")
    print(f"  Total chunks:  {info['count']}")
    print(f"  Metadata:      {info['metadata']}")


def main():
    parser = argparse.ArgumentParser(description="GitLab RAG Ingestion CLI")
    parser.add_argument(
        "--url",
        "-u",
        action="append",
        dest="urls",
        help="Source URL to ingest (can be repeated). Defaults to GitLab Handbook + Direction.",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-ingest all pages (ignore content hash cache).",
    )
    parser.add_argument(
        "--stats",
        "-s",
        action="store_true",
        help="Show ChromaDB collection stats and exit.",
    )
    args = parser.parse_args()

    if args.stats:
        asyncio.run(show_stats())
        return

    from backend.core.config import CRAWL_SOURCE_URLS

    urls = args.urls or CRAWL_SOURCE_URLS

    asyncio.run(run_ingest(urls=urls, force=args.force))


if __name__ == "__main__":
    main()
