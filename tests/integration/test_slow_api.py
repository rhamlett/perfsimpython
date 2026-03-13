"""Integration tests for Slow Requests API endpoints.

Tests GET /api/slow and slow generator endpoints.
"""

import asyncio
import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSlowRequestAPI:
    """Tests for GET /api/slow endpoint."""

    async def test_slow_request_timing(self, async_client: AsyncClient) -> None:
        """Test slow request returns after specified delay."""
        delay = 0.5  # 500ms

        start = time.perf_counter()
        response = await async_client.get(f"/api/slow?delay_seconds={delay}")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()

        assert data["delay_seconds"] == delay
        assert elapsed >= delay * 0.9

    async def test_slow_request_default_delay(self, async_client: AsyncClient) -> None:
        """Test slow request with default delay."""
        response = await async_client.get("/api/slow")

        assert response.status_code == 200
        data = response.json()
        assert "delay_seconds" in data

    async def test_slow_request_validation(self, async_client: AsyncClient) -> None:
        """Test slow request validation for max delay."""
        # Try to set extremely long delay
        response = await async_client.get("/api/slow?delay_seconds=1000")

        # Should either reject or cap the delay
        assert response.status_code in [200, 400, 422]

    async def test_slow_request_is_non_blocking(self, async_client: AsyncClient) -> None:
        """Test that slow requests don't block other requests."""
        delay = 0.3

        # Start concurrent slow requests
        start = time.perf_counter()

        tasks = [async_client.get(f"/api/slow?delay_seconds={delay}") for _ in range(3)]

        responses = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Should complete in roughly the same time as one request
        # since they run concurrently (async sleep, not blocking)
        assert elapsed < delay * 2


@pytest.mark.asyncio
class TestSlowGeneratorAPI:
    """Tests for slow request generator endpoints."""

    async def test_slow_request_generator_start(self, async_client: AsyncClient) -> None:
        """Test starting the slow request generator."""
        response = await async_client.post(
            "/api/slow/start",
            json={
                "interval_seconds": 0.5,
                "max_requests": 3,
                "delay_seconds": 0.1,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["started"] is True

        # Stop generator
        await async_client.post("/api/slow/stop")

    async def test_slow_request_generator_stop(self, async_client: AsyncClient) -> None:
        """Test stopping the slow request generator."""
        # Start first
        await async_client.post(
            "/api/slow/start",
            json={
                "interval_seconds": 1,
                "max_requests": 100,
                "delay_seconds": 0.1,
            },
        )

        # Then stop
        response = await async_client.post("/api/slow/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["stopped"] is True

    async def test_slow_request_generator_status(self, async_client: AsyncClient) -> None:
        """Test getting generator status."""
        response = await async_client.get("/api/slow/status")

        assert response.status_code == 200
        data = response.json()

        assert "is_running" in data
        assert "generated_count" in data
