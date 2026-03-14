"""CPU stress simulation service.

This service creates CPU-bound work using multiprocessing to consume
CPU resources. Each worker process performs intensive calculations
to drive CPU usage higher.

EDUCATIONAL NOTE: In production, excessive CPU usage causes:
- Slow response times for all requests
- Health check failures leading to restarts
- Autoscaling triggers (if configured)
- In Azure App Service: visible in CPU % metrics and App Service Diagnostics
"""

import logging
import math
import multiprocessing
import time
from uuid import UUID

from src.models.entities import SimulationState, SimulationType
from src.services.event_log_service import event_log_service
from src.services.simulation_tracker import simulation_tracker

logger = logging.getLogger(__name__)


def _cpu_worker(duration: float | None, intensity: int) -> None:
    """Worker function that performs CPU-intensive calculations.

    This function runs in a separate process and performs mathematical
    operations to consume CPU cycles.

    Args:
        duration: How long to run (None for indefinite).
        intensity: How aggressively to use CPU (1-10).
    """
    start_time = time.time()

    # Intensity affects how many iterations we do per cycle
    iterations_per_cycle = intensity * 10000

    while True:
        # Check if duration exceeded
        if duration is not None:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break

        # Perform CPU-intensive calculations
        # Using math operations that can't be easily optimized away
        x = 0.0
        for i in range(iterations_per_cycle):
            x += math.sin(i) * math.cos(i)
            x += math.sqrt(abs(x) + 1)
            x = math.tanh(x)


class CpuStressService:
    """Service for managing CPU stress simulations.

    This service can spawn multiple worker processes that perform
    CPU-intensive calculations, allowing simulation of high CPU usage
    scenarios for diagnostic practice.

    Attributes:
        _processes: Dictionary mapping simulation IDs to worker processes.
    """

    def __init__(self) -> None:
        """Initialize the CPU stress service."""
        self._processes: dict[UUID, list[multiprocessing.Process]] = {}

    def start_stress(
        self,
        duration_seconds: float | None = None,
        intensity: int = 5,
        workers: int = 1,
    ) -> SimulationState:
        """Start a CPU stress simulation.

        Creates worker processes that perform CPU-intensive calculations.
        Multiple calls stack to increase CPU load.

        Args:
            duration_seconds: How long to run (None for indefinite).
            intensity: CPU stress intensity from 1 (low) to 10 (high).
            workers: Number of parallel worker processes.

        Returns:
            SimulationState tracking the started simulation.
        """
        # Create simulation state
        simulation = SimulationState(
            type=SimulationType.CPU_STRESS,
            duration_seconds=duration_seconds,
            params={
                "intensity": intensity,
                "workers": workers,
            },
        )

        # Start worker processes
        processes = []
        for _ in range(workers):
            process = multiprocessing.Process(
                target=_cpu_worker,
                args=(duration_seconds, intensity),
                daemon=True,
            )
            process.start()
            processes.append(process)

        # Store processes for cleanup
        self._processes[simulation.id] = processes

        # Track the simulation
        simulation_tracker.add(simulation)

        # Log the event
        event_log_service.log_start(
            simulation_type="cpu_stress",
            simulation_id=simulation.id,
            message=f"CPU stress started: {workers} workers at intensity {intensity}",
            data={"duration": duration_seconds, "intensity": intensity, "workers": workers},
        )

        logger.info(
            "Started CPU stress simulation %s with %d workers at intensity %d",
            simulation.id,
            workers,
            intensity,
        )

        return simulation

    def stop_stress(self, simulation_id: UUID) -> bool:
        """Stop a specific CPU stress simulation.

        Args:
            simulation_id: ID of the simulation to stop.

        Returns:
            True if stopped successfully, False if not found.
        """
        processes = self._processes.pop(simulation_id, None)
        if processes is None:
            return False

        # Terminate all worker processes
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()

        # Remove from tracker
        simulation_tracker.remove(simulation_id)

        # Log the event
        event_log_service.log_stop(
            simulation_type="cpu_stress",
            simulation_id=simulation_id,
            message="CPU stress stopped",
        )

        logger.info("Stopped CPU stress simulation %s", simulation_id)
        return True

    def stop_all(self) -> int:
        """Stop all running CPU stress simulations.

        Returns:
            Number of simulations stopped.
        """
        simulation_ids = list(self._processes.keys())
        stopped_count = 0

        for sim_id in simulation_ids:
            if self.stop_stress(sim_id):
                stopped_count += 1

        if stopped_count > 0:
            event_log_service.log_stop(
                simulation_type="cpu_stress",
                message=f"Stopped all CPU stress simulations ({stopped_count} total)",
                data={"stopped_count": stopped_count},
            )

        logger.info("Stopped %d CPU stress simulations", stopped_count)
        return stopped_count

    def get_active_count(self) -> int:
        """Get the number of active CPU stress simulations.

        Returns:
            Count of running simulations.
        """
        return len(self._processes)

    def get_active_simulations(self) -> list[UUID]:
        """Get list of active CPU stress simulation IDs.

        Returns:
            List of simulation UUIDs currently running.
        """
        return list(self._processes.keys())

    def cleanup_completed(self) -> int:
        """Clean up any completed simulations.

        Returns:
            Number of simulations cleaned up.
        """
        completed = []
        for sim_id, processes in self._processes.items():
            # Check if all processes have finished
            if all(not p.is_alive() for p in processes):
                completed.append(sim_id)

        for sim_id in completed:
            self._processes.pop(sim_id, None)
            simulation_tracker.remove(sim_id)

        return len(completed)


# Global singleton instance
cpu_stress_service = CpuStressService()
