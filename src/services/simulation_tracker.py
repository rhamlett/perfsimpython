"""Simulation tracker service for managing active simulations.

This service maintains a registry of all running simulations,
allowing the dashboard to display active operations and enabling
cleanup/stop operations.
"""

from threading import Lock
from uuid import UUID

from src.models.entities import SimulationState, SimulationType


class SimulationTracker:
    """Tracks and manages active performance simulations.

    This class provides thread-safe operations for managing the lifecycle
    of simulations across the application.

    Attributes:
        _simulations: Dictionary mapping simulation IDs to their state.
        _lock: Thread lock for safe concurrent access.
    """

    def __init__(self) -> None:
        """Initialize the simulation tracker."""
        self._simulations: dict[UUID, SimulationState] = {}
        self._lock = Lock()

    def add(self, simulation: SimulationState) -> SimulationState:
        """Add a new simulation to the tracker.

        Args:
            simulation: The simulation state to track.

        Returns:
            The added simulation state.
        """
        with self._lock:
            self._simulations[simulation.id] = simulation
        return simulation

    def remove(self, simulation_id: UUID) -> SimulationState | None:
        """Remove a simulation from the tracker.

        Args:
            simulation_id: ID of the simulation to remove.

        Returns:
            The removed simulation state, or None if not found.
        """
        with self._lock:
            return self._simulations.pop(simulation_id, None)

    def get(self, simulation_id: UUID) -> SimulationState | None:
        """Get a simulation by its ID.

        Args:
            simulation_id: ID of the simulation to retrieve.

        Returns:
            The simulation state, or None if not found.
        """
        with self._lock:
            return self._simulations.get(simulation_id)

    def list_active(self) -> list[SimulationState]:
        """Get all active simulations.

        Returns:
            List of all currently tracked simulations.
        """
        with self._lock:
            return list(self._simulations.values())

    def list_by_type(self, sim_type: SimulationType) -> list[SimulationState]:
        """Get all active simulations of a specific type.

        Args:
            sim_type: The type of simulations to retrieve.

        Returns:
            List of simulations matching the specified type.
        """
        with self._lock:
            return [s for s in self._simulations.values() if s.type == sim_type]

    def count(self) -> int:
        """Get the total number of active simulations.

        Returns:
            Count of currently tracked simulations.
        """
        with self._lock:
            return len(self._simulations)

    def get_all_simulations(self) -> list[SimulationState]:
        """Get all active simulations.

        Alias for list_active() for API compatibility.

        Returns:
            List of all currently tracked simulations.
        """
        return self.list_active()

    def count_by_type(self, sim_type: SimulationType) -> int:
        """Get the count of active simulations of a specific type.

        Args:
            sim_type: The type of simulations to count.

        Returns:
            Count of simulations matching the specified type.
        """
        with self._lock:
            return sum(1 for s in self._simulations.values() if s.type == sim_type)

    def clear(self) -> int:
        """Remove all tracked simulations.

        Returns:
            The number of simulations that were cleared.
        """
        with self._lock:
            count = len(self._simulations)
            self._simulations.clear()
            return count

    def cleanup_expired(self) -> list[SimulationState]:
        """Remove all expired simulations.

        Returns:
            List of simulations that were removed.
        """
        with self._lock:
            expired = [s for s in self._simulations.values() if s.is_expired]
            for sim in expired:
                del self._simulations[sim.id]
            return expired


# Global singleton instance
simulation_tracker = SimulationTracker()
