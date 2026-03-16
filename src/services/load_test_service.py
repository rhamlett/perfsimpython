"""Load test service with error injection capability.

Provides a load test endpoint that simulates realistic application behavior
under varying load conditions, including configurable error injection.
"""

import asyncio
import hashlib
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.services.event_log_service import event_log_service

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTION POOL - Random exceptions to simulate realistic failures
# =============================================================================

EXCEPTION_FACTORIES: list[Callable[[], Exception]] = [
    # Common application logic exceptions
    lambda: ValueError("Operation is not valid due to current state"),
    lambda: TypeError("Value does not fall within the expected range"),
    lambda: AttributeError("'NoneType' object has no attribute 'process'"),
    # Classic Python exceptions
    lambda: KeyError("The given key was not present in the dictionary"),
    lambda: IndexError("Index was outside the bounds of the list"),
    lambda: ZeroDivisionError("Attempted to divide by zero"),
    # I/O and network-related exceptions
    lambda: TimeoutError("The operation has timed out"),
    lambda: ConnectionError("Unable to read data from the transport connection"),
    lambda: OSError("An error occurred while processing the request"),
    # Format and overflow exceptions
    lambda: OverflowError("Arithmetic operation resulted in an overflow"),
    lambda: RuntimeError("An unexpected error occurred during processing"),
    # Resource exceptions
    lambda: MemoryError("Insufficient memory to continue execution"),
    lambda: RecursionError("Maximum recursion depth exceeded"),
]


@dataclass
class LoadTestRequest:
    """Request parameters for load test endpoint.

    All parameters have defaults, making the request body optional.
    Parameter names match .NET version for API compatibility.
    """

    work_iterations: int = 200
    """Number of SHA256 hash iterations for CPU work. 1000 ≈ 5-10ms."""

    buffer_size_kb: int = 20000
    """Size of memory buffer to allocate in kilobytes (20 MB default)."""

    soft_limit: int = 25
    """Concurrent requests before degradation delays begin."""

    degradation_factor: int = 500
    """Milliseconds of delay added per concurrent request over soft limit."""

    baseline_delay_ms: int = 500
    """Minimum blocking delay applied to every request in milliseconds."""

    error_after: int = 120
    """Seconds after which random errors may be thrown. 0 disables."""

    error_percent: int = 20
    """Probability (0-100) of throwing error after threshold."""


@dataclass
class LoadTestResult:
    """Result of a load test request."""

    elapsed_ms: int
    concurrent_requests_at_start: int
    degradation_delay_applied_ms: int
    work_iterations_completed: int
    memory_allocated_bytes: int
    work_completed: bool
    exception_thrown: bool
    exception_type: str | None
    exception_message: str | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class LoadTestService:
    """Service for simulating realistic application behavior under load.

    Provides a load test endpoint that:
    - Performs actual CPU work (SHA256 hashes)
    - Allocates real memory (held for request duration)
    - Degrades naturally under load (soft limit pattern)
    - Fails realistically after extended processing (random exceptions)
    """

    def __init__(self) -> None:
        """Initialize the load test service."""
        self._concurrent_requests = 0
        self._total_requests_processed = 0
        self._total_exceptions_thrown = 0
        self._total_response_time_ms = 0
        self._lock = asyncio.Lock()

    async def execute_work(self, request: LoadTestRequest) -> LoadTestResult:
        """Execute load test work with configurable parameters.

        This method simulates realistic application behavior:
        1. Allocates memory and holds it for the request duration
        2. Calculates degradation delay based on concurrent requests
        3. Performs CPU work in cycles with yields
        4. Checks for error injection based on elapsed time

        Args:
            request: Load test configuration parameters.

        Returns:
            LoadTestResult with timing and completion details.

        Raises:
            Random exception from pool if error conditions are met.
        """
        async with self._lock:
            self._concurrent_requests += 1
            current_concurrent = self._concurrent_requests

        start_time = time.perf_counter()
        total_cpu_work_done = 0
        buffer: bytearray | None = None

        try:
            # STEP 1: Allocate memory up front and hold for entire request
            buffer_size = request.buffer_size_kb * 1024
            buffer = bytearray(buffer_size)
            self._touch_memory_buffer(buffer)

            # STEP 2: Calculate total request duration
            over_limit = max(0, current_concurrent - request.soft_limit)
            degradation_delay_ms = over_limit * request.degradation_factor
            total_duration_ms = request.baseline_delay_ms + degradation_delay_ms

            logger.debug(
                "Load test: Concurrent=%d, Duration=%dms (base=%dms + degradation=%dms)",
                current_concurrent,
                total_duration_ms,
                request.baseline_delay_ms,
                degradation_delay_ms,
            )

            # STEP 3: Sustained work loop
            # Interleave CPU work with brief sleeps for realistic behavior
            sleep_per_cycle_ms = 50
            cpu_work_ms_per_cycle = request.work_iterations // 100

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            while elapsed_ms < total_duration_ms:
                # CPU work phase (blocking - sync-over-async anti-pattern)
                if cpu_work_ms_per_cycle > 0:
                    self._perform_cpu_work(cpu_work_ms_per_cycle)
                    total_cpu_work_done += cpu_work_ms_per_cycle

                # Keep memory active
                self._touch_memory_buffer(buffer)

                # Sleep phase (async yield to allow other work)
                remaining_ms = total_duration_ms - elapsed_ms
                sleep_ms = min(sleep_per_cycle_ms, max(0, remaining_ms))
                if sleep_ms > 0:
                    await asyncio.sleep(sleep_ms / 1000.0)

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # Check for error injection after work completes
            self._check_and_throw_error(
                start_time,
                request.error_after,
                request.error_percent,
            )

            # Final memory touch
            self._touch_memory_buffer(buffer)

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            return LoadTestResult(
                elapsed_ms=elapsed_ms,
                concurrent_requests_at_start=current_concurrent,
                degradation_delay_applied_ms=degradation_delay_ms,
                work_iterations_completed=total_cpu_work_done,
                memory_allocated_bytes=buffer_size,
                work_completed=True,
                exception_thrown=False,
                exception_type=None,
                exception_message=None,
            )

        except Exception as ex:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            async with self._lock:
                self._total_exceptions_thrown += 1

            logger.warning(
                "Load test exception after %dms: %s - %s",
                elapsed_ms,
                type(ex).__name__,
                str(ex),
            )
            raise

        finally:
            # Release memory and update counters
            del buffer
            elapsed_final = int((time.perf_counter() - start_time) * 1000)
            async with self._lock:
                self._concurrent_requests -= 1
                self._total_requests_processed += 1
                self._total_response_time_ms += elapsed_final

    def _touch_memory_buffer(self, buffer: bytearray) -> None:
        """Touch memory buffer to prevent GC optimization."""
        checksum = 0
        for i in range(0, len(buffer), 4096):  # Touch every page
            buffer[i] = buffer[i] ^ 0xFF
            checksum += buffer[i]

    def _perform_cpu_work(self, work_ms: int) -> None:
        """Perform CPU-intensive work for specified duration.

        Uses SHA256 hashing in a loop to simulate real CPU work.
        This is a blocking operation that will block the event loop.
        """
        if work_ms <= 0:
            return

        end_time = time.perf_counter() + (work_ms / 1000.0)
        data = b"initial"

        while time.perf_counter() < end_time:
            # SHA256 hash iterations - real CPU work
            data = hashlib.sha256(data).digest()

    def _check_and_throw_error(
        self,
        start_time: float,
        error_after: int,
        error_percent: int,
    ) -> None:
        """Check if error should be thrown based on elapsed time and probability.

        Args:
            start_time: Request start time (from time.perf_counter()).
            error_after: Seconds threshold. 0 disables errors.
            error_percent: Probability (0-100) of error.

        Raises:
            Random exception from pool if conditions are met.
        """
        if error_after <= 0 or error_percent <= 0:
            return

        elapsed_seconds = time.perf_counter() - start_time

        if elapsed_seconds > error_after:
            probability = error_percent / 100.0
            if random.random() < probability:
                # Pick and throw random exception
                exception_factory = random.choice(EXCEPTION_FACTORIES)
                exception = exception_factory()

                logger.info(
                    "Load test throwing random exception after %.1fs "
                    "(threshold: %ds, probability: %d%%): %s",
                    elapsed_seconds,
                    error_after,
                    error_percent,
                    type(exception).__name__,
                )

                # Log to event log for dashboard visibility
                event_log_service.log_event(
                    event_type="load_test_error",
                    message=f"Injected error: {type(exception).__name__}: {exception}",
                    metadata={
                        "exception_type": type(exception).__name__,
                        "exception_message": str(exception),
                        "elapsed_seconds": round(elapsed_seconds, 2),
                    },
                )

                raise exception

    def get_stats(self) -> dict:
        """Get current load test statistics with camelCase keys for API compatibility."""
        avg_response_time = (
            self._total_response_time_ms / self._total_requests_processed
            if self._total_requests_processed > 0
            else 0
        )
        return {
            "currentConcurrentRequests": self._concurrent_requests,
            "totalRequestsProcessed": self._total_requests_processed,
            "totalExceptionsThrown": self._total_exceptions_thrown,
            "averageResponseTimeMs": round(avg_response_time, 1),
        }


# Global singleton instance
load_test_service = LoadTestService()
