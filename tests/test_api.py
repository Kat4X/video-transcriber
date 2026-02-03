"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from transcriber.main import app
from transcriber.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize database before each test."""
    await init_db()


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestTranscriptionsAPI:
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_transcriptions_empty(self, client):
        response = await client.get("/api/transcriptions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_create_transcription_no_input(self, client):
        response = await client.post("/api/transcriptions")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_transcription_not_found(self, client):
        response = await client.get("/api/transcriptions/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_transcription_not_found(self, client):
        response = await client.delete("/api/transcriptions/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_transcription_not_found(self, client):
        response = await client.get("/api/transcriptions/nonexistent-id/download")
        assert response.status_code == 404
