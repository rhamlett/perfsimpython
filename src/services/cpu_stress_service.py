"""CPU stress simulation service.

This service creates CPU-bound work using in-process threads to consume
CPU resources. Each worker thread performs intensive calculations that
compete with the FastAPI event loop due to Python's GIL.

Note:
    In production, excessive CPU usage causes:

    - Slow response times for all requests (directly observable with this
      approach)
    - Health check failures leading to restarts
    - Autoscaling triggers (if configured)
    - In Azure App Service: visible in CPU % metrics and App Service
      Diagnostics

    Unlike multiprocessing, in-process threads share the GIL with the main
    event loop. CPU-bound work in these threads directly competes for
    execution time, causing measurable request latency increases.
"""

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from uuid import UUID

from src.models.entities import SimulationState, SimulationType
from src.services.event_log_service import event_log_service
from src.services.simulation_tracker import simulation_tracker

logger = logging.getLogger(__name__)


@dataclass
class CpuWorkerState:
    """State for a CPU stress worker thread.

    Attributes:
        threads: List of worker threads.
        stop_event: Event to signal threads to stop.
    """

    threads: list[threading.Thread] = field(default_factory=list)
    stop_event: threading.Event = field(default_factory=threading.Event)


def _cpu_worker(
    stop_event: threading.Event,
    duration: float | None,
    intensity: int,
) -> None:
    """Worker function that performs CPU-intensive calculations.

    This function runs in a thread within the main process. Due to Python's
    GIL, CPU-bound work here directly competes with the event loop, causing
    request latency to increase.

    Intensity controls iterations per cycle (``intensity * 1000``). The
    value was reduced from 10000 to allow more frequent stop-event checks.
    Math operations (sin, cos, sqrt, tanh) are chosen because they cannot
    be easily optimized away by the interpreter.

    Args:
        stop_event: Event to check for stop signal.
        duration: How long to run (None for indefinite).
        intensity: How aggressively to use CPU (1-10).
    """
    start_time = time.time()

    iterations_per_cycle = intensity * 1000

    while not stop_event.is_set():
        if duration is not None:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break

        x = 0.0
        for i in range(iterations_per_cycle):
            x += math.sin(i) * math.cos(i)
            x += math.sqrt(abs(x) + 1)
            x = math.tanh(x)


class CpuStressService:
    """Service for managing CPU stress simulations.

    This service spawns worker threads that perform CPU-intensive calculations
    within the main process. Due to Python's GIL, this directly competes with
    the FastAPI event loop, causing observable request latency increases.

    Attributes:
        _workers: Dictionary mapping simulation IDs to worker state.
    """

    def __init__(self) -> None:
        """Initialize the CPU stress service."""
        self._workers: dict[UUID, CpuWorkerState] = {}

    def start_stress(
        self,
        duration_seconds: float | None = None,
        intensity: int = 5,
        workers: int = 1,
    ) -> SimulationState:
        """Start a CPU stress simulation.

        Creates worker threads that perform CPU-intensive calculations.
        Multiple calls stack to increase CPU load.

        Args:
            duration_seconds: How long to run (None for indefinite).
            intensity: CPU stress intensity from 1 (low) to 10 (high).
            workers: Number of parallel worker threads.

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

        # Create worker state with stop event
        worker_state = CpuWorkerState()

        # Start worker threads
        for i in range(workers):
            thread = threading.Thread(
                target=_cpu_worker,
                args=(worker_state.stop_event, duration_seconds, intensity),
                daemon=True,
                name=f"cpu-stress-{simulation.id}-{i}",
            )
            thread.start()
            worker_state.threads.append(thread)

        # Store worker state for cleanup
        self._workers[simulation.id] = worker_state

        # Track the simulation
        simulation_tracker.add(simulation)

        # Log the event
        event_log_service.log_start(
            simulation_type="cpu_stress",
            simulation_id=simulation.id,
            message=f"CPU stress started: {workers} in-process workers at intensity {intensity}",
            data={"duration": duration_seconds, "intensity": intensity, "workers": workers},
            message_key="srv.cpu.started",
            message_params={
                "intensity": str(intensity),
                "threads": str(workers),
                "duration": str(duration_seconds),
            },
        )

        logger.info(
            "Started CPU stress simulation %s with %d in-process workers at intensity %d",
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
        worker_state = self._workers.pop(simulation_id, None)
        if worker_state is None:
            return False

        # Signal all threads to stop
        worker_state.stop_event.set()

        # Wait for threads to finish
        for thread in worker_state.threads:
            thread.join(timeout=2.0)

        # Remove from tracker
        simulation_tracker.remove(simulation_id)

        # Log the event
        event_log_service.log_stop(
            simulation_type="cpu_stress",
            simulation_id=simulation_id,
            message="CPU stress stopped",
            message_key="srv.cpu.stopped",
        )

        logger.info("Stopped CPU stress simulation %s", simulation_id)
        return True

    def stop_all(self) -> int:
        """Stop all running CPU stress simulations.

        Returns:
            Number of simulations stopped.
        """
        simulation_ids = list(self._workers.keys())
        stopped_count = 0

        for sim_id in simulation_ids:
            if self.stop_stress(sim_id):
                stopped_count += 1

        if stopped_count > 0:
            event_log_service.log_stop(
                simulation_type="cpu_stress",
                message=f"Stopped all CPU stress simulations ({stopped_count} total)",
                data={"stopped_count": stopped_count},
                message_key="srv.cpu.stopped",
            )

        logger.info("Stopped %d CPU stress simulations", stopped_count)
        return stopped_count

    def get_active_count(self) -> int:
        """Get the number of active CPU stress simulations.

        Returns:
            Count of running simulations.
        """
        return len(self._workers)

    def cleanup_finished(self) -> int:
        """Clean up any CPU stress simulations whose threads have naturally finished.

        This is called periodically to remove simulations from the tracker
        when their worker threads have completed their duration.

        Returns:
            Number of simulations cleaned up.
        """
        finished_ids: list[UUID] = []

        for sim_id, worker_state in self._workers.items():
            # Check if all threads for this simulation have finished
            all_finished = all(not t.is_alive() for t in worker_state.threads)
            if all_finished:
                finished_ids.append(sim_id)

        cleaned_count = 0
        for sim_id in finished_ids:
            # Remove the worker state
            worker_state = self._workers.pop(sim_id)
            for t in worker_state.threads:
                t.join(timeout=0.1)  # Brief join to clean up

            # Remove from the simulation tracker
            simulation_tracker.remove(sim_id)
            cleaned_count += 1

            logger.debug("Cleaned up finished CPU stress simulation %s", sim_id)

        return cleaned_count

    def get_active_simulations(self) -> list[UUID]:
        """Get list of active CPU stress simulation IDs.

        Returns:
            List of simulation UUIDs currently running.
        """
        return list(self._workers.keys())

    def cleanup_completed(self) -> int:
        """Clean up any completed simulations.

        Returns:
            Number of simulations cleaned up.
        """
        completed = []
        for sim_id, worker_state in self._workers.items():
            # Check if all threads have finished
            if all(not t.is_alive() for t in worker_state.threads):
                completed.append(sim_id)

        for sim_id in completed:
            self._workers.pop(sim_id, None)
            simulation_tracker.remove(sim_id)

        return len(completed)


# Global singleton instance
cpu_stress_service = CpuStressService()
