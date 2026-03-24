from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import chat, health, ingest
from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    logger.info("GitLab RAG starting up", chroma_dir=cfg.chroma_persist_dir)

    try:
        from backend.db.chroma import get_chroma_store

        store = get_chroma_store()
        logger.info("ChromaDB warmed up", doc_count=store.count())
    except Exception as e:
        logger.warning("ChromaDB warmup failed (may be empty on first run)", error=str(e))

    try:
        from backend.services.embedder import get_embedder

        get_embedder()
        logger.info("Embedding service warmed up")
    except Exception as e:
        logger.warning("Embedder warmup failed", error=str(e))

    try:
        from backend.services.memory import get_memory

        get_memory()
        logger.info("Conversation memory warmed up")
    except Exception as e:
        logger.warning("Memory warmup failed", error=str(e))

    logger.info("GitLab RAG ready to serve requests")
    yield
    logger.info("GitLab RAG shutting down")


def create_app() -> FastAPI:
    cfg = get_settings()
    configure_logging(cfg.log_level)

    app = FastAPI(
        title="GitLab RAG Chatbot API",
        description=(
            "Retrieval-Augmented Generation chatbot for GitLab Handbook and Direction pages. "
            "Ask questions about GitLab's culture, processes, and product strategy."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    raw_origins = (cfg.cors_origins or "").strip()
    if raw_origins:
        allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    else:
        allow_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again."},
        )

    app.include_router(chat.router, tags=["chat"])
    app.include_router(ingest.router, tags=["ingestion"])
    app.include_router(health.router, tags=["observability"])

    return app


app = create_app()
