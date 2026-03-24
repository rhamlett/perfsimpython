"""Memory pressure API endpoints.

Provides endpoints for allocating and releasing memory blocks
to simulate memory pressure scenarios.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.memory_pressure_service import memory_pressure_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory")


class MemoryAllocateRequest(BaseModel):
    """Request to allocate memory."""

    size_mb: int = Field(
        ...,
        gt=0,
        description="Size in megabytes to allocate",
    )


class MemoryAllocateResponse(BaseModel):
    """Response for memory allocation."""

    block_id: UUID
    size_mb: int
    message: str
    simulation_id: str | None = None


class MemoryReleaseRequest(BaseModel):
    """Request to release a memory block."""

    block_id: UUID = Field(..., description="ID of the block to release")


class MemoryReleaseResponse(BaseModel):
    """Response for memory release."""

    released: bool
    block_id: UUID


class MemoryReleaseAllResponse(BaseModel):
    """Response for releasing all memory."""

    released_count: int
    message: str


class MemoryBlockInfo(BaseModel):
    """Information about an allocated memory block."""

    id: UUID
    size_mb: int
    allocated_at: str


class MemoryStatusResponse(BaseModel):
    """Response for memory status."""

    total_allocated_mb: int
    max_allocation_mb: int
    remaining_capacity_mb: int
    block_count: int
    blocks: list[MemoryBlockInfo]


@router.post(
    "/allocate",
    response_model=MemoryAllocateResponse,
    summary="Allocate memory",
    description="Allocate a block of memory to simulate memory pressure",
)
async def allocate_memory(
    request: MemoryAllocateRequest | None = None,
    size_mb: int | None = Query(None, gt=0, description="Size in MB"),
) -> MemoryAllocateResponse:
    """Allocate a memory block.

    Args:
        request: Request body with size_mb.
        size_mb: Query parameter alternative for size.

    Returns:
        Allocation response with block ID.

    Raises:
        HTTPException: If allocation fails or exceeds limit.
    """
    # Get size from request body or query param
    actual_size = size_mb
    if request is not None:
        actual_size = request.size_mb

    if actual_size is None:
        raise HTTPException(
            status_code=400,
            detail="size_mb is required (in body or query parameter)",
        )

    try:
        block = memory_pressure_service.allocate_memory(actual_size)
        simulation_id = memory_pressure_service.get_simulation_id(block.id)

        return MemoryAllocateResponse(
            block_id=block.id,
            size_mb=block.size_mb,
            message="Memory allocated",
            simulation_id=str(simulation_id) if simulation_id else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/release",
    response_model=MemoryReleaseResponse,
    summary="Release memory block",
    description="Release a specific memory block by ID",
)
async def release_memory(request: MemoryReleaseRequest) -> MemoryReleaseResponse:
    """Release a specific memory block.

    Args:
        request: Request with block_id to release.

    Returns:
        Release response indicating success.

    Raises:
        HTTPException: If block not found.
    """
    released = memory_pressure_service.release_memory(request.block_id)

    if not released:
        raise HTTPException(
            status_code=404,
            detail=f"Memory block {request.block_id} not found",
        )

    return MemoryReleaseResponse(
        released=True,
        block_id=request.block_id,
    )


@router.post(
    "/release-all",
    response_model=MemoryReleaseAllResponse,
    summary="Release all memory",
    description="Release all allocated memory blocks",
)
async def release_all_memory() -> MemoryReleaseAllResponse:
    """Release all allocated memory blocks.

    Returns:
        Response with count of released blocks.
    """
    count = memory_pressure_service.release_all()

    return MemoryReleaseAllResponse(
        released_count=count,
        message="All memory released",
    )


@router.get(
    "/status",
    response_model=MemoryStatusResponse,
    summary="Get memory status",
    description="Get current memory allocation status",
)
async def get_memory_status() -> MemoryStatusResponse:
    """Get current memory allocation status.

    Returns:
        Status response with allocation details.
    """
    blocks = memory_pressure_service.get_allocated_blocks()

    return MemoryStatusResponse(
        total_allocated_mb=memory_pressure_service.get_total_allocated_mb(),
        max_allocation_mb=memory_pressure_service.max_allocation_mb,
        remaining_capacity_mb=memory_pressure_service.get_remaining_capacity_mb(),
        block_count=len(blocks),
        blocks=[
            MemoryBlockInfo(
                id=block.id,
                size_mb=block.size_mb,
                allocated_at=block.allocated_at.isoformat(),
            )
            for block in blocks
        ],
    )
