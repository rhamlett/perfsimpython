"""Admin API endpoints.

Provides administrative functions for managing simulations,
generating failed requests, and resetting application state.
"""

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.services.cpu_stress_service import cpu_stress_service
from src.services.event_log_service import event_log_service
from src.services.memory_pressure_service import memory_pressure_service
from src.services.slow_request_service import slow_request_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


class FailedRequestsRequest(BaseModel):
    """Request to generate failed requests."""

    count: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Number of 500 errors to generate (1-1000)",
    )


class FailedRequestsResponse(BaseModel):
    """Response for failed requests generation."""

    generated_count: int
    error_code: int
    message: str


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


# Failed requests endpoint at /api/failed-requests (not under /admin)
failed_requests_router = APIRouter()


@failed_requests_router.post(
    "/failed-requests",
    response_model=FailedRequestsResponse,
    summary="Generate failed requests",
    description="Generate HTTP 500 error responses for testing error handling",
)
async def generate_failed_requests(
    request: FailedRequestsRequest | None = None,
    count: int | None = Query(None, ge=1, le=1000),
) -> FailedRequestsResponse:
    """Generate HTTP 500 error responses.

    This endpoint logs errors to simulate failed requests for
    testing Application Insights error tracking and alerting.

    Args:
        request: Request body with count.
        count: Query parameter alternative for count.

    Returns:
        Response with count of generated errors.
    """
    # Get count from request body or query param
    actual_count = count or (request.count if request else 10)

    # Log each failed request
    for i in range(actual_count):
        logger.error(
            "Simulated error %d/%d: Intentional 500 error for diagnostic practice",
            i + 1,
            actual_count,
        )
        event_log_service.log_event(
            event_type="failed_request",
            message=f"Simulated HTTP 500 error ({i + 1}/{actual_count})",
            metadata={"error_number": i + 1, "total": actual_count},
        )

    return FailedRequestsResponse(
        generated_count=actual_count,
        error_code=500,
        message=f"Generated {actual_count} failed request log entries",
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
