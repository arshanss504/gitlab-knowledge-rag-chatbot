"""
tests/test_api.py
Integration tests for FastAPI endpoints using TestClient.
Uses mocking to avoid real ChromaDB/Gemini calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_rag_pipeline():
    """Mock RAG pipeline that returns a canned response."""
    from backend.models.schemas import ChatResponse, Source
    from datetime import datetime

    mock = MagicMock()
    mock.run = AsyncMock(
        return_value=ChatResponse(
            answer="GitLab has six core values [Source 1].",
            sources=[
                Source(
                    title="GitLab Values",
                    url="https://handbook.gitlab.com/values",
                    section="Core Values",
                    relevance_score=0.92,
                )
            ],
            session_id="test-session",
            query_id="test-query-id",
            timestamp=datetime.utcnow(),
        )
    )
    return mock


@pytest.fixture
def client(mock_rag_pipeline):
    """TestClient with mocked services."""
    with patch("app.services.rag.get_rag_pipeline", return_value=mock_rag_pipeline), \
         patch("app.db.chroma.get_chroma_store") as mock_store, \
         patch("app.services.embedder.get_embedder"):

        mock_store.return_value.count.return_value = 1234
        mock_store.return_value.collection_info.return_value = {
            "name": "gitlab_handbook",
            "count": 1234,
            "metadata": {},
        }

        from main import app
        with TestClient(app) as c:
            yield c


class TestChatEndpoint:
    def test_chat_success(self, client, mock_rag_pipeline):
        response = client.post("/chat", json={
            "query": "What are GitLab's core values?",
            "session_id": "test-session-123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "query_id" in data
        assert "session_id" in data

    def test_chat_empty_query_rejected(self, client):
        response = client.post("/chat", json={
            "query": "",
            "session_id": "test-session-123",
        })
        assert response.status_code == 422

    def test_chat_missing_session_id_rejected(self, client):
        response = client.post("/chat", json={"query": "What is GitLab?"})
        assert response.status_code == 422

    def test_chat_sources_have_required_fields(self, client):
        response = client.post("/chat", json={
            "query": "Tell me about GitLab values",
            "session_id": "sess-abc",
        })
        data = response.json()
        for source in data["sources"]:
            assert "title" in source
            assert "url" in source
            assert "relevance_score" in source


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_components(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "components" in data
        assert "chroma" in data["components"]

    def test_health_chroma_shows_doc_count(self, client):
        data = client.get("/health").json()
        assert data["components"]["chroma"]["doc_count"] == 1234


class TestIngestEndpoint:
    def test_ingest_returns_202(self, client):
        with patch("app.services.ingest.get_ingest_pipeline") as mock_pipe:
            mock_pipe.return_value.run = AsyncMock()
            response = client.post("/ingest", json={})
            assert response.status_code == 202
            data = response.json()
            assert "message" in data
