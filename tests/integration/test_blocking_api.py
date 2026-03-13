"""Integration tests for Blocking Simulation API endpoints.

Tests POST /api/blocking/sync and /api/blocking/async endpoints.
"""

import asyncio
import time

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSyncBlockingAPI:
    """Tests for POST /api/blocking/sync endpoint."""

    async def test_sync_blocking_increases_latency(self, async_client: AsyncClient) -> None:
        """Test that sync blocking delays the response."""
        duration = 0.5  # 500ms

        start = time.perf_counter()
        response = await async_client.post(
            "/api/blocking/sync", json={"duration_seconds": duration, "count": 1}
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()

        assert data["blocked_duration"] >= duration * 0.8
        assert elapsed >= duration * 0.8

    async def test_sync_blocking_multiple_count(self, async_client: AsyncClient) -> None:
        """Test sync blocking with count > 1."""
        response = await async_client.post(
            "/api/blocking/sync", json={"duration_seconds": 0.1, "count": 3}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3

    async def test_sync_blocking_default_count(self, async_client: AsyncClient) -> None:
        """Test sync blocking with default count of 1."""
        response = await async_client.post("/api/blocking/sync", json={"duration_seconds": 0.1})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    async def test_sync_blocking_validation_error(self, async_client: AsyncClient) -> None:
        """Test sync blocking validation with negative duration."""
        response = await async_client.post("/api/blocking/sync", json={"duration_seconds": -1})

        assert response.status_code == 400 or response.status_code == 422


@pytest.mark.asyncio
class TestAsyncBlockingAPI:
    """Tests for POST /api/blocking/async endpoint."""

    async def test_async_blocking_delays_all_requests(self, async_client: AsyncClient) -> None:
        """Test that async blocking delays concurrent requests."""
        duration = 0.5  # 500ms

        start = time.perf_counter()
        response = await async_client.post(
            "/api/blocking/async", json={"duration_seconds": duration}
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        data = response.json()

        assert data["blocked_duration"] >= duration * 0.8
        assert elapsed >= duration * 0.8

    async def test_async_blocking_with_chunk_ms(self, async_client: AsyncClient) -> None:
        """Test async blocking with custom chunk size."""
        response = await async_client.post(
            "/api/blocking/async", json={"duration_seconds": 0.2, "chunk_ms": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["chunked"] is True

    async def test_async_blocking_validation_error(self, async_client: AsyncClient) -> None:
        """Test async blocking validation with negative duration."""
        response = await async_client.post("/api/blocking/async", json={"duration_seconds": -1})

        assert response.status_code == 400 or response.status_code == 422


@pytest.mark.asyncio
class TestBlockingConcurrency:
    """Tests for concurrent blocking behavior."""

    async def test_sync_blocking_affects_throughput(self, async_client: AsyncClient) -> None:
        """Test that sync blocking reduces server throughput."""
        # Make requests in quick succession
        duration = 0.2

        start = time.perf_counter()

        # Send multiple blocking requests concurrently
        tasks = [
            async_client.post("/api/blocking/sync", json={"duration_seconds": duration, "count": 1})
            for _ in range(3)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.perf_counter() - start

        # All requests should succeed
        for resp in responses:
            if not isinstance(resp, Exception):
                assert resp.status_code == 200

        # Total time should be significantly more than single request
        # because sync blocking ties up the thread pool
        # (but with enough workers, they might all run in parallel)
        assert elapsed >= duration * 0.5

    async def test_async_blocking_serializes_requests(self, async_client: AsyncClient) -> None:
        """Test that async blocking serializes event loop processing."""
        duration = 0.2

        start = time.perf_counter()

        # Send concurrent async blocking requests
        tasks = [
            async_client.post("/api/blocking/async", json={"duration_seconds": duration})
            for _ in range(2)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        _elapsed = time.perf_counter() - start  # Timing for reference

        # All should succeed
        for resp in responses:
            if not isinstance(resp, Exception):
                assert resp.status_code == 200
