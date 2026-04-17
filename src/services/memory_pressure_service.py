"""Memory pressure simulation service.

Allocates and releases memory blocks on demand to simulate
memory pressure scenarios for diagnostic practice.
"""

import gc
import logging
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from src.models.entities import AllocatedMemoryBlock, SimulationState, SimulationType
from src.services.event_log_service import event_log_service
from src.services.simulation_tracker import simulation_tracker

logger = logging.getLogger(__name__)


class MemoryPressureService:
    """Service for simulating memory pressure.

    Manages memory allocations by creating and tracking byte arrays
    to intentionally consume system memory. Used for educational
    purposes to practice memory diagnostics.

    Attributes:
        max_allocation_mb: Maximum total memory that can be allocated (very high by default).
        _blocks: Dictionary of allocated memory blocks.
        _data: Dictionary of actual byte arrays (kept separate for GC).
        _simulations: Dictionary mapping block IDs to simulation IDs.
        _lock: Thread lock for concurrent access.
    """

    def __init__(self, max_allocation_mb: int = 1_000_000) -> None:
        """Initialize the memory pressure service.

        Args:
            max_allocation_mb: Maximum total allocation in megabytes.
                              Defaults to 1,000,000 MB (1 TB) - effectively unlimited.
        """
        self.max_allocation_mb = max_allocation_mb
        self._blocks: dict[UUID, AllocatedMemoryBlock] = {}
        self._data: dict[UUID, bytearray] = {}
        self._simulations: dict[UUID, UUID] = {}  # block_id -> simulation_id
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

                # Track as a simulation for dashboard visibility
                simulation = SimulationState(
                    type=SimulationType.MEMORY_PRESSURE,
                    duration_seconds=None,  # Indefinite - until released
                    params={"size_mb": size_mb, "block_id": str(block_id)},
                )
                simulation_tracker.add(simulation)
                self._simulations[block_id] = simulation.id

                logger.info(
                    "Allocated %d MB memory (block %s). Total: %d MB",
                    size_mb,
                    block_id,
                    self.get_total_allocated_mb(),
                )

                # Log event for dashboard with simulation_id
                event_log_service.log_start(
                    simulation_type="memory_pressure",
                    simulation_id=simulation.id,
                    message=f"Allocated {size_mb} MB (block {str(block_id)[:8]}...)",
                    data={"size_mb": size_mb, "block_id": str(block_id)},
                    message_key="srv.memory.allocated",
                    message_params={"size": str(size_mb), "chunks": "1"},
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

            # Remove from simulation tracker
            sim_id = self._simulations.pop(block_id, None)
            if sim_id:
                simulation_tracker.remove(sim_id)

            # Force garbage collection to return memory to OS
            gc.collect()

            logger.info(
                "Released %d MB memory (block %s). Total: %d MB",
                block.size_mb,
                block_id,
                self.get_total_allocated_mb(),
            )

            # Log event for dashboard with simulation_id
            event_log_service.log_stop(
                simulation_type="memory_pressure",
                simulation_id=sim_id,
                message=f"Released {block.size_mb} MB (block {str(block_id)[:8]}...)",
                data={"size_mb": block.size_mb, "block_id": str(block_id)},
                message_key="srv.memory.released",
                message_params={"size": str(block.size_mb)},
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

                # Remove all simulations from tracker
                for sim_id in self._simulations.values():
                    simulation_tracker.remove(sim_id)
                self._simulations.clear()

                # Force garbage collection to return memory to OS
                gc.collect()

                logger.info(
                    "Released all memory: %d blocks, %d MB total",
                    count,
                    total_mb,
                )

                # Log event for dashboard
                event_log_service.log_event(
                    event_type="memory_pressure",
                    message=f"Released {count} memory block(s), {total_mb} MB total",
                    metadata={"released_count": count, "total_mb": total_mb},
                    message_key="srv.memory.released",
                    message_params={"size": str(total_mb)},
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

    def get_simulation_id(self, block_id: UUID) -> UUID | None:
        """Get the simulation ID for a specific block.

        Args:
            block_id: The ID of the memory block.

        Returns:
            The simulation ID if found, None otherwise.
        """
        return self._simulations.get(block_id)

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
