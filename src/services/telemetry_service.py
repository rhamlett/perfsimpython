"""Telemetry service for Application Insights correlation.

Provides simulation ID tracking and correlation with Azure Application Insights
telemetry. The simulation ID is propagated to telemetry allowing correlation
of dashboard events with server-side logs.

Note:
    Application Insights is optional — the app runs without it,
    just doesn't send telemetry. Azure App Service sets
    ``APPLICATIONINSIGHTS_CONNECTION_STRING`` automatically when App Insights
    is enabled in the portal.

    Uses opencensus-ext-azure (classic SDK) like the Java and Node.js
    implementations. This avoids conflicts with App Service's
    auto-instrumentation.

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
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Context variable to track current simulation ID across async operations
_current_simulation_id: ContextVar[UUID | None] = ContextVar("current_simulation_id", default=None)

# Whether Application Insights is available
_appinsights_available = False
_azure_exporter: Any = None


def _check_appinsights() -> bool:
    """Check if Application Insights is available and initialize the exporter.

    Uses opencensus-ext-azure (classic SDK) which works alongside App Service
    auto-instrumentation without conflicts.
    """
    global _appinsights_available, _azure_exporter

    # Check for connection string
    conn_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_string:
        logger.debug("Application Insights not configured (no connection string)")
        return False

    # Try to import and configure opencensus Azure exporter
    try:
        from opencensus.ext.azure.log_exporter import AzureEventHandler

        # Create an event handler for custom events
        _azure_exporter = AzureEventHandler(connection_string=conn_string)
        _appinsights_available = True
        logger.info("Application Insights enabled via opencensus (classic SDK)")
        return True
    except ImportError as e:
        logger.debug("opencensus-ext-azure not installed - Application Insights disabled: %s", e)
        return False
    except Exception as e:
        logger.warning("Failed to initialize Application Insights: %s", e)
        return False


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
    if not _appinsights_available or not _azure_exporter:
        logger.debug("Telemetry event not sent (App Insights not available): %s", event_name)
        return

    try:
        # Build custom dimensions
        custom_dimensions = {
            "SimulationId": str(simulation_id),
            "SimulationType": simulation_type,
            **(properties or {}),
        }

        # Create a log record that will be exported as a custom event
        # The AzureEventHandler exports log records with custom_dimensions as customEvents
        event_logger = logging.getLogger("azure.appinsights.events")
        event_logger.addHandler(_azure_exporter)
        event_logger.setLevel(logging.INFO)

        # Log with extra containing custom_dimensions - this becomes a customEvent
        event_logger.info(
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


def add_simulation_to_current_span(_simulation_id: UUID, _simulation_type: str) -> None:
    """Add simulation ID to span attributes (no-op with classic SDK).

    This method exists for API compatibility. The classic opencensus SDK
    doesn't use OpenTelemetry spans in the same way.

    Args:
        _simulation_id: The simulation ID to add.
        _simulation_type: Type of simulation.
    """
    # No-op - classic SDK doesn't have span correlation like OpenTelemetry
    pass


# Initialize on module load
_check_appinsights()
