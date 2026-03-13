"""Pytest fixtures and configuration for Performance Problem Simulator tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.app import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def app():
    """Create a fresh FastAPI application instance for each test."""
    return create_app()


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """Create a synchronous test client for the application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an asynchronous test client for the application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def mock_settings(monkeypatch):
    """Fixture to modify application settings for testing."""

    def _mock_settings(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key.upper(), str(value))

    return _mock_settings
