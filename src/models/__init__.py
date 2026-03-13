"""Models package for Performance Problem Simulator.

Contains Pydantic models for request/response validation and domain entities.
"""

from src.models.entities import AllocatedMemoryBlock, SimulationState, SimulationType
from src.models.requests import (
    BlockingRequest,
    CpuStressRequest,
    CrashRequest,
    FailedRequestsRequest,
    MemoryAllocateRequest,
    SlowRequest,
)
from src.models.responses import (
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
    SimulationResponse,
)

__all__ = [
    # Entities
    "SimulationType",
    "SimulationState",
    "AllocatedMemoryBlock",
    # Requests
    "CpuStressRequest",
    "MemoryAllocateRequest",
    "BlockingRequest",
    "SlowRequest",
    "CrashRequest",
    "FailedRequestsRequest",
    # Responses
    "HealthResponse",
    "MetricsResponse",
    "SimulationResponse",
    "ErrorResponse",
]
