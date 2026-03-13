"""Pydantic request models for API endpoints.

These models provide automatic validation for incoming API requests.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CpuStressRequest(BaseModel):
    """Request model for CPU stress simulation.

    Attributes:
        duration_seconds: How long to stress the CPU (None for indefinite).
        intensity: CPU stress intensity from 1 (low) to 10 (high).
        workers: Number of parallel CPU workers to spawn.
    """

    duration_seconds: float | None = Field(
        default=None,
        ge=0,
        le=3600,
        description="Duration in seconds (None for indefinite, max 1 hour)",
    )
    intensity: int = Field(
        default=5,
        ge=1,
        le=10,
        description="CPU stress intensity (1-10)",
    )
    workers: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Number of parallel CPU workers",
    )


class MemoryAllocateRequest(BaseModel):
    """Request model for memory allocation simulation.

    Attributes:
        size_mb: Amount of memory to allocate in megabytes.
    """

    size_mb: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Memory to allocate in MB (max 2GB per allocation)",
    )


class BlockingRequest(BaseModel):
    """Request model for blocking simulation.

    Attributes:
        duration_seconds: How long to block.
        count: Number of concurrent blocking operations (sync only).
        chunk_ms: For async blocking, how long each blocking chunk lasts.
    """

    duration_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=300,
        description="Duration to block in seconds (max 5 minutes)",
    )
    count: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of concurrent blocking operations",
    )
    chunk_ms: int = Field(
        default=100,
        ge=10,
        le=5000,
        description="Async blocking chunk duration in milliseconds",
    )


class SlowRequest(BaseModel):
    """Request model for slow request simulation.

    Attributes:
        delay_seconds: How long to delay the response.
        interval_seconds: For generators, time between slow requests.
        max_requests: Maximum number of slow requests to generate.
    """

    delay_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=300,
        description="Response delay in seconds (max 5 minutes)",
    )
    interval_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60,
        description="Interval between generated slow requests",
    )
    max_requests: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of requests to generate",
    )


class CrashRequest(BaseModel):
    """Request model for crash simulation.

    Attributes:
        crash_type: Type of crash to trigger.
    """

    crash_type: Literal["exception", "stackoverflow", "oom", "sigabrt"] = Field(
        default="exception",
        description="Type of crash to simulate",
    )


class FailedRequestsRequest(BaseModel):
    """Request model for generating failed HTTP requests.

    Attributes:
        count: Number of 500 errors to generate.
    """

    count: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Number of HTTP 500 errors to generate",
    )


class StopSimulationRequest(BaseModel):
    """Request model for stopping a specific simulation.

    Attributes:
        simulation_id: UUID of the simulation to stop.
    """

    simulation_id: str = Field(
        ...,
        description="UUID of the simulation to stop",
    )
