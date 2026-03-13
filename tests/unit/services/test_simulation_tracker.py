"""Unit tests for SimulationTracker."""

from uuid import uuid4

import pytest

from src.models.entities import SimulationState, SimulationType
from src.services.simulation_tracker import SimulationTracker


class TestSimulationTracker:
    """Test suite for SimulationTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh SimulationTracker for each test."""
        return SimulationTracker()

    @pytest.fixture
    def cpu_simulation(self):
        """Create a CPU stress simulation state."""
        return SimulationState(
            type=SimulationType.CPU_STRESS,
            duration_seconds=10.0,
            params={"intensity": 5},
        )

    def test_add_simulation(self, tracker, cpu_simulation):
        """Test adding a simulation to the tracker."""
        result = tracker.add(cpu_simulation)

        assert result == cpu_simulation
        assert tracker.count() == 1

    def test_remove_simulation(self, tracker, cpu_simulation):
        """Test removing a simulation from the tracker."""
        tracker.add(cpu_simulation)
        removed = tracker.remove(cpu_simulation.id)

        assert removed == cpu_simulation
        assert tracker.count() == 0

    def test_remove_nonexistent_returns_none(self, tracker):
        """Test removing a non-existent simulation returns None."""
        result = tracker.remove(uuid4())
        assert result is None

    def test_get_simulation(self, tracker, cpu_simulation):
        """Test retrieving a simulation by ID."""
        tracker.add(cpu_simulation)
        result = tracker.get(cpu_simulation.id)

        assert result == cpu_simulation

    def test_get_nonexistent_returns_none(self, tracker):
        """Test retrieving a non-existent simulation returns None."""
        result = tracker.get(uuid4())
        assert result is None

    def test_list_active_returns_all_simulations(self, tracker):
        """Test listing all active simulations."""
        sim1 = SimulationState(type=SimulationType.CPU_STRESS)
        sim2 = SimulationState(type=SimulationType.MEMORY_PRESSURE)

        tracker.add(sim1)
        tracker.add(sim2)

        result = tracker.list_active()

        assert len(result) == 2
        assert sim1 in result
        assert sim2 in result

    def test_list_by_type(self, tracker):
        """Test listing simulations filtered by type."""
        cpu_sim = SimulationState(type=SimulationType.CPU_STRESS)
        mem_sim = SimulationState(type=SimulationType.MEMORY_PRESSURE)

        tracker.add(cpu_sim)
        tracker.add(mem_sim)

        cpu_results = tracker.list_by_type(SimulationType.CPU_STRESS)
        mem_results = tracker.list_by_type(SimulationType.MEMORY_PRESSURE)

        assert len(cpu_results) == 1
        assert cpu_results[0] == cpu_sim
        assert len(mem_results) == 1
        assert mem_results[0] == mem_sim

    def test_count(self, tracker):
        """Test counting total simulations."""
        assert tracker.count() == 0

        tracker.add(SimulationState(type=SimulationType.CPU_STRESS))
        assert tracker.count() == 1

        tracker.add(SimulationState(type=SimulationType.MEMORY_PRESSURE))
        assert tracker.count() == 2

    def test_count_by_type(self, tracker):
        """Test counting simulations by type."""
        tracker.add(SimulationState(type=SimulationType.CPU_STRESS))
        tracker.add(SimulationState(type=SimulationType.CPU_STRESS))
        tracker.add(SimulationState(type=SimulationType.MEMORY_PRESSURE))

        assert tracker.count_by_type(SimulationType.CPU_STRESS) == 2
        assert tracker.count_by_type(SimulationType.MEMORY_PRESSURE) == 1
        assert tracker.count_by_type(SimulationType.SLOW_REQUEST) == 0

    def test_clear(self, tracker):
        """Test clearing all simulations."""
        tracker.add(SimulationState(type=SimulationType.CPU_STRESS))
        tracker.add(SimulationState(type=SimulationType.MEMORY_PRESSURE))

        cleared_count = tracker.clear()

        assert cleared_count == 2
        assert tracker.count() == 0

    def test_thread_safety(self, tracker):
        """Test that tracker handles concurrent access safely."""
        import threading

        simulations = [SimulationState(type=SimulationType.CPU_STRESS) for _ in range(100)]

        def add_simulations():
            for sim in simulations[:50]:
                tracker.add(sim)

        def remove_simulations():
            for sim in simulations[50:]:
                tracker.add(sim)
                tracker.remove(sim.id)

        t1 = threading.Thread(target=add_simulations)
        t2 = threading.Thread(target=remove_simulations)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Should have 50 simulations left (from t1)
        assert tracker.count() == 50
