"""Integration tests for Memory Pressure API endpoints.

Tests POST /api/memory/allocate, /api/memory/release, and /api/memory/release-all.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMemoryAllocateAPI:
    """Tests for POST /api/memory/allocate endpoint."""

    async def test_allocate_memory(self, async_client: AsyncClient) -> None:
        """Test successful memory allocation."""
        response = await async_client.post("/api/memory/allocate", json={"size_mb": 50})

        assert response.status_code == 200
        data = response.json()

        assert "block_id" in data
        assert data["size_mb"] == 50
        assert data["message"] == "Memory allocated"

        # Cleanup
        await async_client.post("/api/memory/release-all")

    async def test_allocate_memory_query_param(self, async_client: AsyncClient) -> None:
        """Test allocation with query parameter."""
        response = await async_client.post("/api/memory/allocate?size_mb=100")

        assert response.status_code == 200
        data = response.json()
        assert data["size_mb"] == 100

        # Cleanup
        await async_client.post("/api/memory/release-all")

    async def test_allocate_multiple_blocks(self, async_client: AsyncClient) -> None:
        """Test allocating multiple memory blocks stacks."""
        # Allocate first block
        response1 = await async_client.post("/api/memory/allocate", json={"size_mb": 100})
        assert response1.status_code == 200
        block1_id = response1.json()["block_id"]

        # Allocate second block
        response2 = await async_client.post("/api/memory/allocate", json={"size_mb": 200})
        assert response2.status_code == 200
        block2_id = response2.json()["block_id"]

        # Both blocks should exist
        assert block1_id != block2_id

        # Cleanup
        await async_client.post("/api/memory/release-all")

    async def test_allocate_negative_size_returns_error(self, async_client: AsyncClient) -> None:
        """Test that negative size returns validation error."""
        response = await async_client.post("/api/memory/allocate", json={"size_mb": -50})

        assert response.status_code == 400 or response.status_code == 422

    async def test_allocate_zero_size_returns_error(self, async_client: AsyncClient) -> None:
        """Test that zero size returns validation error."""
        response = await async_client.post("/api/memory/allocate", json={"size_mb": 0})

        assert response.status_code == 400 or response.status_code == 422


@pytest.mark.asyncio
class TestMemoryReleaseAPI:
    """Tests for POST /api/memory/release endpoint."""

    async def test_release_memory(self, async_client: AsyncClient) -> None:
        """Test releasing a specific memory block."""
        # First allocate
        alloc_response = await async_client.post("/api/memory/allocate", json={"size_mb": 100})
        block_id = alloc_response.json()["block_id"]

        # Then release
        response = await async_client.post("/api/memory/release", json={"block_id": block_id})

        assert response.status_code == 200
        data = response.json()
        assert data["released"] is True
        assert data["block_id"] == block_id

    async def test_release_nonexistent_block(self, async_client: AsyncClient) -> None:
        """Test releasing a block that doesn't exist."""
        from uuid import uuid4

        response = await async_client.post("/api/memory/release", json={"block_id": str(uuid4())})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_release_invalid_uuid(self, async_client: AsyncClient) -> None:
        """Test releasing with invalid UUID format."""
        response = await async_client.post(
            "/api/memory/release", json={"block_id": "not-a-valid-uuid"}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestMemoryReleaseAllAPI:
    """Tests for POST /api/memory/release-all endpoint."""

    async def test_release_all_memory(self, async_client: AsyncClient) -> None:
        """Test releasing all memory blocks."""
        # Allocate multiple blocks
        await async_client.post("/api/memory/allocate", json={"size_mb": 50})
        await async_client.post("/api/memory/allocate", json={"size_mb": 100})
        await async_client.post("/api/memory/allocate", json={"size_mb": 75})

        # Release all
        response = await async_client.post("/api/memory/release-all")

        assert response.status_code == 200
        data = response.json()
        assert data["released_count"] == 3
        assert data["message"] == "All memory released"

    async def test_release_all_when_empty(self, async_client: AsyncClient) -> None:
        """Test release-all when no blocks exist."""
        # Ensure empty state
        await async_client.post("/api/memory/release-all")

        response = await async_client.post("/api/memory/release-all")

        assert response.status_code == 200
        data = response.json()
        assert data["released_count"] == 0


@pytest.mark.asyncio
class TestMemoryStatusAPI:
    """Tests for GET /api/memory/status endpoint."""

    async def test_get_memory_status(self, async_client: AsyncClient) -> None:
        """Test getting current memory allocation status."""
        # Allocate some memory
        await async_client.post("/api/memory/allocate", json={"size_mb": 100})
        await async_client.post("/api/memory/allocate", json={"size_mb": 200})

        response = await async_client.get("/api/memory/status")

        assert response.status_code == 200
        data = response.json()

        assert "total_allocated_mb" in data
        assert data["total_allocated_mb"] == 300
        assert "block_count" in data
        assert data["block_count"] == 2
        assert "blocks" in data

        # Cleanup
        await async_client.post("/api/memory/release-all")

    async def test_get_memory_status_empty(self, async_client: AsyncClient) -> None:
        """Test getting status when no memory allocated."""
        # Ensure empty state
        await async_client.post("/api/memory/release-all")

        response = await async_client.get("/api/memory/status")

        assert response.status_code == 200
        data = response.json()

        assert data["total_allocated_mb"] == 0
        assert data["block_count"] == 0
        assert data["blocks"] == []
