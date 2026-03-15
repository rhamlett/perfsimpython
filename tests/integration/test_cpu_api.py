"""Integration tests for CPU stress API endpoints."""

from fastapi.testclient import TestClient


class TestCpuApi:
    """Integration tests for CPU stress simulation API."""

    def test_start_cpu_stress(self, client: TestClient):
        """Test starting CPU stress simulation."""
        response = client.post(
            "/api/cpu/start",
            json={"duration_seconds": 1, "intensity": 3, "workers": 1},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "simulation_id" in data
        assert data["message"] == "CPU stress started"

    def test_start_cpu_stress_default_params(self, client: TestClient):
        """Test starting CPU stress with default parameters."""
        response = client.post("/api/cpu/start", json={})

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

    def test_stop_cpu_stress(self, client: TestClient):
        """Test stopping a specific CPU stress simulation."""
        # Start a simulation first
        start_response = client.post(
            "/api/cpu/start",
            json={"duration_seconds": 60, "intensity": 1},
        )
        simulation_id = start_response.json()["simulation_id"]

        # Stop the simulation
        response = client.post(
            "/api/cpu/stop",
            json={"simulation_id": simulation_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stop_all_cpu_stress(self, client: TestClient):
        """Test stopping all CPU stress simulations."""
        # Start multiple simulations
        client.post("/api/cpu/start", json={"duration_seconds": 60})
        client.post("/api/cpu/start", json={"duration_seconds": 60})

        # Stop all
        response = client.post("/api/cpu/stop-all")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stopped_count" in data.get("data", {})

    def test_cpu_stress_stacking(self, client: TestClient):
        """Test that multiple CPU stress simulations can run concurrently."""
        # Start multiple simulations (should stack)
        response1 = client.post("/api/cpu/start", json={"duration_seconds": 60})
        response2 = client.post("/api/cpu/start", json={"duration_seconds": 60})

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Check they have different IDs
        id1 = response1.json()["simulation_id"]
        id2 = response2.json()["simulation_id"]
        assert id1 != id2

        # Clean up
        client.post("/api/cpu/stop-all")

    def test_start_cpu_stress_high_intensity(self, client: TestClient):
        """Test that high intensity values are accepted (no upper limit)."""
        response = client.post(
            "/api/cpu/start",
            json={"intensity": 100, "duration_seconds": 0.1},
        )

        assert response.status_code == 200  # Should succeed
        client.post("/api/cpu/stop-all")

    def test_start_cpu_stress_invalid_duration(self, client: TestClient):
        """Test that invalid duration is rejected."""
        response = client.post(
            "/api/cpu/start",
            json={"duration_seconds": -5},  # Negative
        )

        assert response.status_code == 422  # Validation error
