"""Unit tests for MetricsService."""

from src.services.metrics_service import MetricsService, metrics_service


class TestMetricsService:
    """Test suite for MetricsService."""

    def test_get_cpu_percent_returns_float(self):
        """Test that get_cpu_percent returns a float value."""
        service = MetricsService()
        result = service.get_cpu_percent()

        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_get_memory_info_returns_dict(self):
        """Test that get_memory_info returns proper structure."""
        service = MetricsService()
        result = service.get_memory_info()

        # Check that all expected attributes exist
        assert hasattr(result, "total_mb")
        assert hasattr(result, "available_mb")
        assert hasattr(result, "used_mb")
        assert hasattr(result, "percent")

        # Check values are reasonable
        assert result.total_mb > 0
        assert result.available_mb >= 0
        assert result.used_mb >= 0
        assert 0.0 <= result.percent <= 100.0

    def test_get_cpu_count_returns_positive_integer(self):
        """Test that get_cpu_count returns a positive integer."""
        service = MetricsService()
        result = service.get_cpu_count()

        assert isinstance(result, int)
        assert result >= 1

    def test_get_process_info_returns_valid_metrics(self):
        """Test that get_process_info returns valid process metrics."""
        service = MetricsService()
        result = service.get_process_info()

        assert hasattr(result, "pid")
        assert hasattr(result, "memory_mb")
        assert hasattr(result, "cpu_percent")
        assert hasattr(result, "threads")

        assert result.pid > 0
        assert result.memory_mb >= 0
        assert result.threads >= 1

    def test_get_all_metrics_returns_complete_structure(self):
        """Test that get_all_metrics returns complete metrics dictionary."""
        service = MetricsService()
        result = service.get_all_metrics()

        assert "cpu_percent" in result
        assert "cpu_count" in result
        assert "memory" in result
        assert "process" in result

        # Check nested structures
        assert "total_mb" in result["memory"]
        assert "pid" in result["process"]

    def test_singleton_instance_works(self):
        """Test that the singleton instance is functional."""
        result = metrics_service.get_cpu_percent()
        assert isinstance(result, float)

    def test_memory_metrics_to_dict(self):
        """Test that memory metrics can be serialized to dict."""
        service = MetricsService()
        memory = service.get_memory_info()
        result = memory.to_dict()

        assert isinstance(result, dict)
        assert "total_mb" in result
        assert "available_mb" in result
        assert "used_mb" in result
        assert "percent" in result

    def test_process_metrics_to_dict(self):
        """Test that process metrics can be serialized to dict."""
        service = MetricsService()
        process = service.get_process_info()
        result = process.to_dict()

        assert isinstance(result, dict)
        assert "pid" in result
        assert "memory_mb" in result
        assert "cpu_percent" in result
        assert "threads" in result
