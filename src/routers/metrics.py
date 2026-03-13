"""Metrics endpoint router.

Provides detailed system and application metrics for monitoring.
"""

from datetime import datetime

from fastapi import APIRouter

from src.models.responses import MemoryInfo, MetricsResponse, ProcessInfo
from src.services.metrics_service import metrics_service
from src.services.simulation_tracker import simulation_tracker

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse, tags=["metrics"])
async def get_metrics() -> MetricsResponse:
    """Get detailed system and application metrics.

    Returns comprehensive metrics including:
    - CPU usage percentage and core count
    - System memory (total, available, used, percent)
    - Process-specific metrics (PID, memory, CPU, threads)
    - List of active simulations
    - Memory allocation statistics

    This endpoint is designed for dashboard updates and detailed monitoring.

    Returns:
        MetricsResponse with all current metrics.
    """
    # Get system metrics
    cpu_percent = metrics_service.get_cpu_percent()
    cpu_count = metrics_service.get_cpu_count()
    memory = metrics_service.get_memory_info()
    process = metrics_service.get_process_info()

    # Get active simulations
    active_sims = simulation_tracker.list_active()
    active_sim_dicts = [sim.to_dict() for sim in active_sims]

    # Calculate total allocated memory (for memory pressure simulations)
    # This will be populated when memory service is implemented
    allocated_blocks = 0
    total_allocated_mb = 0.0

    return MetricsResponse(
        timestamp=datetime.utcnow(),
        cpu_percent=round(cpu_percent, 2),
        cpu_count=cpu_count,
        memory=MemoryInfo(
            total_mb=round(memory.total_mb, 2),
            available_mb=round(memory.available_mb, 2),
            used_mb=round(memory.used_mb, 2),
            percent=round(memory.percent, 2),
        ),
        process=ProcessInfo(
            pid=process.pid,
            memory_mb=round(process.memory_mb, 2),
            cpu_percent=round(process.cpu_percent, 2),
            threads=process.threads,
            open_files=process.open_files,
        ),
        active_simulations=active_sim_dicts,
        allocated_memory_blocks=allocated_blocks,
        total_allocated_mb=total_allocated_mb,
    )
