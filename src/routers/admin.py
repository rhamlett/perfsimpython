"""Admin API endpoints.

Provides administrative functions for managing simulations,
generating failed requests, and resetting application state.
"""

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.services.cpu_stress_service import cpu_stress_service
from src.services.event_log_service import event_log_service
from src.services.failed_request_service import failed_request_service
from src.services.memory_pressure_service import memory_pressure_service
from src.services.slow_request_service import slow_request_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


class FailedRequestsRequest(BaseModel):
    """Request to generate failed requests."""

    count: int = Field(
        default=10,
        ge=1,
        description="Number of HTTP 500 errors to generate",
    )


class FailedRequestsStartResponse(BaseModel):
    """Response for starting failed request generation."""

    simulation_id: str
    status: str
    message: str


class FailedRequestsStopResponse(BaseModel):
    """Response for stopping failed request generation."""

    simulation_id: str
    status: str
    message: str
    requests_sent: int
    requests_completed: int


class FailedRequestsStatusResponse(BaseModel):
    """Response for failed request status."""

    is_running: bool
    requests_sent: int
    requests_completed: int
    requests_in_progress: int
    target_count: int


class ResetResponse(BaseModel):
    """Response for reset operation."""

    message: str
    cpu_stopped: int
    memory_released: int
    slow_generator_stopped: bool


class StatsResponse(BaseModel):
    """Response for application stats."""

    cpu_simulations: int
    memory_allocated_mb: int
    memory_block_count: int
    slow_generator_running: bool
    slow_requests_generated: int


# Failed requests endpoints at /api/failed-requests (not under /admin)
failed_requests_router = APIRouter()


@failed_requests_router.post(
    "/failed-requests/start",
    response_model=FailedRequestsStartResponse,
    summary="Start generating failed requests",
    description=(
        "Start generating HTTP 500 errors by calling the load test endpoint "
        "with error injection configured for guaranteed failure. Each request "
        "takes ~1.5 seconds and throws a random exception type."
    ),
)
async def start_failed_requests(
    request: FailedRequestsRequest | None = None,
    count: int | None = Query(None, ge=1, description="Number of errors to generate"),
) -> FailedRequestsStartResponse:
    """Start generating HTTP 500 error responses.

    This endpoint starts a background process that generates real HTTP 500 errors
    by calling the load test endpoint with 100% error probability. The errors
    appear in Azure AppLens and Application Insights failure metrics.

    Args:
        request: Request body with count.
        count: Query parameter alternative for count.

    Returns:
        Response with simulation ID and status.
    """
    actual_count = count or (request.count if request else 10)
    result = failed_request_service.start(actual_count)

    return FailedRequestsStartResponse(
        simulation_id=str(result.simulation_id),
        status=result.status,
        message=result.message,
    )


@failed_requests_router.post(
    "/failed-requests/stop",
    response_model=FailedRequestsStopResponse,
    summary="Stop generating failed requests",
    description="Stop the failed request generation. Requests already in progress will complete.",
)
async def stop_failed_requests() -> FailedRequestsStopResponse:
    """Stop generating failed requests.

    Returns:
        Response with final counts.
    """
    result = failed_request_service.stop()

    return FailedRequestsStopResponse(
        simulation_id=str(result.simulation_id),
        status=result.status,
        message=result.message,
        requests_sent=result.requests_sent,
        requests_completed=result.requests_completed,
    )


@failed_requests_router.get(
    "/failed-requests/status",
    response_model=FailedRequestsStatusResponse,
    summary="Get failed request generation status",
    description="Get the current status of the failed request generator.",
)
async def get_failed_requests_status() -> FailedRequestsStatusResponse:
    """Get current status of the failed request generator.

    Returns:
        Response with current counts and running state.
    """
    status = failed_request_service.get_status()

    return FailedRequestsStatusResponse(
        is_running=status.is_running,
        requests_sent=status.requests_sent,
        requests_completed=status.requests_completed,
        requests_in_progress=status.requests_in_progress,
        target_count=status.target_count,
    )


@router.post(
    "/reset",
    response_model=ResetResponse,
    summary="Reset all simulations",
    description="Stop all CPU simulations, release all memory, stop generators",
)
async def reset_all() -> ResetResponse:
    """Reset all simulations and release resources.

    Returns:
        Response with counts of stopped/released resources.
    """
    # Stop CPU simulations
    cpu_count = cpu_stress_service.stop_all()

    # Release all memory
    memory_count = memory_pressure_service.release_all()

    # Stop slow request generator
    slow_stopped = slow_request_service.stop_slow_generator()

    logger.info(
        "Reset complete: %d CPU sims stopped, %d memory blocks released, " "slow generator %s",
        cpu_count,
        memory_count,
        "stopped" if slow_stopped else "was not running",
    )

    event_log_service.log_event(
        event_type="admin_reset",
        message="All simulations reset",
        metadata={
            "cpu_stopped": cpu_count,
            "memory_released": memory_count,
            "slow_generator_stopped": slow_stopped,
        },
    )

    return ResetResponse(
        message="All simulations reset",
        cpu_stopped=cpu_count,
        memory_released=memory_count,
        slow_generator_stopped=slow_stopped,
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get application stats",
    description="Get detailed statistics about current simulation state",
)
async def get_stats() -> StatsResponse:
    """Get application statistics.

    Returns:
        Current state of all simulations.
    """
    slow_stats = slow_request_service.get_stats()

    return StatsResponse(
        cpu_simulations=len(cpu_stress_service.get_active_simulations()),
        memory_allocated_mb=memory_pressure_service.get_total_allocated_mb(),
        memory_block_count=len(memory_pressure_service.get_allocated_blocks()),
        slow_generator_running=slow_stats["is_running"],
        slow_requests_generated=slow_stats["generated_count"],
    )
