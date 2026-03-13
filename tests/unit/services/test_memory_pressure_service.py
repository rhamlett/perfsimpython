"""Unit tests for MemoryPressureService.

Tests memory allocation, release, and limit enforcement.
"""

import pytest

from src.services.memory_pressure_service import MemoryPressureService


class TestMemoryPressureService:
    """Tests for MemoryPressureService."""

    @pytest.fixture
    def service(self) -> MemoryPressureService:
        """Create a fresh service instance for each test."""
        svc = MemoryPressureService(max_allocation_mb=500)
        yield svc
        # Cleanup: release all memory after test
        svc.release_all()

    def test_allocate_creates_block(self, service: MemoryPressureService) -> None:
        """Test that allocate_memory creates a memory block."""
        block = service.allocate_memory(100)

        assert block is not None
        assert block.size_mb == 100
        assert block.id is not None

        # Verify block is tracked
        blocks = service.get_allocated_blocks()
        assert len(blocks) == 1
        assert blocks[0].id == block.id

    def test_allocate_multiple_blocks(self, service: MemoryPressureService) -> None:
        """Test allocating multiple memory blocks."""
        service.allocate_memory(50)
        service.allocate_memory(75)
        service.allocate_memory(25)

        blocks = service.get_allocated_blocks()
        assert len(blocks) == 3

        total = service.get_total_allocated_mb()
        assert total == 150

    def test_release_frees_memory(self, service: MemoryPressureService) -> None:
        """Test that release_memory removes a block."""
        block = service.allocate_memory(100)
        block_id = block.id

        result = service.release_memory(block_id)

        assert result is True
        blocks = service.get_allocated_blocks()
        assert len(blocks) == 0
        assert service.get_total_allocated_mb() == 0

    def test_release_nonexistent_block(self, service: MemoryPressureService) -> None:
        """Test releasing a block that doesn't exist returns False."""
        from uuid import uuid4

        result = service.release_memory(uuid4())
        assert result is False

    def test_release_all(self, service: MemoryPressureService) -> None:
        """Test release_all frees all memory blocks."""
        service.allocate_memory(100)
        service.allocate_memory(200)
        service.allocate_memory(50)

        assert len(service.get_allocated_blocks()) == 3

        count = service.release_all()

        assert count == 3
        assert len(service.get_allocated_blocks()) == 0
        assert service.get_total_allocated_mb() == 0

    def test_allocation_limit_enforced(self, service: MemoryPressureService) -> None:
        """Test that allocation fails when exceeding max limit."""
        # Service has max 500MB limit
        service.allocate_memory(400)

        # Try to allocate more than remaining
        with pytest.raises(ValueError) as exc_info:
            service.allocate_memory(200)

        assert "exceed" in str(exc_info.value).lower()
        assert service.get_total_allocated_mb() == 400

    def test_allocation_exactly_at_limit(self, service: MemoryPressureService) -> None:
        """Test allocation succeeds when exactly at limit."""
        block = service.allocate_memory(500)

        assert block is not None
        assert service.get_total_allocated_mb() == 500

    def test_cannot_allocate_negative_size(self, service: MemoryPressureService) -> None:
        """Test that negative allocation size is rejected."""
        with pytest.raises(ValueError) as exc_info:
            service.allocate_memory(-50)

        assert "positive" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    def test_cannot_allocate_zero_size(self, service: MemoryPressureService) -> None:
        """Test that zero allocation size is rejected."""
        with pytest.raises(ValueError) as exc_info:
            service.allocate_memory(0)

        assert "positive" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    def test_get_block_by_id(self, service: MemoryPressureService) -> None:
        """Test retrieving a specific block by ID."""
        block1 = service.allocate_memory(100)
        service.allocate_memory(200)  # Second block for variety

        retrieved = service.get_block(block1.id)

        assert retrieved is not None
        assert retrieved.id == block1.id
        assert retrieved.size_mb == 100

    def test_get_block_nonexistent(self, service: MemoryPressureService) -> None:
        """Test retrieving nonexistent block returns None."""
        from uuid import uuid4

        result = service.get_block(uuid4())
        assert result is None

    def test_remaining_capacity(self, service: MemoryPressureService) -> None:
        """Test remaining capacity calculation."""
        assert service.get_remaining_capacity_mb() == 500

        service.allocate_memory(200)
        assert service.get_remaining_capacity_mb() == 300

        service.allocate_memory(100)
        assert service.get_remaining_capacity_mb() == 200


class TestMemoryPressureServiceSingleton:
    """Tests for singleton behavior."""

    def test_global_instance_exists(self) -> None:
        """Test that global singleton instance is available."""
        from src.services.memory_pressure_service import memory_pressure_service

        assert memory_pressure_service is not None
        assert isinstance(memory_pressure_service, MemoryPressureService)
