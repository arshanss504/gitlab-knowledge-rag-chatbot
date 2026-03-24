from fastapi import APIRouter, HTTPException, status

from backend.core.logging import get_logger
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.rag import get_rag_pipeline

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message and get a RAG-grounded answer",
)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info("Chat request received", session_id=request.session_id)

    try:
        pipeline = get_rag_pipeline()
        return await pipeline.run(query=request.query, session_id=request.session_id)
    except Exception as exc:
        logger.error("Chat pipeline error", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your question. Please try again.",
        )
