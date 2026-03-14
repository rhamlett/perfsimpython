"""Blocking simulation API endpoints.

Provides endpoints for simulating synchronous and asynchronous blocking
to demonstrate thread pool starvation and event loop blocking patterns.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.services.blocking_service import blocking_service
from src.services.event_log_service import event_log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blocking")


class SyncBlockRequest(BaseModel):
    """Request for synchronous blocking."""

    duration_seconds: float = Field(
        ...,
        gt=0,
        le=300,
        description="Duration to block in seconds (max 300)",
    )
    count: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Number of blocking operations to perform",
    )


class AsyncBlockRequest(BaseModel):
    """Request for asynchronous blocking."""

    duration_seconds: float = Field(
        ...,
        gt=0,
        le=300,
        description="Duration to block in seconds (max 300)",
    )
    chunk_ms: int | None = Field(
        default=None,
        ge=1,
        le=10000,
        description="If provided, block in chunks of this size (ms)",
    )


class BlockingResponse(BaseModel):
    """Response for blocking operations."""

    message: str
    blocked_duration: float
    count: int = 1
    chunked: bool = False


@router.post(
    "/sync",
    response_model=BlockingResponse,
    summary="Trigger synchronous blocking",
    description=(
        "Block the thread pool with synchronous sleep operations. "
        "This simulates synchronous I/O or CPU-bound work that "
        "starves the thread pool and causes request queuing."
    ),
)
async def sync_blocking(request: SyncBlockRequest) -> BlockingResponse:
    """Trigger synchronous blocking.

    This endpoint intentionally blocks thread pool workers using time.sleep().
    When all workers are blocked, incoming requests will queue up.

    Args:
        request: Request with duration and count.

    Returns:
        Response with actual blocked duration.
    """
    event_log_service.log_event(
        event_type="blocking_started",
        message=f"Starting sync blocking for {request.duration_seconds}s x{request.count}",
        metadata={
            "type": "sync",
            "duration": request.duration_seconds,
            "count": request.count,
        },
    )

    total_blocked = 0.0
    for i in range(request.count):
        # Run sync blocking in thread pool (proper async handling)
        blocked = await blocking_service.run_sync_in_thread(request.duration_seconds)
        total_blocked += blocked
        logger.debug("Sync blocking iteration %d/%d complete", i + 1, request.count)

    event_log_service.log_event(
        event_type="blocking_completed",
        message=f"Sync blocking completed: {total_blocked:.2f}s total",
        metadata={
            "type": "sync",
            "total_blocked": total_blocked,
            "count": request.count,
        },
    )

    return BlockingResponse(
        message=f"Sync blocked for {total_blocked:.2f} seconds",
        blocked_duration=total_blocked,
        count=request.count,
        chunked=False,
    )


@router.post(
    "/async",
    response_model=BlockingResponse,
    summary="Trigger asynchronous blocking",
    description=(
        "Block the event loop with time.sleep() in async context. "
        "This is an intentional anti-pattern that demonstrates "
        "how blocking in async code affects all concurrent operations."
    ),
)
async def async_blocking(request: AsyncBlockRequest) -> BlockingResponse:
    """Trigger asynchronous blocking on the event loop.

    This endpoint intentionally blocks the event loop using time.sleep().
    While blocked, NO other async operations can make progress.

    Args:
        request: Request with duration and optional chunk size.

    Returns:
        Response with actual blocked duration.
    """
    chunked = request.chunk_ms is not None

    event_log_service.log_event(
        event_type="blocking_started",
        message=f"Starting async blocking for {request.duration_seconds}s",
        metadata={
            "type": "async",
            "duration": request.duration_seconds,
            "chunked": chunked,
            "chunk_ms": request.chunk_ms,
        },
    )

    if chunked and request.chunk_ms is not None:
        # Chunked blocking with yields
        blocked = await blocking_service.chunked_block(
            request.duration_seconds,
            request.chunk_ms,
        )
    else:
        # Full event loop blocking (BAD!)
        blocked = await blocking_service.async_block(request.duration_seconds)

    event_log_service.log_event(
        event_type="blocking_completed",
        message=f"Async blocking completed: {blocked:.2f}s",
        metadata={
            "type": "async",
            "blocked_duration": blocked,
            "chunked": chunked,
        },
    )

    return BlockingResponse(
        message=f"Async blocked for {blocked:.2f} seconds",
        blocked_duration=blocked,
        count=1,
        chunked=chunked,
    )


@router.post(
    "/demo-proper",
    response_model=BlockingResponse,
    summary="Demonstrate proper async blocking handling",
    description=(
        "Run blocking operation properly in thread pool. "
        "This demonstrates the correct pattern for handling blocking "
        "operations in async code - offload to a thread pool."
    ),
)
async def demo_proper_blocking(request: SyncBlockRequest) -> BlockingResponse:
    """Demonstrate proper handling of blocking operations.

    This endpoint shows the correct way to handle blocking operations
    in async code - by running them in a thread pool so the event loop
    remains free to process other requests.

    Args:
        request: Request with duration.

    Returns:
        Response with actual blocked duration.
    """
    event_log_service.log_event(
        event_type="blocking_started",
        message=f"Starting proper blocking demo for {request.duration_seconds}s",
        metadata={
            "type": "proper",
            "duration": request.duration_seconds,
        },
    )

    total_blocked = 0.0
    for _ in range(request.count):
        blocked = await blocking_service.run_sync_in_thread(request.duration_seconds)
        total_blocked += blocked

    event_log_service.log_event(
        event_type="blocking_completed",
        message=f"Proper blocking demo completed: {total_blocked:.2f}s",
        metadata={
            "type": "proper",
            "total_blocked": total_blocked,
        },
    )

    return BlockingResponse(
        message=f"Properly handled blocking for {total_blocked:.2f} seconds",
        blocked_duration=total_blocked,
        count=request.count,
        chunked=False,
    )
