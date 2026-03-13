"""Pydantic response models for API endpoints.

These models provide consistent, documented response structures.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health check endpoint.

    Attributes:
        status: Health status (healthy, degraded, unhealthy).
        timestamp: When the health check was performed.
        version: Application version.
        cpu_percent: Current CPU usage percentage.
        memory_percent: Current memory usage percentage.
        active_simulations: Number of currently running simulations.
    """

    status: str = Field(description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")
    cpu_percent: float = Field(default=0.0, description="Current CPU usage %")
    memory_percent: float = Field(default=0.0, description="Current memory usage %")
    active_simulations: int = Field(default=0, description="Number of active simulations")


class MemoryInfo(BaseModel):
    """Memory information sub-model."""

    total_mb: float = Field(description="Total system memory in MB")
    available_mb: float = Field(description="Available memory in MB")
    used_mb: float = Field(description="Used memory in MB")
    percent: float = Field(description="Memory usage percentage")


class ProcessInfo(BaseModel):
    """Process information sub-model."""

    pid: int = Field(description="Process ID")
    memory_mb: float = Field(description="Process memory usage in MB")
    cpu_percent: float = Field(description="Process CPU usage percentage")
    threads: int = Field(description="Number of threads")
    open_files: int = Field(description="Number of open file descriptors")


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint.

    Provides detailed system and application metrics.
    """

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_percent: float = Field(description="System CPU usage percentage")
    cpu_count: int = Field(description="Number of CPU cores")
    memory: MemoryInfo = Field(description="System memory information")
    process: ProcessInfo = Field(description="Current process information")
    active_simulations: list[dict] = Field(
        default_factory=list, description="List of active simulations"
    )
    allocated_memory_blocks: int = Field(default=0, description="Number of allocated memory blocks")
    total_allocated_mb: float = Field(default=0.0, description="Total allocated memory in MB")


class SimulationResponse(BaseModel):
    """Response model for simulation operations.

    Attributes:
        success: Whether the operation succeeded.
        message: Human-readable status message.
        simulation_id: ID of the affected simulation (if applicable).
        data: Additional response data.
    """

    success: bool = Field(description="Operation success status")
    message: str = Field(description="Status message")
    simulation_id: str | None = Field(default=None, description="Simulation ID if applicable")
    data: dict[str, Any] | None = Field(default=None, description="Additional response data")


class ErrorResponse(BaseModel):
    """Response model for error responses.

    Provides consistent error reporting structure.
    """

    error: str = Field(description="Error type/code")
    message: str = Field(description="Human-readable error message")
    detail: str | None = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: str | None = Field(default=None, description="Request path that caused error")
