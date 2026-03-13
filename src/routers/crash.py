"""Crash simulation API endpoints.

⚠️ WARNING: These endpoints will crash/terminate the application! ⚠️

Only use in controlled educational environments for practicing
crash diagnostics and recovery procedures.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.crash_service import CrashType, crash_service
from src.services.event_log_service import event_log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crash")


class CrashRequest(BaseModel):
    """Request to trigger a crash.

    ⚠️ WARNING: This will terminate the application! ⚠️
    """

    crash_type: str = Field(
        ...,
        description="Type of crash: 'exception', 'stackoverflow', 'oom', 'sigabrt'",
    )
    confirmed: bool = Field(
        default=False,
        description="Must be true to confirm intentional crash",
    )


class CrashTypeInfo(BaseModel):
    """Information about a crash type."""

    type: str
    description: str
    diagnostic_signature: str
    azure_tools: list[str]


class CrashTypesResponse(BaseModel):
    """Response listing all crash types."""

    crash_types: list[CrashTypeInfo]
    warning: str


class CrashTriggerResponse(BaseModel):
    """Response when crash is about to be triggered."""

    message: str
    crash_type: str
    warning: str


@router.get(
    "/types",
    response_model=CrashTypesResponse,
    summary="List crash types",
    description="Get information about available crash types and their diagnostic signatures",
)
async def list_crash_types() -> CrashTypesResponse:
    """List all available crash types with diagnostic information.

    Returns:
        List of crash types with descriptions and Azure tools.
    """
    crash_types = crash_service.get_all_crash_types()

    return CrashTypesResponse(
        crash_types=[
            CrashTypeInfo(
                type=ct["type"],
                description=ct["description"],
                diagnostic_signature=ct["diagnostic_signature"],
                azure_tools=ct["azure_tools"],
            )
            for ct in crash_types
        ],
        warning="⚠️ Triggering any crash type will terminate the application!",
    )


@router.post(
    "",
    response_model=CrashTriggerResponse,
    summary="Trigger crash",
    description="⚠️ WARNING: Triggers application crash! Requires confirmation.",
)
async def trigger_crash(request: CrashRequest) -> CrashTriggerResponse:
    """Trigger the specified crash type.

    ⚠️ WARNING: This will terminate the application! ⚠️

    Args:
        request: Crash request with type and confirmation.

    Returns:
        Response confirming crash will be triggered.

    Raises:
        HTTPException: If not confirmed or invalid crash type.
    """
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Crash not confirmed. Set 'confirmed: true' to intentionally "
                "crash the application. ⚠️ THIS WILL TERMINATE THE PROCESS! ⚠️"
            ),
        )

    if not crash_service.validate_crash_type(request.crash_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid crash type '{request.crash_type}'. "
            f"Valid types: {[ct.value for ct in CrashType]}",
        )

    crash_type = CrashType(request.crash_type)

    # Log the crash event before triggering
    logger.warning(
        "⚠️ CRASH REQUESTED ⚠️ Type: %s - Application will terminate!",
        crash_type.value,
    )

    event_log_service.log_event(
        event_type="crash_triggered",
        message=f"Crash triggered: {crash_type.value}",
        metadata={"crash_type": crash_type.value},
    )

    # For exception type, we can respond before crashing
    # For other types, this response may not be sent
    if crash_type == CrashType.EXCEPTION:
        # Trigger after sending response
        crash_service.trigger_crash(crash_type)
        # This line won't be reached for exception type
        return CrashTriggerResponse(
            message="Crash triggered",
            crash_type=crash_type.value,
            warning="Application should have crashed",
        )
    else:
        # For OOM, SIGABRT, stackoverflow - response may not be sent
        crash_service.trigger_crash(crash_type)
        return CrashTriggerResponse(
            message="Crash triggered",
            crash_type=crash_type.value,
            warning="Application should have crashed",
        )


@router.get(
    "/info/{crash_type}",
    response_model=CrashTypeInfo,
    summary="Get crash type info",
    description="Get detailed information about a specific crash type",
)
async def get_crash_info(crash_type: str) -> CrashTypeInfo:
    """Get information about a specific crash type.

    Args:
        crash_type: The crash type to get info for.

    Returns:
        Crash type information.

    Raises:
        HTTPException: If invalid crash type.
    """
    if not crash_service.validate_crash_type(crash_type):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown crash type '{crash_type}'. "
            f"Valid types: {[ct.value for ct in CrashType]}",
        )

    info = crash_service.get_crash_info(CrashType(crash_type))

    return CrashTypeInfo(
        type=info["type"],
        description=info["description"],
        diagnostic_signature=info["diagnostic_signature"],
        azure_tools=info["azure_tools"],
    )
