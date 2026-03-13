"""Unit tests for SlowRequestService.

Tests slow response delays and generator functionality.
"""

import asyncio
import time

import pytest

from src.services.slow_request_service import SlowRequestService


class TestSlowRequestService:
    """Tests for SlowRequestService."""

    @pytest.fixture
    def service(self) -> SlowRequestService:
        """Create a fresh service instance for each test."""
        svc = SlowRequestService()
        yield svc
        # Cleanup
        svc.stop_slow_generator()

    @pytest.mark.asyncio
    async def test_slow_response_delays_correctly(self, service: SlowRequestService) -> None:
        """Test that slow_response delays by the specified duration."""
        delay = 0.2  # 200ms

        start = time.perf_counter()
        await service.slow_response(delay)
        elapsed = time.perf_counter() - start

        # Allow tolerance for timing
        assert elapsed >= delay * 0.9
        assert elapsed < delay * 2

    @pytest.mark.asyncio
    async def test_slow_response_zero_delay(self, service: SlowRequestService) -> None:
        """Test slow_response with zero delay returns quickly."""
        start = time.perf_counter()
        await service.slow_response(0)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_slow_response_negative_delay_raises(self, service: SlowRequestService) -> None:
        """Test slow_response rejects negative delay."""
        with pytest.raises(ValueError):
            await service.slow_response(-1)

    @pytest.mark.asyncio
    async def test_slow_response_is_non_blocking(self, service: SlowRequestService) -> None:
        """Test that slow_response uses asyncio.sleep (non-blocking)."""
        # Start multiple slow responses concurrently
        start = time.perf_counter()

        await asyncio.gather(
            service.slow_response(0.1),
            service.slow_response(0.1),
            service.slow_response(0.1),
        )

        elapsed = time.perf_counter() - start

        # All should complete in about 0.1s if truly non-blocking
        # rather than 0.3s if blocking
        assert elapsed < 0.2

    @pytest.mark.asyncio
    async def test_slow_generator_starts(self, service: SlowRequestService) -> None:
        """Test that slow generator can be started."""
        result = await service.start_slow_generator(
            interval_seconds=0.1,
            max_requests=5,
            delay_seconds=0.05,
        )

        assert result is True
        assert service.is_generator_running

    @pytest.mark.asyncio
    async def test_slow_generator_stops(self, service: SlowRequestService) -> None:
        """Test that slow generator can be stopped."""
        await service.start_slow_generator(
            interval_seconds=0.1,
            max_requests=100,
            delay_seconds=0.05,
        )

        service.stop_slow_generator()

        # Give time for cleanup
        await asyncio.sleep(0.1)
        assert not service.is_generator_running

    @pytest.mark.asyncio
    async def test_slow_generator_completes_after_max_requests(
        self, service: SlowRequestService
    ) -> None:
        """Test generator stops after max_requests."""
        max_requests = 3
        interval = 0.05

        await service.start_slow_generator(
            interval_seconds=interval,
            max_requests=max_requests,
            delay_seconds=0.01,
        )

        # Wait for generator to complete
        await asyncio.sleep(max_requests * interval * 2)

        # Generator should have stopped after max requests
        # Give a bit more time for cleanup
        await asyncio.sleep(0.1)

        assert service.generated_count >= max_requests

    @pytest.mark.asyncio
    async def test_cannot_start_generator_twice(self, service: SlowRequestService) -> None:
        """Test that starting generator while running raises error."""
        await service.start_slow_generator(
            interval_seconds=1,
            max_requests=10,
            delay_seconds=0.1,
        )

        with pytest.raises(RuntimeError):
            await service.start_slow_generator(
                interval_seconds=0.5,
                max_requests=5,
                delay_seconds=0.1,
            )

    @pytest.mark.asyncio
    async def test_get_stats(self, service: SlowRequestService) -> None:
        """Test getting generator stats."""
        stats = service.get_stats()

        assert "is_running" in stats
        assert "generated_count" in stats
        assert "max_requests" in stats


class TestSlowRequestServiceSingleton:
    """Tests for singleton behavior."""

    def test_global_instance_exists(self) -> None:
        """Test that global singleton instance is available."""
        from src.services.slow_request_service import slow_request_service

        assert slow_request_service is not None
        assert isinstance(slow_request_service, SlowRequestService)
