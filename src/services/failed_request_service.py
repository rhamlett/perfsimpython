"""Failed request simulation service.

Generates HTTP 500 errors by calling the load test endpoint with
error injection configured for guaranteed failure.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from src.models.entities import SimulationState, SimulationType
from src.services.event_log_service import event_log_service
from src.services.simulation_tracker import simulation_tracker

logger = logging.getLogger(__name__)


@dataclass
class FailedRequestStatus:
    """Status of the failed request generator."""

    is_running: bool
    requests_sent: int
    requests_completed: int
    requests_in_progress: int
    target_count: int
    started_at: datetime | None = None


@dataclass
class FailedRequestResult:
    """Result of starting/stopping failed request simulation."""

    simulation_id: UUID
    status: str
    message: str
    requests_sent: int = 0
    requests_completed: int = 0


# Load test parameters tuned for guaranteed failure with visible latency
# Parameter names use camelCase to match .NET version API
FAILURE_REQUEST_BODY = {
    # Enough delay to exceed errorAfter and appear in latency monitor
    "baselineDelayMs": 1500,
    # Some CPU work so request is visible in metrics
    "workIterations": 500,
    # Small memory allocation
    "bufferSizeKb": 100,
    # High soft limit to avoid degradation delays
    "softLimit": 10000,
    # No additional degradation
    "degradationFactor": 0,
    # Error check starts after 1 second
    "errorAfter": 1,
    # 100% guaranteed failure
    "errorPercent": 100,
}


class FailedRequestService:
    """Service that generates failed HTTP requests for AppLens/App Insights testing.

    Makes HTTP requests to the load test endpoint with parameters configured
    for guaranteed failure (100% error probability). Each request takes ~1.5
    seconds before throwing a random exception, resulting in an HTTP 500.
    """

    def __init__(self) -> None:
        """Initialize the failed request service."""
        self._generator_task: asyncio.Task | None = None
        self._is_running = False
        self._requests_sent = 0
        self._requests_completed = 0
        self._requests_in_progress = 0
        self._target_count = 0
        self._started_at: datetime | None = None
        self._simulation_id: UUID | None = None

    @property
    def is_running(self) -> bool:
        """Check if the generator is currently running."""
        return self._is_running

    def start(self, request_count: int) -> FailedRequestResult:
        """Start generating failed HTTP requests.

        Args:
            request_count: Number of failed requests to generate.

        Returns:
            Result with simulation ID and status.
        """
        if self._is_running:
            return FailedRequestResult(
                simulation_id=self._simulation_id or uuid4(),
                status="AlreadyRunning",
                message="Failed request simulation is already running. Stop it first.",
            )

        self._simulation_id = uuid4()
        self._requests_sent = 0
        self._requests_completed = 0
        self._requests_in_progress = 0
        self._target_count = max(1, request_count)
        self._started_at = datetime.now(UTC)
        self._is_running = True

        # Track as simulation for dashboard visibility
        simulation = SimulationState(
            id=self._simulation_id,
            type=SimulationType.FAILED_REQUEST,
            duration_seconds=float(self._target_count * 2),  # ~2s per request
            params={
                "target_count": self._target_count,
            },
        )
        simulation_tracker.add(simulation)

        # Start the generator task
        self._generator_task = asyncio.create_task(
            self._run_generator(),
            name=f"FailedRequestGenerator-{self._simulation_id}",
        )

        logger.warning(
            "❌ Failed request simulation started: %s. Generating %d failures",
            self._simulation_id,
            self._target_count,
        )

        event_log_service.log_event(
            event_type="failedrequests",
            message=f"Started generating {self._target_count} failures",
            metadata={
                "simulation_id": str(self._simulation_id),
                "target_count": self._target_count,
            },
        )

        return FailedRequestResult(
            simulation_id=self._simulation_id,
            status="Started",
            message=(
                f"Generating {self._target_count} failed requests. "
                "These will appear in AppLens and Application Insights. "
                "Each request takes ~1.5 seconds before failing with a random error."
            ),
        )

    def stop(self) -> FailedRequestResult:
        """Stop the failed request simulation.

        Returns:
            Result with final counts.
        """
        if not self._is_running:
            return FailedRequestResult(
                simulation_id=uuid4(),
                status="NotRunning",
                message="No failed request simulation is running.",
            )

        self._is_running = False

        if self._generator_task:
            self._generator_task.cancel()
            self._generator_task = None

        # Remove from simulation tracker
        if self._simulation_id:
            simulation_tracker.remove(self._simulation_id)

        logger.info(
            "🛑 Failed request simulation stopped: %s. Sent=%d, Completed=%d",
            self._simulation_id,
            self._requests_sent,
            self._requests_completed,
        )

        event_log_service.log_event(
            event_type="failed_requests_stopped",
            message=f"Stopped after {self._requests_completed} failed requests",
            metadata={
                "requests_sent": self._requests_sent,
                "requests_completed": self._requests_completed,
            },
        )

        return FailedRequestResult(
            simulation_id=self._simulation_id or uuid4(),
            status="Stopped",
            message=f"Stopped. Sent: {self._requests_sent}, Completed: {self._requests_completed}",
            requests_sent=self._requests_sent,
            requests_completed=self._requests_completed,
        )

    def get_status(self) -> FailedRequestStatus:
        """Get current status of the failed request generator."""
        return FailedRequestStatus(
            is_running=self._is_running,
            requests_sent=self._requests_sent,
            requests_completed=self._requests_completed,
            requests_in_progress=self._requests_in_progress,
            target_count=self._target_count,
            started_at=self._started_at,
        )

    async def _run_generator(self) -> None:
        """Background task that generates failed HTTP requests.

        Makes HTTP POST requests to the load test endpoint with error
        injection parameters that guarantee failure.
        """
        try:
            # Create HTTP client with generous timeout (requests take ~1.5s)
            async with httpx.AsyncClient(timeout=30.0) as client:
                while self._requests_sent < self._target_count and self._is_running:
                    self._requests_sent += 1
                    self._requests_in_progress += 1
                    request_num = self._requests_sent

                    try:
                        # Time the request
                        request_start = time.perf_counter()

                        # Make request to load test endpoint - will fail with 500
                        response = await client.post(
                            "http://127.0.0.1:8000/api/loadtest",
                            json=FAILURE_REQUEST_BODY,
                        )

                        request_duration = time.perf_counter() - request_start

                        # This should NOT succeed (we expect 500)
                        if response.status_code == 200:
                            logger.warning(
                                "Failed request %d/%d unexpectedly succeeded",
                                request_num,
                                self._target_count,
                            )
                        else:
                            # Extract exception type from error response
                            exception_type = "Unknown"
                            try:
                                error_data = response.json()
                                error_detail = error_data.get("detail", "")
                                # Parse exception type from detail (format: "ExceptionType: message")
                                if ":" in error_detail:
                                    exception_type = error_detail.split(":")[0].strip()
                                elif error_detail:
                                    exception_type = error_detail
                            except Exception:
                                pass

                            logger.info(
                                "Failed request %d/%d: %s (%.2fs)",
                                request_num,
                                self._target_count,
                                exception_type,
                                request_duration,
                            )

                            # Format message like .NET version: "Failed Request: ExceptionType (1.57s)"
                            event_log_service.log_event(
                                event_type="failedrequests",
                                message=f"Failed Request: {exception_type} ({request_duration:.2f}s)",
                                metadata={
                                    "request_num": request_num,
                                    "exception_type": exception_type,
                                    "duration_seconds": round(request_duration, 2),
                                    "status_code": response.status_code,
                                },
                            )

                    except httpx.RequestError as e:
                        request_duration = time.perf_counter() - request_start
                        exception_type = type(e).__name__

                        logger.info(
                            "Failed request %d/%d: %s (%.2fs)",
                            request_num,
                            self._target_count,
                            exception_type,
                            request_duration,
                        )

                        event_log_service.log_event(
                            event_type="failedrequests",
                            message=f"Failed Request: {exception_type} ({request_duration:.2f}s)",
                            metadata={
                                "request_num": request_num,
                                "exception_type": exception_type,
                                "duration_seconds": round(request_duration, 2),
                            },
                        )

                    finally:
                        self._requests_completed += 1
                        self._requests_in_progress -= 1

                    # Small delay between requests to spread them out
                    if self._requests_sent < self._target_count and self._is_running:
                        await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Failed request generator cancelled")
        finally:
            self._is_running = False
            # Remove from simulation tracker
            if self._simulation_id:
                simulation_tracker.remove(self._simulation_id)
                self._simulation_id = None

            event_log_service.log_event(
                event_type="failed_requests_completed",
                message=f"Failed request generation complete: {self._requests_completed} requests",
                metadata={
                    "requests_completed": self._requests_completed,
                    "target_count": self._target_count,
                },
            )


# Global singleton instance
failed_request_service = FailedRequestService()
