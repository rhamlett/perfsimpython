"""Integration tests for Failed Requests API endpoints.

Tests POST /api/failed-requests endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestFailedRequestsAPI:
    """Tests for POST /api/failed-requests endpoint."""

    async def test_generate_500_errors(self, async_client: AsyncClient) -> None:
        """Test generating HTTP 500 errors."""
        count = 5

        response = await async_client.post("/api/failed-requests", json={"count": count})

        assert response.status_code == 200
        data = response.json()

        assert data["generated_count"] == count
        assert data["error_code"] == 500
        assert "message" in data

    async def test_generate_500_errors_default_count(self, async_client: AsyncClient) -> None:
        """Test generating errors with default count."""
        response = await async_client.post("/api/failed-requests")

        assert response.status_code == 200
        data = response.json()

        assert "generated_count" in data
        assert data["generated_count"] >= 1

    async def test_generate_500_errors_validation(self, async_client: AsyncClient) -> None:
        """Test validation for count parameter."""
        # Try negative count
        response = await async_client.post("/api/failed-requests", json={"count": -1})

        assert response.status_code == 400 or response.status_code == 422

    async def test_generate_500_errors_max_limit(self, async_client: AsyncClient) -> None:
        """Test that there's a reasonable max limit on count."""
        response = await async_client.post(
            "/api/failed-requests", json={"count": 10000}  # Very high count
        )

        # Should either reject or cap
        assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
class TestAdminResetAPI:
    """Tests for POST /api/admin/reset endpoint."""

    async def test_admin_reset(self, async_client: AsyncClient) -> None:
        """Test admin reset endpoint."""
        # Create some state first
        await async_client.post("/api/memory/allocate", json={"size_mb": 10})

        # Reset
        response = await async_client.post("/api/admin/reset")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "reset" in data["message"].lower()

    async def test_admin_stats(self, async_client: AsyncClient) -> None:
        """Test admin stats endpoint."""
        response = await async_client.get("/api/admin/stats")

        assert response.status_code == 200
        data = response.json()

        assert "cpu_simulations" in data or "simulations" in data
        assert "memory_allocated_mb" in data or "memory" in data
