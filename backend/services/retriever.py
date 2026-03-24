from dataclasses import dataclass
from typing import List, Optional

from backend.core.logging import get_logger
from backend.db.chroma import ChromaStore, get_chroma_store
from backend.services.embedder import EmbeddingService, get_embedder

logger = get_logger(__name__)

_TOP_K = 8
_SCORE_THRESHOLD = 0.35


@dataclass
class RetrievedChunk:
    text: str
    source_url: str
    section_url: str
    title: str
    section: str
    relevance_score: float
    chunk_index: int


class RetrieverService:
    def __init__(
        self,
        store: Optional[ChromaStore] = None,
        embedder: Optional[EmbeddingService] = None,
    ):
        self._store = store or get_chroma_store()
        self._embedder = embedder or get_embedder()

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        conversation_context: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        k = top_k or _TOP_K

        effective_query = query
        if conversation_context:
            effective_query = f"{conversation_context}\n\nCurrent question: {query}"

        query_embedding = await self._embedder.embed_query(effective_query)

        candidates = self._store.query(
            query_embedding=query_embedding,
            top_k=k,
            score_threshold=_SCORE_THRESHOLD,
        )

        if not candidates:
            logger.info("No candidates above threshold", query=query[:80])
            return []

        results = []
        for text, meta, score in candidates:
            results.append(
                RetrievedChunk(
                    text=text,
                    source_url=meta.get("source_url", ""),
                    section_url=meta.get("section_url", meta.get("source_url", "")),
                    title=meta.get("title", "GitLab"),
                    section=meta.get("section", ""),
                    relevance_score=round(score, 4),
                    chunk_index=meta.get("chunk_index", 0),
                )
            )

        logger.info("Retrieval complete", query=query[:80], returned=len(results))
        return results
