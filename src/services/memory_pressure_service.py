"""Memory pressure simulation service.

Allocates and releases memory blocks on demand to simulate
memory pressure scenarios for diagnostic practice.
"""

import logging
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from src.models.entities import AllocatedMemoryBlock

logger = logging.getLogger(__name__)


class MemoryPressureService:
    """Service for simulating memory pressure.

    Manages memory allocations by creating and tracking byte arrays
    to intentionally consume system memory. Used for educational
    purposes to practice memory diagnostics.

    Attributes:
        max_allocation_mb: Maximum total memory that can be allocated.
        _blocks: Dictionary of allocated memory blocks.
        _data: Dictionary of actual byte arrays (kept separate for GC).
        _lock: Thread lock for concurrent access.
    """

    def __init__(self, max_allocation_mb: int = 2048) -> None:
        """Initialize the memory pressure service.

        Args:
            max_allocation_mb: Maximum total allocation in megabytes.
                              Defaults to 2048 MB (2 GB).
        """
        self.max_allocation_mb = max_allocation_mb
        self._blocks: dict[UUID, AllocatedMemoryBlock] = {}
        self._data: dict[UUID, bytearray] = {}
        self._lock = Lock()

    def allocate_memory(self, size_mb: int) -> AllocatedMemoryBlock:
        """Allocate a memory block.

        Creates a bytearray of the specified size to consume memory.

        Args:
            size_mb: Size of memory to allocate in megabytes.

        Returns:
            The allocated memory block metadata.

        Raises:
            ValueError: If size is invalid or would exceed the limit.
        """
        if size_mb <= 0:
            raise ValueError("Size must be a positive number")

        with self._lock:
            current_total = self.get_total_allocated_mb()

            if current_total + size_mb > self.max_allocation_mb:
                raise ValueError(
                    f"Allocation would exceed maximum limit of {self.max_allocation_mb} MB. "
                    f"Currently allocated: {current_total} MB, "
                    f"Requested: {size_mb} MB, "
                    f"Available: {self.max_allocation_mb - current_total} MB"
                )

            # Create the block metadata
            block_id = uuid4()
            block = AllocatedMemoryBlock(
                id=block_id,
                size_mb=size_mb,
                allocated_at=datetime.now(UTC),
            )

            # Actually allocate the memory
            try:
                size_bytes = size_mb * 1024 * 1024
                self._data[block_id] = bytearray(size_bytes)
                self._blocks[block_id] = block

                logger.info(
                    "Allocated %d MB memory (block %s). Total: %d MB",
                    size_mb,
                    block_id,
                    self.get_total_allocated_mb(),
                )

                return block
            except MemoryError:
                logger.error("Failed to allocate %d MB - out of memory", size_mb)
                raise ValueError(f"Failed to allocate {size_mb} MB - insufficient memory")

    def release_memory(self, block_id: UUID) -> bool:
        """Release a specific memory block.

        Args:
            block_id: The ID of the block to release.

        Returns:
            True if the block was found and released, False otherwise.
        """
        with self._lock:
            if block_id not in self._blocks:
                return False

            block = self._blocks[block_id]
            del self._blocks[block_id]
            del self._data[block_id]

            logger.info(
                "Released %d MB memory (block %s). Total: %d MB",
                block.size_mb,
                block_id,
                self.get_total_allocated_mb(),
            )

            return True

    def release_all(self) -> int:
        """Release all allocated memory blocks.

        Returns:
            The number of blocks that were released.
        """
        with self._lock:
            count = len(self._blocks)

            if count > 0:
                total_mb = self.get_total_allocated_mb()
                self._blocks.clear()
                self._data.clear()

                logger.info(
                    "Released all memory: %d blocks, %d MB total",
                    count,
                    total_mb,
                )

            return count

    def get_block(self, block_id: UUID) -> AllocatedMemoryBlock | None:
        """Get a specific memory block by ID.

        Args:
            block_id: The ID of the block to retrieve.

        Returns:
            The block metadata if found, None otherwise.
        """
        return self._blocks.get(block_id)

    def get_allocated_blocks(self) -> list[AllocatedMemoryBlock]:
        """Get all currently allocated memory blocks.

        Returns:
            List of all allocated block metadata.
        """
        return list(self._blocks.values())

    def get_total_allocated_mb(self) -> int:
        """Get the total amount of allocated memory.

        Returns:
            Total allocated memory in megabytes.
        """
        return sum(block.size_mb for block in self._blocks.values())

    def get_remaining_capacity_mb(self) -> int:
        """Get the remaining allocation capacity.

        Returns:
            Remaining capacity in megabytes.
        """
        return self.max_allocation_mb - self.get_total_allocated_mb()


# Global singleton instance
memory_pressure_service = MemoryPressureService()
