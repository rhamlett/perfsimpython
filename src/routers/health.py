"""Health check endpoint router.

Provides a simple health check endpoint for monitoring and load balancers.
"""

from datetime import datetime

from fastapi import APIRouter

from src.models.responses import HealthResponse
from src.services.metrics_service import metrics_service
from src.services.simulation_tracker import simulation_tracker

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Check application health status.

    Returns basic health information including:
    - Status (healthy/degraded/unhealthy)
    - Current CPU and memory usage percentages
    - Number of active simulations
    - Application version

    This endpoint is designed for quick health checks by load balancers
    and monitoring systems.

    Returns:
        HealthResponse with current health status and basic metrics.
    """
    # Get current metrics
    cpu_percent = metrics_service.get_cpu_percent()
    memory = metrics_service.get_memory_info()
    active_count = simulation_tracker.count()

    # Determine health status
    # High CPU or memory could indicate degraded status
    status = "healthy"
    if cpu_percent > 90 or memory.percent > 90:
        status = "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        cpu_percent=round(cpu_percent, 2),
        memory_percent=round(memory.percent, 2),
        active_simulations=active_count,
    )
