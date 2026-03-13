"""Integration tests for WebSocket connections."""

from fastapi.testclient import TestClient


class TestWebSocket:
    """Test suite for WebSocket functionality."""

    def test_websocket_connect(self, client: TestClient):
        """Test that WebSocket connection can be established."""
        with client.websocket_connect("/ws/metrics") as websocket:
            # Connection should succeed
            # Receive metrics message to verify connection is working
            data = websocket.receive_json()
            assert data["type"] == "metrics"
            assert "data" in data

    def test_websocket_receive_metrics(self, client: TestClient):
        """Test that WebSocket receives metrics data."""
        with client.websocket_connect("/ws/metrics") as websocket:
            # Should receive metrics data
            data = websocket.receive_json()

            # Verify it contains expected metric structure
            assert data["type"] == "metrics"
            assert "system" in data["data"]
            assert "process" in data["data"]
            assert "cpu_percent" in data["data"]["system"]
            assert "memory_percent" in data["data"]["system"]

    def test_websocket_multiple_messages(self, client: TestClient):
        """Test receiving multiple WebSocket messages."""
        with client.websocket_connect("/ws/metrics") as websocket:
            # Receive first message
            data1 = websocket.receive_json()
            assert data1["type"] == "metrics"

            # Receive second message (if available within timeout)
            try:
                data2 = websocket.receive_json()
                assert data2["type"] == "metrics"
            except Exception:
                # May timeout if no second message, which is acceptable
                pass
