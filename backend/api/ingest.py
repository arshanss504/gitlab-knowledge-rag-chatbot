import asyncio

from fastapi import APIRouter, status

from backend.core.config import CRAWL_SOURCE_URLS
from backend.core.logging import get_logger
from backend.models.schemas import IngestRequest, IngestResponse
from backend.services.ingest import get_ingest_pipeline

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger data ingestion (async background task)",
)
async def trigger_ingest(request: IngestRequest) -> IngestResponse:
    source_urls = request.source_urls or CRAWL_SOURCE_URLS

    logger.info("Ingest triggered", source_urls=source_urls, force=request.force_reingest)

    pipeline = get_ingest_pipeline()
    asyncio.create_task(pipeline.run(source_urls, request.force_reingest))

    return IngestResponse(
        message="Ingestion started in background.",
        pages_queued=len(source_urls),
    )
