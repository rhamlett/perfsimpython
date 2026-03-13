"""Unit tests for health router."""

from fastapi.testclient import TestClient


class TestHealthRouter:
    """Test suite for health endpoint."""

    def test_health_returns_200(self, client: TestClient):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/api/health")

        assert response.status_code == 200

    def test_health_includes_status(self, client: TestClient):
        """Test that health response includes status field."""
        response = client.get("/api/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_includes_metrics(self, client: TestClient):
        """Test that health response includes basic metrics."""
        response = client.get("/api/health")
        data = response.json()

        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "active_simulations" in data

        # Verify types
        assert isinstance(data["cpu_percent"], (int, float))
        assert isinstance(data["memory_percent"], (int, float))
        assert isinstance(data["active_simulations"], int)

    def test_health_includes_version(self, client: TestClient):
        """Test that health response includes version field."""
        response = client.get("/api/health")
        data = response.json()

        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_includes_timestamp(self, client: TestClient):
        """Test that health response includes timestamp field."""
        response = client.get("/api/health")
        data = response.json()

        assert "timestamp" in data
        # Should be ISO format datetime string
        assert "T" in data["timestamp"]
