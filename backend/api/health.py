from fastapi import APIRouter

from backend.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health", summary="System health check")
async def health_check() -> dict:
    components = {}
    overall = "ok"

    try:
        from backend.db.chroma import get_chroma_store

        store = get_chroma_store()
        info = store.collection_info()
        components["chroma"] = {"status": "ok", "doc_count": info["count"]}
    except Exception as e:
        components["chroma"] = {"status": "down", "error": str(e)}
        overall = "down"

    try:
        from backend.core.config import get_settings

        cfg = get_settings()
        has_key = bool(cfg.gemini_api_key and cfg.gemini_api_key != "your_gemini_api_key_here")
        components["gemini"] = {
            "status": "ok" if has_key else "degraded",
            "model": cfg.gemini_chat_model,
        }
        if not has_key:
            overall = "degraded"
    except Exception as e:
        components["gemini"] = {"status": "down", "error": str(e)}
        overall = "down"

    return {"status": overall, "components": components}
