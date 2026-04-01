"""CPU stress simulation endpoint router.

Provides API endpoints for starting, stopping, and managing CPU stress simulations.

Note:
    These endpoints intentionally create high CPU load.
    Use in sandboxed environments only. In Azure, observe CPU metrics in:

    - App Service Diagnostics → CPU Usage
    - Application Insights → Performance
    - Metrics blade → CPU Percentage
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from src.models.requests import CpuStressRequest, StopSimulationRequest
from src.models.responses import SimulationResponse
from src.services.cpu_stress_service import cpu_stress_service

router = APIRouter()


@router.post("/cpu/start", response_model=SimulationResponse, tags=["cpu"])
async def start_cpu_stress(request: CpuStressRequest = CpuStressRequest()) -> SimulationResponse:
    """Start a CPU stress simulation.

    Creates worker processes that perform CPU-intensive calculations.
    Multiple calls will stack CPU load (each adds more workers).

    Note:
        This simulates runaway CPU usage. In Azure App Service,
        you can diagnose this using:

        - App Service Diagnostics → CPU Usage blade
        - Kudu SSH → top/htop commands
        - Application Insights → Performance counters

    Args:
        request: CPU stress parameters including duration, intensity, and workers.

    Returns:
        SimulationResponse with the simulation ID and status.
    """
    simulation = cpu_stress_service.start_stress(
        duration_seconds=request.duration_seconds,
        intensity=request.intensity,
        workers=request.workers,
    )

    return SimulationResponse(
        success=True,
        message="CPU stress started",
        simulation_id=str(simulation.id),
        data={
            "duration_seconds": request.duration_seconds,
            "intensity": request.intensity,
            "workers": request.workers,
        },
    )


class StopCpuRequest:
    """Request body for stopping a specific CPU simulation."""

    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id


@router.post("/cpu/stop", response_model=SimulationResponse, tags=["cpu"])
async def stop_cpu_stress(request: StopSimulationRequest) -> SimulationResponse:
    """Stop a specific CPU stress simulation.

    Args:
        request: Request containing simulation_id to stop.

    Returns:
        SimulationResponse indicating success or failure.

    Raises:
        HTTPException: If simulation not found.
    """
    try:
        sim_uuid = UUID(request.simulation_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid simulation_id format",
        )

    success = cpu_stress_service.stop_stress(sim_uuid)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {request.simulation_id} not found",
        )

    return SimulationResponse(
        success=True,
        message="CPU stress stopped",
        simulation_id=request.simulation_id,
    )


@router.post("/cpu/stop-all", response_model=SimulationResponse, tags=["cpu"])
async def stop_all_cpu_stress() -> SimulationResponse:
    """Stop all running CPU stress simulations.

    Returns:
        SimulationResponse with count of stopped simulations.
    """
    stopped_count = cpu_stress_service.stop_all()

    return SimulationResponse(
        success=True,
        message=f"Stopped {stopped_count} CPU stress simulation(s)",
        data={"stopped_count": stopped_count},
    )
