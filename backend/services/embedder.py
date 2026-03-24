import asyncio
from typing import List

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import GEMINI_EMBEDDING_MODEL, get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

_BATCH_SIZE = 80


def _configure_gemini():
    genai.configure(api_key=get_settings().gemini_api_key)


@retry(
    retry=retry_if_not_exception_type(ResourceExhausted),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
def _embed_batch_sync(texts: List[str], task_type: str, model: str) -> List[List[float]]:
    result = genai.embed_content(
        model=model,
        content=texts,
        task_type=task_type,
    )
    return result["embedding"] if len(texts) == 1 else result["embedding"]


class EmbeddingService:
    def __init__(self):
        _configure_gemini()
        self._model = GEMINI_EMBEDDING_MODEL
        logger.info("EmbeddingService ready", model=self._model)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return await self._embed_in_batches(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, query: str) -> List[float]:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _embed_batch_sync([query], "RETRIEVAL_QUERY", self._model),
        )
        return result if isinstance(result[0], float) else result[0]

    async def _embed_in_batches(
        self, texts: List[str], task_type: str
    ) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        all_embeddings: List[List[float]] = []

        total_batches = (len(texts) + _BATCH_SIZE - 1) // _BATCH_SIZE
        logger.info("Embedding started", total_texts=len(texts), batch_size=_BATCH_SIZE, api_calls=total_batches)

        for i in range(0, len(texts), _BATCH_SIZE):
            if i > 0:
                await asyncio.sleep(61)

            batch = texts[i : i + _BATCH_SIZE]
            logger.info(
                "Embedding batch",
                batch_index=i // _BATCH_SIZE,
                batch_size=len(batch),
                task_type=task_type,
            )
            result = await loop.run_in_executor(
                None,
                lambda b=batch: _embed_batch_sync(b, task_type, self._model),
            )
            if isinstance(result[0], float):
                all_embeddings.append(result)
            else:
                all_embeddings.extend(result)

        return all_embeddings


_embedder: EmbeddingService | None = None


def get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService()
    return _embedder
