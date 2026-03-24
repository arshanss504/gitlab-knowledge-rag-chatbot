import asyncio
from typing import Dict, List, Optional

from google.api_core.exceptions import ResourceExhausted

from backend.core.config import CRAWL_SOURCE_URLS
from backend.core.logging import get_logger
from backend.db.chroma import ChromaStore, get_chroma_store
from backend.services.chunker import SemanticChunker
from backend.services.crawler import GitLabCrawler
from backend.services.embedder import EmbeddingService, get_embedder

logger = get_logger(__name__)

_EMBED_BATCH_SIZE = 80


class IngestionPipeline:
    def __init__(
        self,
        store: Optional[ChromaStore] = None,
        embedder: Optional[EmbeddingService] = None,
    ):
        self._store = store or get_chroma_store()
        self._embedder = embedder or get_embedder()
        self._chunker = SemanticChunker()

    async def run(
        self,
        source_urls: Optional[List[str]] = None,
        force_reingest: bool = False,
    ) -> None:
        urls = source_urls or CRAWL_SOURCE_URLS

        logger.info("Ingestion started", urls=urls)

        known_hashes: Dict[str, str] = {}
        if not force_reingest:
            known_hashes = self._load_known_hashes(urls)

        crawler = GitLabCrawler(known_hashes=known_hashes)

        pending_chunks = []
        pending_texts = []
        pages_ingested = 0
        pages_skipped = 0
        cooldown_until = 0

        try:
            async for page in crawler.crawl(urls):
                if page is None:
                    pages_skipped += 1
                    continue

                try:
                    chunks = self._chunker.chunk_page(
                        source_url=page.url,
                        title=page.title,
                        sections=page.sections,
                        extra_metadata={"domain": page.source_domain},
                    )
                    if not chunks:
                        continue

                    pending_chunks.extend(chunks)
                    pending_texts.extend(c.text for c in chunks)
                    pages_ingested += 1

                    now = asyncio.get_event_loop().time()
                    if len(pending_chunks) >= _EMBED_BATCH_SIZE and now >= cooldown_until:
                        batch_c = pending_chunks[:_EMBED_BATCH_SIZE]
                        batch_t = pending_texts[:_EMBED_BATCH_SIZE]
                        embedded = await self._embed_and_upsert(batch_c, batch_t)
                        pending_chunks = pending_chunks[_EMBED_BATCH_SIZE:]
                        pending_texts = pending_texts[_EMBED_BATCH_SIZE:]
                        logger.info("Batch processed", done=len(batch_c), new=embedded, remaining=len(pending_chunks))
                        if embedded:
                            cooldown_until = asyncio.get_event_loop().time() + 61

                except ResourceExhausted:
                    cooldown_until = asyncio.get_event_loop().time() + 65
                    logger.warning("Rate limited, pausing 65s — will keep crawling and batch later")
                except Exception as e:
                    logger.error("Failed to process page", url=page.url, error=str(e))

            consecutive_failures = 0
            while pending_chunks:
                now = asyncio.get_event_loop().time()
                if now < cooldown_until:
                    wait = cooldown_until - now
                    logger.info("Waiting for rate limit cooldown", seconds=round(wait))
                    await asyncio.sleep(wait)

                batch_c = pending_chunks[:_EMBED_BATCH_SIZE]
                batch_t = pending_texts[:_EMBED_BATCH_SIZE]
                try:
                    embedded = await self._embed_and_upsert(batch_c, batch_t)
                    pending_chunks = pending_chunks[_EMBED_BATCH_SIZE:]
                    pending_texts = pending_texts[_EMBED_BATCH_SIZE:]
                    consecutive_failures = 0
                    logger.info("Batch processed", done=len(batch_c), new=embedded, remaining=len(pending_chunks))
                    if embedded:
                        cooldown_until = asyncio.get_event_loop().time() + 61
                except ResourceExhausted:
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        logger.error(
                            "Daily quota likely exhausted — stopping ingestion. "
                            "Retry with a fresh API key or wait for quota reset.",
                            remaining_chunks=len(pending_chunks),
                            consecutive_failures=consecutive_failures,
                        )
                        break
                    backoff = 60 * (2 ** (consecutive_failures - 1))
                    cooldown_until = asyncio.get_event_loop().time() + backoff
                    logger.warning(
                        "Rate limited, backing off",
                        wait_seconds=backoff,
                        attempt=consecutive_failures,
                        remaining=len(pending_chunks),
                    )

            logger.info(
                "Ingestion complete",
                ingested=pages_ingested,
                skipped=pages_skipped,
            )

        except Exception as e:
            logger.error("Ingestion failed", error=str(e))

    async def _embed_and_upsert(self, chunks, texts):
        chunk_ids = [c.id for c in chunks]
        try:
            existing = self._store._collection.get(ids=chunk_ids)
            existing_ids = set(existing["ids"])
        except Exception:
            existing_ids = set()

        new = [
            (c, t)
            for c, t in zip(chunks, texts)
            if c.id not in existing_ids
        ]

        if not new:
            logger.info("All chunks already in DB, skipping", skipped=len(chunks))
            return 0

        new_chunks, new_texts = zip(*new)
        new_chunks, new_texts = list(new_chunks), list(new_texts)

        logger.info(
            "Embedding new chunks only",
            total=len(chunks),
            new=len(new_chunks),
            skipped=len(existing_ids),
        )
        embeddings = await self._embedder.embed_documents(new_texts)
        self._store.upsert(
            ids=[c.id for c in new_chunks],
            embeddings=embeddings,
            documents=new_texts,
            metadatas=[c.metadata for c in new_chunks],
        )
        return len(new_chunks)

    def _load_known_hashes(self, source_urls: List[str]) -> Dict[str, str]:
        known: Dict[str, str] = {}
        for url in source_urls:
            try:
                result = self._store.get_by_url(url)
                for meta in result.get("metadatas", []):
                    if meta.get("source_url") and meta.get("content_hash"):
                        known[meta["source_url"]] = meta["content_hash"]
            except Exception:
                pass
        logger.info("Loaded known hashes for incremental update", count=len(known))
        return known


_pipeline: IngestionPipeline | None = None


def get_ingest_pipeline() -> IngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestionPipeline()
    return _pipeline
