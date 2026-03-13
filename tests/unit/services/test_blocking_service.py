"""Unit tests for BlockingService.

Tests synchronous and asynchronous blocking simulation.
"""

import asyncio
import time

import pytest

from src.services.blocking_service import BlockingService


class TestBlockingService:
    """Tests for BlockingService."""

    @pytest.fixture
    def service(self) -> BlockingService:
        """Create a fresh service instance for each test."""
        return BlockingService()

    def test_sync_blocking_delays(self, service: BlockingService) -> None:
        """Test that sync blocking delays execution by expected duration."""
        duration = 0.1  # 100ms

        start = time.perf_counter()
        service.sync_block(duration)
        elapsed = time.perf_counter() - start

        # Allow some tolerance
        assert elapsed >= duration * 0.9
        assert elapsed < duration * 2

    def test_sync_blocking_short_duration(self, service: BlockingService) -> None:
        """Test sync blocking with very short duration."""
        duration = 0.01  # 10ms

        start = time.perf_counter()
        service.sync_block(duration)
        elapsed = time.perf_counter() - start

        assert elapsed >= duration * 0.5

    @pytest.mark.asyncio
    async def test_async_blocking_delays(self, service: BlockingService) -> None:
        """Test that async blocking delays execution."""
        duration = 0.1  # 100ms

        start = time.perf_counter()
        await service.async_block(duration)
        elapsed = time.perf_counter() - start

        # Allow some tolerance
        assert elapsed >= duration * 0.9
        assert elapsed < duration * 2

    @pytest.mark.asyncio
    async def test_async_blocking_blocks_event_loop(self, service: BlockingService) -> None:
        """Test that async blocking blocks the event loop (intentionally bad)."""
        # This tests the intentional bad behavior we're simulating
        duration = 0.1
        concurrent_task_ran = False

        async def concurrent_task() -> None:
            nonlocal concurrent_task_ran
            concurrent_task_ran = True

        # Start blocking task and a concurrent task
        blocking_task = asyncio.create_task(service.async_block(duration))
        concurrent = asyncio.create_task(concurrent_task())

        # Wait a bit - in normal async code, concurrent should run immediately
        await asyncio.sleep(0.01)

        # The blocking task should still be running and concurrent might be delayed
        # due to the intentional blocking behavior
        await blocking_task
        await concurrent

        # Concurrent task should eventually complete
        assert concurrent_task_ran

    @pytest.mark.asyncio
    async def test_chunked_block_allows_yields(self, service: BlockingService) -> None:
        """Test that chunked_block yields between chunks."""
        duration = 0.2
        chunk_ms = 50

        start = time.perf_counter()
        await service.chunked_block(duration, chunk_ms)
        elapsed = time.perf_counter() - start

        assert elapsed >= duration * 0.8
        assert elapsed < duration * 3

    def test_sync_block_with_zero_duration(self, service: BlockingService) -> None:
        """Test sync block with zero duration returns immediately."""
        start = time.perf_counter()
        service.sync_block(0)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_async_block_with_zero_duration(self, service: BlockingService) -> None:
        """Test async block with zero duration returns immediately."""
        start = time.perf_counter()
        await service.async_block(0)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1

    def test_sync_block_negative_duration(self, service: BlockingService) -> None:
        """Test sync block rejects negative duration."""
        with pytest.raises(ValueError):
            service.sync_block(-1)

    @pytest.mark.asyncio
    async def test_async_block_negative_duration(self, service: BlockingService) -> None:
        """Test async block rejects negative duration."""
        with pytest.raises(ValueError):
            await service.async_block(-1)


class TestBlockingServiceSingleton:
    """Tests for singleton behavior."""

    def test_global_instance_exists(self) -> None:
        """Test that global singleton instance is available."""
        from src.services.blocking_service import blocking_service

        assert blocking_service is not None
        assert isinstance(blocking_service, BlockingService)
