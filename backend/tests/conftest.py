"""
Pytest Configuration and Fixtures
Shared test fixtures and configuration for backend tests.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def async_client() -> AsyncClient:
    """
    Async HTTP client for testing FastAPI endpoints.

    Yields:
        AsyncClient: Configured test client
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
