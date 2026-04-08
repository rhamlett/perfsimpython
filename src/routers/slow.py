"""Slow request simulation API endpoints.

Provides endpoints for simulating slow responses and generating
periodic slow requests for latency diagnostics.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.event_log_service import event_log_service
from src.services.slow_request_service import slow_request_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slow")


class SlowGeneratorStartRequest(BaseModel):
    """Request to start slow request generator."""

    interval_seconds: float = Field(
        default=1.0,
        gt=0,
        description="Interval between requests in seconds",
    )
    max_requests: int = Field(
        default=10,
        ge=1,
        description="Maximum number of requests to generate",
    )
    delay_seconds: float = Field(
        default=5.0,
        gt=0,
        description="Delay for each slow request in seconds",
    )


class SlowResponse(BaseModel):
    """Response for slow request."""

    message: str
    delay_seconds: float
    actual_delay: float


class SlowGeneratorStartResponse(BaseModel):
    """Response for starting slow generator."""

    started: bool
    message: str
    simulation_id: str | None = None
    config: dict


class SlowGeneratorStopResponse(BaseModel):
    """Response for stopping slow generator."""

    stopped: bool
    message: str
    generated_count: int


class SlowGeneratorStatusResponse(BaseModel):
    """Response for generator status."""

    is_running: bool
    generated_count: int
    max_requests: int
    interval_seconds: float
    delay_seconds: float


@router.get(
    "",
    response_model=SlowResponse,
    summary="Slow response (sync-over-async anti-pattern)",
    description=(
        "Returns a response after blocking with time.sleep() (INTENTIONALLY BAD). "
        "This demonstrates the sync-over-async anti-pattern visible in profilers "
        "and diagnostics: event loop lag spikes, increased concurrent request latency, "
        "and time.sleep appearing in stack traces."
    ),
)
async def slow_request(
    delay_seconds: float = Query(
        default=5.0,
        gt=0,
        description="Delay in seconds (blocks event loop)",
    ),
) -> SlowResponse:
    """Return a slow response using blocking time.sleep (INTENTIONALLY BAD!).

    This endpoint demonstrates the sync-over-async anti-pattern where
    time.sleep() is used in async context, blocking the event loop.

    Diagnostic visibility:
    - Event loop lag metric will spike
    - Profilers show time.sleep in stack traces
    - Concurrent requests will queue/timeout
    - Application Insights shows increased response times

    Args:
        delay_seconds: How long to block the event loop.

    Returns:
        Response with delay information.
    """
    actual = await slow_request_service.slow_response(delay_seconds)

    event_log_service.log_event(
        event_type="slow_request",
        message=f"Slow request completed with {delay_seconds}s delay",
        metadata={"delay_seconds": delay_seconds, "actual_delay": actual},
    )

    return SlowResponse(
        message=f"Response delayed by {delay_seconds} seconds",
        delay_seconds=delay_seconds,
        actual_delay=actual,
    )


@router.post(
    "/start",
    response_model=SlowGeneratorStartResponse,
    summary="Start slow request generator",
    description="Start generating periodic slow requests",
)
async def start_slow_generator(
    request: SlowGeneratorStartRequest,
) -> SlowGeneratorStartResponse:
    """Start the slow request generator.

    Creates a background task that generates slow requests
    at the specified interval.

    Args:
        request: Generator configuration.

    Returns:
        Response indicating generator was started.

    Raises:
        HTTPException: If generator already running.
    """
    try:
        await slow_request_service.start_slow_generator(
            interval_seconds=request.interval_seconds,
            max_requests=request.max_requests,
            delay_seconds=request.delay_seconds,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reduce probe frequency during slow-request simulation
    from src.services.probe_service import probe_service

    probe_service.set_slow_request_mode(True)

    return SlowGeneratorStartResponse(
        started=True,
        message="Slow request generator started",
        simulation_id=(
            str(slow_request_service.simulation_id) if slow_request_service.simulation_id else None
        ),
        config={
            "interval_seconds": request.interval_seconds,
            "max_requests": request.max_requests,
            "delay_seconds": request.delay_seconds,
        },
    )


@router.post(
    "/stop",
    response_model=SlowGeneratorStopResponse,
    summary="Stop slow request generator",
    description="Stop the slow request generator if running",
)
async def stop_slow_generator() -> SlowGeneratorStopResponse:
    """Stop the slow request generator.

    Returns:
        Response with final generated count.
    """
    stopped = slow_request_service.stop_slow_generator()

    # Restore normal probe frequency
    from src.services.probe_service import probe_service

    probe_service.set_slow_request_mode(False)

    return SlowGeneratorStopResponse(
        stopped=stopped,
        message="Slow request generator stopped" if stopped else "Generator was not running",
        generated_count=slow_request_service.generated_count,
    )


@router.get(
    "/status",
    response_model=SlowGeneratorStatusResponse,
    summary="Get generator status",
    description="Get the status of the slow request generator",
)
async def get_generator_status() -> SlowGeneratorStatusResponse:
    """Get slow request generator status.

    Returns:
        Current generator status and statistics.
    """
    stats = slow_request_service.get_stats()

    return SlowGeneratorStatusResponse(
        is_running=stats["is_running"],
        generated_count=stats["generated_count"],
        max_requests=stats["max_requests"],
        interval_seconds=stats["interval_seconds"],
        delay_seconds=stats["delay_seconds"],
    )
