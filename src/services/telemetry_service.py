"""Telemetry service for Application Insights correlation.

Provides simulation ID tracking and correlation with Azure Application Insights
telemetry. The simulation ID is propagated to telemetry allowing correlation
of dashboard events with server-side logs.

Note:
    Application Insights is optional — the app runs without it,
    just doesn't send telemetry. Azure App Service sets
    ``APPLICATIONINSIGHTS_CONNECTION_STRING`` automatically when App Insights
    is enabled in the portal.

    Uses ``azure-monitor-opentelemetry`` (the modern OpenTelemetry-based
    distro). Full request/dependency/exception/log telemetry is configured
    in ``app.py`` via ``configure_azure_monitor()``. This module handles
    custom simulation events only.

Example:
    Custom events appear in the ``customEvents`` table in Log Analytics
    and can be queried::

        customEvents
        | where name in ("SimulationStarted", "SimulationEnded")
        | where customDimensions["SimulationId"] == "YOUR-SIMULATION-ID"
"""

import logging
import os
from contextvars import ContextVar
from uuid import UUID

logger = logging.getLogger(__name__)

# Context variable to track current simulation ID across async operations
_current_simulation_id: ContextVar[UUID | None] = ContextVar("current_simulation_id", default=None)

# Whether Application Insights is available
_appinsights_available = False
_event_logger: logging.Logger | None = None


def _check_appinsights() -> bool:
    """Check if Application Insights is available.

    The actual Azure Monitor configuration (``configure_azure_monitor()``)
    happens in ``app.py`` at startup. This function only checks whether
    the connection string is present so that custom-event helpers know
    whether to emit log records.
    """
    global _appinsights_available, _event_logger

    conn_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_string:
        logger.debug("Application Insights not configured (no connection string)")
        return False

    # The AzureLogHandler attached by configure_azure_monitor() will
    # pick up records from any logger. We use a dedicated logger so
    # custom-event records are easy to identify.
    _event_logger = logging.getLogger("azure.appinsights.events")
    _event_logger.setLevel(logging.INFO)
    _appinsights_available = True
    logger.info("Application Insights enabled via azure-monitor-opentelemetry")
    return True


def set_current_simulation_id(simulation_id: UUID | None) -> None:
    """Set the current simulation ID for telemetry correlation.

    This sets a context variable that can be used to correlate all
    telemetry within the current async context with a specific simulation.

    Args:
        simulation_id: The simulation ID to set, or None to clear.
    """
    _current_simulation_id.set(simulation_id)


def get_current_simulation_id() -> UUID | None:
    """Get the current simulation ID if set.

    Returns:
        The current simulation ID, or None if not set.
    """
    return _current_simulation_id.get()


def track_simulation_event(
    event_name: str,
    simulation_id: UUID,
    simulation_type: str,
    properties: dict | None = None,
) -> None:
    """Track a simulation event in Application Insights.

    Sends a custom event to Application Insights with the simulation ID
    as a property for correlation in KQL queries.

    Events appear in the customEvents table in Log Analytics:

        customEvents
        | where name in ("SimulationStarted", "SimulationEnded")
        | where customDimensions["SimulationId"] == "YOUR-SIMULATION-ID"

    Args:
        event_name: Name of the event (e.g., "SimulationStarted", "SimulationEnded").
        simulation_id: The unique simulation ID.
        simulation_type: Type of simulation (e.g., "cpu_stress", "memory_pressure").
        properties: Additional properties to include in the event.
    """
    if not _appinsights_available or not _event_logger:
        logger.debug("Telemetry event not sent (App Insights not available): %s", event_name)
        return

    try:
        # Build custom dimensions
        custom_dimensions = {
            "SimulationId": str(simulation_id),
            "SimulationType": simulation_type,
            **(properties or {}),
        }

        # Log with extra containing custom_dimensions — the Azure Monitor
        # log exporter converts these into customEvents in App Insights.
        _event_logger.info(
            event_name,
            extra={"custom_dimensions": custom_dimensions},
        )

        logger.info(
            "Telemetry event sent: %s (simulation_id=%s, type=%s)",
            event_name,
            simulation_id,
            simulation_type,
        )
    except Exception as e:
        logger.warning("Failed to track telemetry event: %s", e)


def add_simulation_to_current_span(simulation_id: UUID, simulation_type: str) -> None:
    """Add simulation ID to the current OpenTelemetry span attributes.

    When a span is active, this annotates it with the simulation ID and type
    so that request telemetry in App Insights can be correlated with
    simulation events.

    Args:
        simulation_id: The simulation ID to add.
        simulation_type: Type of simulation.
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute("SimulationId", str(simulation_id))
            span.set_attribute("SimulationType", simulation_type)
    except Exception:
        pass


# Initialize on module load
_check_appinsights()
