"""Domain entities for Performance Problem Simulator.

Contains core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class SimulationType(StrEnum):
    """Types of performance simulations available.

    Each simulation type corresponds to a different performance anti-pattern
    that can be diagnosed using Azure monitoring tools.
    """

    CPU_STRESS = "cpu_stress"
    MEMORY_PRESSURE = "memory_pressure"
    SYNC_BLOCKING = "sync_blocking"
    ASYNC_BLOCKING = "async_blocking"
    SLOW_REQUEST = "slow_request"
    FAILED_REQUEST = "failed_request"
    CRASH = "crash"


@dataclass
class SimulationState:
    """Represents the state of an active simulation.

    Attributes:
        id: Unique identifier for the simulation.
        type: The type of simulation being run.
        started_at: When the simulation was started.
        duration_seconds: How long the simulation should run (None for indefinite).
        params: Additional parameters specific to the simulation type.
    """

    id: UUID = field(default_factory=uuid4)
    type: SimulationType = SimulationType.CPU_STRESS
    started_at: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: float | None = None
    params: dict = field(default_factory=dict)

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since simulation started."""
        return (datetime.utcnow() - self.started_at).total_seconds()

    @property
    def is_expired(self) -> bool:
        """Check if the simulation has exceeded its duration."""
        if self.duration_seconds is None:
            return False
        return self.elapsed_seconds >= self.duration_seconds

    def to_dict(self) -> dict:
        """Convert simulation state to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "type": self.type.value,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "params": self.params,
        }


@dataclass
class AllocatedMemoryBlock:
    """Represents an allocated memory block for memory pressure simulation.

    Attributes:
        id: Unique identifier for the memory block.
        size_mb: Size of the allocated memory in megabytes.
        allocated_at: When the memory was allocated.
    """

    id: UUID = field(default_factory=uuid4)
    size_mb: int = 0
    allocated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert memory block state to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "size_mb": self.size_mb,
            "allocated_at": self.allocated_at.isoformat(),
        }
