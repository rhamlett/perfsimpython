"""Unit tests for CpuStressService."""

import time

import pytest

from src.services.cpu_stress_service import CpuStressService


class TestCpuStressService:
    """Test suite for CpuStressService."""

    @pytest.fixture
    def service(self):
        """Create a fresh CpuStressService for each test."""
        svc = CpuStressService()
        yield svc
        # Clean up after test
        svc.stop_all()

    def test_start_creates_threads(self, service):
        """Test that starting stress creates worker threads."""
        simulation = service.start_stress(duration_seconds=2, intensity=1, workers=1)

        assert simulation is not None
        assert simulation.id in service._workers
        assert len(service._workers[simulation.id].threads) == 1
        assert service._workers[simulation.id].threads[0].is_alive()

        # Clean up
        service.stop_stress(simulation.id)

    def test_start_multiple_workers(self, service):
        """Test that starting with multiple workers creates multiple threads."""
        simulation = service.start_stress(duration_seconds=2, intensity=1, workers=3)

        assert len(service._workers[simulation.id].threads) == 3
        for thread in service._workers[simulation.id].threads:
            assert thread.is_alive()

        # Clean up
        service.stop_stress(simulation.id)

    def test_stop_terminates_threads(self, service):
        """Test that stopping a simulation terminates its threads."""
        simulation = service.start_stress(duration_seconds=60, intensity=1, workers=1)
        thread = service._workers[simulation.id].threads[0]

        # Verify thread is running
        assert thread.is_alive()

        # Stop the simulation
        result = service.stop_stress(simulation.id)

        assert result is True
        # Give some time for thread to terminate
        time.sleep(0.2)
        assert not thread.is_alive()

    def test_stop_nonexistent_returns_false(self, service):
        """Test that stopping non-existent simulation returns False."""
        from uuid import uuid4

        result = service.stop_stress(uuid4())
        assert result is False

    def test_stop_all(self, service):
        """Test stopping all simulations."""
        # Start multiple simulations
        service.start_stress(duration_seconds=60, intensity=1)
        service.start_stress(duration_seconds=60, intensity=1)

        assert service.get_active_count() == 2

        # Stop all
        stopped = service.stop_all()

        assert stopped == 2
        assert service.get_active_count() == 0

    def test_simulation_state_params(self, service):
        """Test that simulation state captures parameters correctly."""
        simulation = service.start_stress(duration_seconds=10, intensity=7, workers=2)

        assert simulation.params["intensity"] == 7
        assert simulation.params["workers"] == 2
        assert simulation.duration_seconds == 10

        # Clean up
        service.stop_stress(simulation.id)

    def test_get_active_count(self, service):
        """Test getting active simulation count."""
        assert service.get_active_count() == 0

        sim1 = service.start_stress(duration_seconds=60, intensity=1)
        assert service.get_active_count() == 1

        service.start_stress(duration_seconds=60, intensity=1)  # Second simulation
        assert service.get_active_count() == 2

        service.stop_stress(sim1.id)
        assert service.get_active_count() == 1

        # Clean up
        service.stop_all()
