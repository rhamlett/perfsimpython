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

# Period length for stats reporting (seconds)
STATS_PERIOD_SECONDS = 60


# =============================================================================
# EXCEPTION POOL - Python exceptions to simulate realistic failures
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

        # Period stats tracking (resets every STATS_PERIOD_SECONDS)
        self._period_start_time = time.time()
        self._period_requests = 0
        self._period_errors = 0
        self._period_total_ms = 0
        self._period_max_ms = 0

    async def execute_work(self, request: LoadTestRequest) -> LoadTestResult:
        """Execute load test work with configurable parameters.

        This method simulates realistic application behavior:

        1. Allocates memory up front and holds it for the entire request
           duration.
        2. Calculates total request duration including degradation delay
           for concurrent requests over the soft limit.
        3. Runs a sustained work loop that interleaves CPU work
           (blocking — sync-over-async anti-pattern) with brief async
           sleeps for realistic behavior.
        4. Checks for error injection based on elapsed time.

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
        had_error = False

        try:
            buffer_size = request.buffer_size_kb * 1024
            buffer = bytearray(buffer_size)
            self._touch_memory_buffer(buffer)

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

            # Sustained work loop: interleave CPU work with brief async sleeps
            sleep_per_cycle_ms = 50
            cpu_work_ms_per_cycle = request.work_iterations // 100

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            while elapsed_ms < total_duration_ms:
                if cpu_work_ms_per_cycle > 0:
                    self._perform_cpu_work(cpu_work_ms_per_cycle)
                    total_cpu_work_done += cpu_work_ms_per_cycle

                self._touch_memory_buffer(buffer)

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
            had_error = True
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

                # Track period stats
                self._period_requests += 1
                self._period_total_ms += elapsed_final
                if elapsed_final > self._period_max_ms:
                    self._period_max_ms = elapsed_final
                if had_error:
                    self._period_errors += 1

                # Check if period has elapsed and emit stats
                self._check_and_emit_period_stats()

    def _touch_memory_buffer(self, buffer: bytearray) -> None:
        """Touch memory buffer to prevent GC optimization.

        Walks every 4096-byte page in the buffer and flips a byte,
        ensuring the OS has actually committed the pages.
        """
        checksum = 0
        for i in range(0, len(buffer), 4096):
            buffer[i] = buffer[i] ^ 0xFF
            checksum += buffer[i]

    def _check_and_emit_period_stats(self) -> None:
        """Check if stats period has elapsed and emit event log message.

        Should be called while holding self._lock.
        Emits stats like: "Load test period stats (60s): 437 requests, 4802.9 avg ms, 12100 max ms, 7.28 RPS, 31.1% errors"
        """
        now = time.time()
        elapsed = now - self._period_start_time

        if elapsed >= STATS_PERIOD_SECONDS and self._period_requests > 0:
            # Calculate stats
            avg_ms = self._period_total_ms / self._period_requests
            max_ms = self._period_max_ms
            rps = self._period_requests / elapsed
            error_pct = (self._period_errors / self._period_requests) * 100

            # Format message matching sister app format
            message = (
                f"Load test period stats ({STATS_PERIOD_SECONDS}s): "
                f"{self._period_requests} requests, "
                f"{avg_ms:.1f} avg ms, "
                f"{max_ms} max ms, "
                f"{rps:.2f} RPS, "
                f"{error_pct:.1f}% errors"
            )

            # Emit event log
            event_log_service.log_event(
                event_type="loadtest",
                message=message,
                metadata={
                    "requests": self._period_requests,
                    "avg_ms": round(avg_ms, 1),
                    "max_ms": max_ms,
                    "rps": round(rps, 2),
                    "error_percent": round(error_pct, 1),
                    "period_seconds": STATS_PERIOD_SECONDS,
                },
            )

            logger.info(message)

            # Reset period stats
            self._period_start_time = now
            self._period_requests = 0
            self._period_errors = 0
            self._period_total_ms = 0
            self._period_max_ms = 0

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
