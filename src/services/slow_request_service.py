"""Slow request simulation service.

Provides methods to simulate slow responses and generate slow requests
for observing application behavior under latency conditions.
"""

import asyncio
import logging

from src.services.event_log_service import event_log_service

logger = logging.getLogger(__name__)


class SlowRequestService:
    """Service for simulating slow responses.

    Provides methods to add artificial delays to responses and
    generate periodic slow requests for diagnostic practice.

    Attributes:
        _generator_task: The background task for generating slow requests.
        _is_running: Whether the generator is currently running.
        _generated_count: Total number of slow requests generated.
        _max_requests: Maximum requests for current generator run.
    """

    def __init__(self) -> None:
        """Initialize the slow request service."""
        self._generator_task: asyncio.Task | None = None
        self._is_running = False
        self._generated_count = 0
        self._max_requests = 0
        self._interval_seconds = 0.0
        self._delay_seconds = 0.0

    async def slow_response(self, delay_seconds: float) -> float:
        """Add artificial delay to a response.

        Uses asyncio.sleep for non-blocking delay, allowing other
        requests to be processed concurrently.

        Args:
            delay_seconds: How long to delay in seconds.

        Returns:
            The actual delay duration.

        Raises:
            ValueError: If delay is negative.
        """
        if delay_seconds < 0:
            raise ValueError("Delay cannot be negative")

        if delay_seconds == 0:
            return 0

        start = asyncio.get_event_loop().time()
        await asyncio.sleep(delay_seconds)
        actual = asyncio.get_event_loop().time() - start

        logger.debug("Slowed response by %.3f seconds", actual)
        return actual

    async def start_slow_generator(
        self,
        interval_seconds: float,
        max_requests: int,
        delay_seconds: float,
    ) -> bool:
        """Start generating periodic slow requests.

        Creates a background task that generates slow requests at the
        specified interval until max_requests is reached.

        Args:
            interval_seconds: Time between requests.
            max_requests: Maximum requests to generate.
            delay_seconds: Delay for each generated request.

        Returns:
            True if generator was started.

        Raises:
            RuntimeError: If generator is already running.
        """
        if self._is_running:
            raise RuntimeError("Slow request generator is already running")

        self._generated_count = 0
        self._max_requests = max_requests
        self._interval_seconds = interval_seconds
        self._delay_seconds = delay_seconds
        self._is_running = True

        self._generator_task = asyncio.create_task(
            self._run_generator(interval_seconds, max_requests, delay_seconds)
        )

        logger.info(
            "Started slow request generator: interval=%.2fs, max=%d, delay=%.2fs",
            interval_seconds,
            max_requests,
            delay_seconds,
        )

        event_log_service.log_event(
            event_type="slow_generator_started",
            message="Slow request generator started",
            metadata={
                "interval_seconds": interval_seconds,
                "max_requests": max_requests,
                "delay_seconds": delay_seconds,
            },
        )

        return True

    async def _run_generator(
        self,
        interval_seconds: float,
        max_requests: int,
        delay_seconds: float,
    ) -> None:
        """Background task for generating slow requests.

        Args:
            interval_seconds: Time between requests.
            max_requests: Maximum requests to generate.
            delay_seconds: Delay for each request.
        """
        try:
            while self._generated_count < max_requests and self._is_running:
                # Simulate a slow request
                await self.slow_response(delay_seconds)
                self._generated_count += 1

                logger.debug(
                    "Generated slow request %d/%d",
                    self._generated_count,
                    max_requests,
                )

                if self._generated_count < max_requests:
                    await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info("Slow request generator cancelled")
        finally:
            self._is_running = False
            event_log_service.log_event(
                event_type="slow_generator_stopped",
                message=f"Slow request generator stopped after {self._generated_count} requests",
                metadata={"generated_count": self._generated_count},
            )

    def stop_slow_generator(self) -> bool:
        """Stop the slow request generator.

        Returns:
            True if generator was stopped, False if not running.
        """
        if not self._is_running:
            return False

        self._is_running = False

        if self._generator_task:
            self._generator_task.cancel()
            self._generator_task = None

        logger.info(
            "Stopped slow request generator after %d requests",
            self._generated_count,
        )

        return True

    @property
    def is_generator_running(self) -> bool:
        """Check if the generator is currently running."""
        return self._is_running

    @property
    def generated_count(self) -> int:
        """Get the count of generated slow requests."""
        return self._generated_count

    def get_stats(self) -> dict:
        """Get generator statistics.

        Returns:
            Dictionary with generator stats.
        """
        return {
            "is_running": self._is_running,
            "generated_count": self._generated_count,
            "max_requests": self._max_requests,
            "interval_seconds": self._interval_seconds,
            "delay_seconds": self._delay_seconds,
        }


# Global singleton instance
slow_request_service = SlowRequestService()
