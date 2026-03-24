"""
app/db/chroma.py
ChromaDB client wrapper.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

_COLLECTION_NAME = "gitlab_handbook"


class ChromaStore:
    def __init__(self):
        cfg = get_settings()
        self._client = chromadb.PersistentClient(
            path=cfg.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB ready",
            collection=_COLLECTION_NAME,
            doc_count=self._collection.count(),
        )

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> int:
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.debug("Upserted chunks", count=len(ids))
        return len(ids)

    def delete_by_source_url(self, url: str) -> None:
        results = self._collection.get(where={"source_url": url})
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            logger.info("Deleted chunks for URL", url=url, count=len(results["ids"]))

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 8,
        score_threshold: float = 0.35,
        where: Optional[Dict] = None,
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, max(1, self._collection.count())),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        items: List[Tuple[str, Dict[str, Any], float]] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1.0 - (dist / 2.0)
            if score >= score_threshold:
                items.append((doc, meta, score))

        items.sort(key=lambda x: x[2], reverse=True)
        return items

    def get_by_url(self, url: str) -> List[Dict]:
        return self._collection.get(where={"source_url": url}, include=["metadatas"])

    def count(self) -> int:
        return self._collection.count()

    def collection_info(self) -> Dict[str, Any]:
        return {
            "name": self._collection.name,
            "count": self._collection.count(),
            "metadata": self._collection.metadata,
        }


@lru_cache(maxsize=1)
def get_chroma_store() -> ChromaStore:
    return ChromaStore()
