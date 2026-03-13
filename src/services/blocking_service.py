"""Blocking simulation service.

Provides methods to simulate synchronous and asynchronous blocking
to demonstrate thread pool starvation and event loop blocking.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for sync blocking operations
_thread_pool = ThreadPoolExecutor(max_workers=4)


class BlockingService:
    """Service for simulating blocking operations.

    Provides methods to demonstrate different types of blocking:
    - sync_block: Synchronous blocking using time.sleep (blocks thread pool)
    - async_block: Async blocking using time.sleep (blocks event loop - BAD!)
    - chunked_block: Blocking in chunks with yields for dashboard updates

    These methods intentionally demonstrate anti-patterns for educational purposes.
    """

    def sync_block(self, duration_seconds: float) -> float:
        """Block synchronously using time.sleep.

        This simulates synchronous I/O or CPU work that blocks the thread.
        When all thread pool workers are blocked, new requests queue up.

        Args:
            duration_seconds: How long to block in seconds.

        Returns:
            The actual duration blocked.

        Raises:
            ValueError: If duration is negative.
        """
        if duration_seconds < 0:
            raise ValueError("Duration cannot be negative")

        if duration_seconds == 0:
            return 0

        start = time.perf_counter()
        time.sleep(duration_seconds)
        actual = time.perf_counter() - start

        logger.debug("Sync blocked for %.3f seconds", actual)
        return actual

    async def async_block(self, duration_seconds: float) -> float:
        """Block asynchronously using time.sleep (INTENTIONALLY BAD!).

        This demonstrates the anti-pattern of using blocking calls
        in async code. The event loop is blocked, preventing ALL
        concurrent async operations from making progress.

        In real code, you should use asyncio.sleep() instead.

        Args:
            duration_seconds: How long to block in seconds.

        Returns:
            The actual duration blocked.

        Raises:
            ValueError: If duration is negative.
        """
        if duration_seconds < 0:
            raise ValueError("Duration cannot be negative")

        if duration_seconds == 0:
            return 0

        start = time.perf_counter()
        # INTENTIONALLY BAD: Using time.sleep in async context blocks the event loop
        time.sleep(duration_seconds)
        actual = time.perf_counter() - start

        logger.warning("Async blocked for %.3f seconds (THIS IS BAD!)", actual)
        return actual

    async def chunked_block(
        self,
        duration_seconds: float,
        chunk_ms: int = 100,
    ) -> float:
        """Block in chunks, yielding between chunks.

        This allows the dashboard to receive updates during the blocking.
        It's still an anti-pattern (blocking in async), but demonstrates
        a slightly better approach by yielding periodically.

        Args:
            duration_seconds: Total time to block in seconds.
            chunk_ms: Size of each blocking chunk in milliseconds.

        Returns:
            The actual duration blocked.

        Raises:
            ValueError: If duration is negative or chunk_ms is not positive.
        """
        if duration_seconds < 0:
            raise ValueError("Duration cannot be negative")
        if chunk_ms <= 0:
            raise ValueError("Chunk size must be positive")

        if duration_seconds == 0:
            return 0

        chunk_seconds = chunk_ms / 1000.0
        remaining = duration_seconds
        start = time.perf_counter()

        while remaining > 0:
            # Block for one chunk
            sleep_time = min(chunk_seconds, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

            # Yield to let other tasks run
            await asyncio.sleep(0)

        actual = time.perf_counter() - start
        logger.debug("Chunked blocked for %.3f seconds", actual)
        return actual

    async def run_sync_in_thread(self, duration_seconds: float) -> float:
        """Run sync blocking in a thread pool (proper async pattern).

        This demonstrates the correct way to handle blocking operations
        in async code - offload to a thread pool.

        Args:
            duration_seconds: How long to block in seconds.

        Returns:
            The actual duration blocked.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _thread_pool,
            self.sync_block,
            duration_seconds,
        )


# Global singleton instance
blocking_service = BlockingService()
