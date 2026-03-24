from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=4, max_length=128)


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


class IngestRequest(BaseModel):
    source_urls: Optional[List[str]] = None
    force_reingest: bool = False


class IngestResponse(BaseModel):
    message: str
    pages_queued: int = 0
