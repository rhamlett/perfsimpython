"""Health check endpoint router.

Provides a simple health check endpoint for monitoring and load balancers.
"""

import os
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from src.models.responses import HealthResponse
from src.services.metrics_service import metrics_service
from src.services.simulation_tracker import simulation_tracker

router = APIRouter()


class SkuResponse(BaseModel):
    """Response model for SKU endpoint."""

    sku: str
    is_azure: bool
    worker: str | None = None


class ConfigResponse(BaseModel):
    """Response model for frontend configuration."""

    latencyProbeIntervalMs: int
    buildTime: str
    idleTimeoutMinutes: int
    isIdle: bool
    secondsUntilIdle: int


@router.get("/config", response_model=ConfigResponse, tags=["health"])
async def get_config() -> ConfigResponse:
    """Get frontend configuration values.

    Returns configurable parameters that the frontend needs to know,
    such as the health probe interval, build time, and idle state.

    Returns:
        ConfigResponse with frontend configuration values.
    """
    from src import BUILD_TIME
    from src.config.settings import get_settings
    from src.services.idle_service import idle_service

    settings = get_settings()

    # Check and update idle state
    is_idle = idle_service.check_idle_state()

    return ConfigResponse(
        latencyProbeIntervalMs=settings.health_probe_rate_clamped,
        buildTime=BUILD_TIME,
        idleTimeoutMinutes=settings.idle_timeout_minutes,
        isIdle=is_idle,
        secondsUntilIdle=idle_service.get_seconds_until_idle(),
    )


class ActivityRequest(BaseModel):
    """Request model for recording activity."""

    source: str = "page_load"


class ActivityResponse(BaseModel):
    """Response model for activity recording."""

    success: bool
    wasIdle: bool
    message: str


@router.post("/activity", response_model=ActivityResponse, tags=["health"])
async def record_activity(request: ActivityRequest) -> ActivityResponse:
    """Record user activity to reset the idle timer.

    This endpoint should be called on page load to wake the application
    from idle state and reset the idle timer. It should NOT be called
    on WebSocket reconnects.

    Args:
        request: Activity source information.

    Returns:
        ActivityResponse indicating if the app was woken from idle.
    """
    from src.services.idle_service import idle_service

    was_idle = idle_service.is_idle
    idle_service.record_activity(source=request.source)

    if was_idle:
        message = "Application woken from idle state"
    else:
        message = "Activity recorded, idle timer reset"

    return ActivityResponse(success=True, wasIdle=was_idle, message=message)


class FooterResponse(BaseModel):
    """Response model for footer endpoint."""

    footer: str | None
    has_custom_footer: bool


@router.get("/footer", response_model=FooterResponse, tags=["health"])
async def get_footer() -> FooterResponse:
    """Get the custom page footer text.

    Returns the PAGE_FOOTER environment variable value if set.
    This allows customizing the footer credits displayed on the dashboard.

    Returns:
        FooterResponse with the footer text and whether it's customized.
    """
    from src.config.settings import get_settings

    settings = get_settings()
    return FooterResponse(
        footer=settings.page_footer, has_custom_footer=settings.page_footer is not None
    )


@router.get("/sku", response_model=SkuResponse, tags=["health"])
async def get_sku() -> SkuResponse:
    """Get the Azure App Service SKU or 'Local' if not on Azure.

    Detects if running on Azure App Service by checking for WEBSITE_SITE_NAME
    environment variable. If on Azure, returns the SKU from WEBSITE_SKU.

    Returns:
        SkuResponse with the SKU name and whether running on Azure.
    """
    website_site_name = os.environ.get("WEBSITE_SITE_NAME")
    is_azure = website_site_name is not None

    if is_azure:
        # WEBSITE_SKU contains values like: Free, Shared, Basic, Standard, Premium, PremiumV2, PremiumV3
        sku = os.environ.get("WEBSITE_SKU", "Unknown")
        # COMPUTERNAME (Windows) or HOSTNAME (Linux) identifies the worker instance
        worker = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME")
    else:
        sku = "Local"
        worker = None

    return SkuResponse(sku=sku, is_azure=is_azure, worker=worker)


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Check application health status.

    Returns basic health information including:
    - Status (healthy/degraded/unhealthy)
    - Current CPU and memory usage percentages
    - Number of active simulations
    - Application version

    This endpoint is designed for quick health checks by load balancers
    and monitoring systems.

    Returns:
        HealthResponse with current health status and basic metrics.
    """
    # Get current metrics
    cpu_percent = metrics_service.get_cpu_percent()
    memory = metrics_service.get_memory_info()
    active_count = simulation_tracker.count()

    # Determine health status
    # High CPU or memory could indicate degraded status
    status = "healthy"
    if cpu_percent > 90 or memory.percent > 90:
        status = "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        cpu_percent=round(cpu_percent, 2),
        memory_percent=round(memory.percent, 2),
        active_simulations=active_count,
    )
