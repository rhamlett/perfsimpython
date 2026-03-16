"""Load test API endpoints.

Provides a load test endpoint that simulates realistic application behavior
under varying load conditions, with configurable error injection for testing
Azure diagnostics tools.

Parameter names use camelCase to match .NET version for API compatibility.
"""

import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from src.services.load_test_service import (
    LoadTestRequest as ServiceLoadTestRequest,
)
from src.services.load_test_service import (
    load_test_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/loadtest")


class LoadTestRequest(BaseModel):
    """Request parameters for load test endpoint.

    All parameters have defaults, making the request body optional.
    Parameter names use camelCase to match .NET version.
    """

    model_config = ConfigDict(populate_by_name=True)

    workIterations: int = Field(
        default=200,
        ge=0,
        alias="workIterations",
        description="SHA256 hash iterations for CPU work. 1000 ≈ 5-10ms.",
    )
    bufferSizeKb: int = Field(
        default=20000,
        ge=0,
        alias="bufferSizeKb",
        description="Memory buffer size in KB (default 20 MB).",
    )
    softLimit: int = Field(
        default=25,
        ge=1,
        alias="softLimit",
        description="Concurrent requests before degradation begins.",
    )
    degradationFactor: int = Field(
        default=500,
        ge=0,
        alias="degradationFactor",
        description="Milliseconds delay per request over soft limit.",
    )
    baselineDelayMs: int = Field(
        default=500,
        ge=0,
        alias="baselineDelayMs",
        description="Minimum delay for every request in milliseconds.",
    )
    errorAfter: int = Field(
        default=120,
        ge=0,
        alias="errorAfter",
        description="Seconds before error injection may occur. 0 disables.",
    )
    errorPercent: int = Field(
        default=20,
        ge=0,
        le=100,
        alias="errorPercent",
        description="Probability (0-100) of error after threshold.",
    )


class LoadTestResponse(BaseModel):
    """Response for load test request."""

    model_config = ConfigDict(populate_by_name=True)

    elapsedMs: int = Field(alias="elapsedMs")
    concurrentRequestsAtStart: int = Field(alias="concurrentRequestsAtStart")
    degradationDelayAppliedMs: int = Field(alias="degradationDelayAppliedMs")
    workIterationsCompleted: int = Field(alias="workIterationsCompleted")
    memoryAllocatedBytes: int = Field(alias="memoryAllocatedBytes")
    workCompleted: bool = Field(alias="workCompleted")
    message: str


class LoadTestStatsResponse(BaseModel):
    """Response for load test statistics."""

    model_config = ConfigDict(populate_by_name=True)

    currentConcurrentRequests: int = Field(alias="currentConcurrentRequests")
    totalRequestsProcessed: int = Field(alias="totalRequestsProcessed")
    totalExceptionsThrown: int = Field(alias="totalExceptionsThrown")
    averageResponseTimeMs: float = Field(alias="averageResponseTimeMs")


async def _execute_load_test(
    workIterations: int,
    bufferSizeKb: int,
    softLimit: int,
    degradationFactor: int,
    baselineDelayMs: int,
    errorAfter: int,
    errorPercent: int,
) -> LoadTestResponse:
    """Execute load test with given parameters."""
    service_request = ServiceLoadTestRequest(
        work_iterations=workIterations,
        buffer_size_kb=bufferSizeKb,
        soft_limit=softLimit,
        degradation_factor=degradationFactor,
        baseline_delay_ms=baselineDelayMs,
        error_after=errorAfter,
        error_percent=errorPercent,
    )

    result = await load_test_service.execute_work(service_request)

    return LoadTestResponse(
        elapsedMs=result.elapsed_ms,
        concurrentRequestsAtStart=result.concurrent_requests_at_start,
        degradationDelayAppliedMs=result.degradation_delay_applied_ms,
        workIterationsCompleted=result.work_iterations_completed,
        memoryAllocatedBytes=result.memory_allocated_bytes,
        workCompleted=result.work_completed,
        message=f"Load test completed in {result.elapsed_ms}ms",
    )


@router.get(
    "",
    response_model=LoadTestResponse,
    summary="Load test endpoint (GET with query params)",
    description=(
        "Simulates realistic application behavior under load. "
        "Use query parameters to configure. "
        "Example: /api/loadtest?workIterations=500&bufferSizeKb=10000"
    ),
)
async def load_test_get(
    workIterations: int = Query(default=200, ge=0, description="SHA256 iterations for CPU work"),
    bufferSizeKb: int = Query(default=20000, ge=0, description="Memory buffer size in KB"),
    softLimit: int = Query(default=25, ge=1, description="Concurrent requests before degradation"),
    degradationFactor: int = Query(
        default=500, ge=0, description="Delay ms per request over limit"
    ),
    baselineDelayMs: int = Query(default=500, ge=0, description="Minimum request duration in ms"),
    errorAfter: int = Query(default=120, ge=0, description="Seconds before errors may be thrown"),
    errorPercent: int = Query(default=20, ge=0, le=100, description="Error probability (0-100)"),
) -> LoadTestResponse:
    """Execute load test work with query parameters.

    This endpoint supports GET with query parameters for easy use with
    Azure Load Testing (no JMeter script required).
    """
    return await _execute_load_test(
        workIterations=workIterations,
        bufferSizeKb=bufferSizeKb,
        softLimit=softLimit,
        degradationFactor=degradationFactor,
        baselineDelayMs=baselineDelayMs,
        errorAfter=errorAfter,
        errorPercent=errorPercent,
    )


@router.post(
    "",
    response_model=LoadTestResponse,
    summary="Load test endpoint (POST with body)",
    description=(
        "Simulates realistic application behavior under load. "
        "Performs CPU work, allocates memory, and can inject random errors. "
        "Use for load testing with Azure Load Testing or similar tools."
    ),
)
async def load_test_post(request: LoadTestRequest | None = None) -> LoadTestResponse:
    """Execute load test work with request body.

    This endpoint simulates realistic application behavior:
    - Performs actual CPU work (SHA256 hashing)
    - Allocates and holds memory for request duration
    - Degrades naturally under concurrent load
    - Can inject random errors after configurable threshold

    Args:
        request: Load test configuration. All fields have defaults.

    Returns:
        Response with timing and completion details.

    Raises:
        Random exception (HTTP 500) if error injection triggers.
    """
    if request is None:
        request = LoadTestRequest()

    return await _execute_load_test(
        workIterations=request.workIterations,
        bufferSizeKb=request.bufferSizeKb,
        softLimit=request.softLimit,
        degradationFactor=request.degradationFactor,
        baselineDelayMs=request.baselineDelayMs,
        errorAfter=request.errorAfter,
        errorPercent=request.errorPercent,
    )


@router.get(
    "/stats",
    response_model=LoadTestStatsResponse,
    summary="Get load test statistics",
    description="Get current load test service statistics.",
)
async def get_stats() -> LoadTestStatsResponse:
    """Get current load test statistics.

    Returns:
        Response with concurrent requests, totals, and exception counts.
    """
    stats = load_test_service.get_stats()
    return LoadTestStatsResponse(**stats)
