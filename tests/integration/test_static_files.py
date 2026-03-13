"""Integration tests for static file serving."""

from fastapi.testclient import TestClient


class TestStaticFiles:
    """Test suite for static file serving."""

    def test_index_html_served(self, client: TestClient):
        """Test that index.html is served at root."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        # Check for dashboard content
        assert "Performance Problem Simulator" in response.text

    def test_css_served(self, client: TestClient):
        """Test that CSS files are served."""
        response = client.get("/css/styles.css")

        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

    def test_js_dashboard_served(self, client: TestClient):
        """Test that dashboard.js is served."""
        response = client.get("/js/dashboard.js")

        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")

    def test_js_charts_served(self, client: TestClient):
        """Test that charts.js is served."""
        response = client.get("/js/charts.js")

        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")

    def test_js_websocket_client_served(self, client: TestClient):
        """Test that websocket-client.js is served."""
        response = client.get("/js/websocket-client.js")

        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")

    def test_favicon_served(self, client: TestClient):
        """Test that favicon is served."""
        response = client.get("/favicon.svg")

        assert response.status_code == 200
        assert "svg" in response.headers.get("content-type", "")
