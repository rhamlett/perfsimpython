"""Unit tests for CrashService.

Tests crash type definitions and crash trigger preparation.
Note: Actual crash tests are deliberately limited since they terminate the process.
"""

import pytest

from src.services.crash_service import CrashService, CrashType


class TestCrashService:
    """Tests for CrashService."""

    @pytest.fixture
    def service(self) -> CrashService:
        """Create a fresh service instance for each test."""
        return CrashService()

    def test_crash_types_defined(self) -> None:
        """Test that all expected crash types are defined."""
        expected_types = {"exception", "stackoverflow", "oom", "sigabrt"}
        actual_types = {ct.value for ct in CrashType}

        assert expected_types == actual_types

    def test_get_crash_info_exception(self, service: CrashService) -> None:
        """Test crash info for exception type."""
        info = service.get_crash_info(CrashType.EXCEPTION)

        assert info["type"] == "exception"
        assert "description" in info
        assert "diagnostic_signature" in info
        assert "azure_tools" in info

    def test_get_crash_info_stackoverflow(self, service: CrashService) -> None:
        """Test crash info for stack overflow type."""
        info = service.get_crash_info(CrashType.STACKOVERFLOW)

        assert info["type"] == "stackoverflow"
        assert "description" in info
        assert "recursion" in info["description"].lower()

    def test_get_crash_info_oom(self, service: CrashService) -> None:
        """Test crash info for out-of-memory type."""
        info = service.get_crash_info(CrashType.OOM)

        assert info["type"] == "oom"
        assert "description" in info
        assert "memory" in info["description"].lower()

    def test_get_crash_info_sigabrt(self, service: CrashService) -> None:
        """Test crash info for SIGABRT type."""
        info = service.get_crash_info(CrashType.SIGABRT)

        assert info["type"] == "sigabrt"
        assert "description" in info
        assert "signal" in info["description"].lower() or "abort" in info["description"].lower()

    def test_get_all_crash_types(self, service: CrashService) -> None:
        """Test getting info for all crash types."""
        all_info = service.get_all_crash_types()

        assert len(all_info) == 4
        assert all("type" in info for info in all_info)
        assert all("description" in info for info in all_info)

    def test_validate_crash_type_valid(self, service: CrashService) -> None:
        """Test validating valid crash types."""
        for crash_type in CrashType:
            assert service.validate_crash_type(crash_type.value) is True

    def test_validate_crash_type_invalid(self, service: CrashService) -> None:
        """Test validating invalid crash type."""
        assert service.validate_crash_type("invalid_type") is False


class TestCrashServiceSingleton:
    """Tests for singleton behavior."""

    def test_global_instance_exists(self) -> None:
        """Test that global singleton instance is available."""
        from src.services.crash_service import crash_service

        assert crash_service is not None
        assert isinstance(crash_service, CrashService)


# Note: We do NOT test actual crash methods since they would terminate the test process.
# In a real scenario, you would test these in isolated subprocesses if needed.
