import uuid
from typing import List, Optional

from backend.core.logging import get_logger
from backend.models.schemas import ChatResponse, Source
from backend.services.generator import GeneratorService, get_generator
from backend.services.memory import ConversationMemory, get_memory
from backend.services.retriever import RetrievedChunk, RetrieverService

logger = get_logger(__name__)


def _build_sources(chunks: List[RetrievedChunk]) -> List[Source]:
    seen: dict[str, Source] = {}
    for chunk in chunks:
        key = chunk.section_url
        if key not in seen or chunk.relevance_score > seen[key].relevance_score:
            seen[key] = Source(
                title=chunk.title,
                url=chunk.section_url,
                section=chunk.section or None,
                relevance_score=chunk.relevance_score,
            )
    return sorted(seen.values(), key=lambda s: s.relevance_score, reverse=True)


class RAGPipeline:
    def __init__(
        self,
        retriever: Optional[RetrieverService] = None,
        generator: Optional[GeneratorService] = None,
        memory: Optional[ConversationMemory] = None,
    ):
        from backend.services.retriever import RetrieverService as RS

        self._retriever = retriever or RS()
        self._generator = generator or get_generator()
        self._memory = memory or get_memory()

    async def run(self, query: str, session_id: str) -> ChatResponse:
        query_id = str(uuid.uuid4())

        history_text = self._memory.get_history_text(session_id)
        previous_query = self._memory.get_previous_query(session_id)

        retrieved = await self._retriever.retrieve(
            query=query,
            conversation_context=previous_query,
        )

        logger.info(
            "RAG pipeline: retrieval done",
            session_id=session_id,
            query_id=query_id,
            chunks_retrieved=len(retrieved),
        )

        answer = await self._generator.generate(
            query=query,
            retrieved_chunks=retrieved,
            history_text=history_text,
        )

        self._memory.add_user_turn(session_id, query)
        self._memory.add_assistant_turn(session_id, answer)

        sources = _build_sources(retrieved)

        logger.info(
            "RAG pipeline: complete",
            session_id=session_id,
            query_id=query_id,
            sources_count=len(sources),
        )

        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=session_id,
            query_id=query_id,
        )


_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
