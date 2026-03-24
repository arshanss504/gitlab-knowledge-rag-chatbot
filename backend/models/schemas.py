"""
app/models/schemas.py
Pydantic v2 request/response models for all API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    session_id: str = Field(
        ...,
        min_length=4,
        max_length=128,
        description="Unique session identifier for conversation memory",
    )


class Source(BaseModel):
    title: str
    url: str
    section: Optional[str] = None
    relevance_score: float = Field(ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source] = []
    session_id: str
    query_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    source_urls: Optional[List[str]] = Field(
        None, description="Override default source URLs. Uses config defaults if empty."
    )
    force_reingest: bool = Field(
        False,
        description="Re-ingest all pages even if content hash matches.",
    )


class IngestResponse(BaseModel):
    message: str
    pages_queued: int = 0
