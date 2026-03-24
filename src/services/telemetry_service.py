"""Telemetry service for Application Insights correlation.

Provides simulation ID tracking and correlation with Azure Application Insights
telemetry via OpenTelemetry. The simulation ID is propagated to telemetry
allowing correlation of dashboard events with server-side logs.

EDUCATIONAL NOTE: Application Insights is optional - the app runs without it,
just doesn't send telemetry. Azure App Service sets APPLICATIONINSIGHTS_CONNECTION_STRING
automatically when App Insights is enabled in the portal.

Custom events are sent via azure-monitor-events-extension which exports to the
AppEvents table in Log Analytics (customEvents in classic App Insights).
"""

import logging
import os
from collections.abc import Callable
from contextvars import ContextVar
from uuid import UUID

logger = logging.getLogger(__name__)

# Context variable to track current simulation ID across async operations
_current_simulation_id: ContextVar[UUID | None] = ContextVar("current_simulation_id", default=None)

# Whether Application Insights is available
_appinsights_available = False
_tracer = None
_track_event_func: Callable[..., None] | None = None


def _check_appinsights() -> bool:
    """Check if Application Insights/OpenTelemetry is available.

    NOTE: Do NOT call configure_azure_monitor() here. Azure App Service
    auto-instrumentation (enabled via portal) already configures the
    OpenTelemetry pipeline. Calling it again causes conflicts.
    """
    global _appinsights_available, _tracer, _track_event_func

    # Check for connection string
    conn_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_string:
        logger.debug("Application Insights not configured (no connection string)")
        return False

    # Try to import OpenTelemetry (should be available via App Service auto-instrumentation)
    try:
        from opentelemetry.trace import get_tracer

        _tracer = get_tracer(__name__)

        # Import track_event from azure-monitor-events-extension
        # This is what sends events to AppEvents table in Log Analytics
        try:
            from azure.monitor.events.extension import track_event

            _track_event_func = track_event
            logger.info("Application Insights integration enabled with custom events support")
        except ImportError:
            logger.warning(
                "azure-monitor-events-extension not installed - "
                "custom events will not appear in AppEvents table"
            )

        _appinsights_available = True
        return True
    except ImportError as e:
        logger.debug("OpenTelemetry not available - Application Insights disabled: %s", e)
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

    Events appear in the AppEvents table (Log Analytics) or customEvents
    (classic Application Insights) and can be queried with:

        AppEvents
        | where Name in ("SimulationStarted", "SimulationEnded")
        | where Properties["SimulationId"] == "YOUR-SIMULATION-ID"

    Args:
        event_name: Name of the event (e.g., "SimulationStarted", "SimulationEnded").
        simulation_id: The unique simulation ID.
        simulation_type: Type of simulation (e.g., "cpu_stress", "memory_pressure").
        properties: Additional properties to include in the event.
    """
    if not _appinsights_available:
        logger.warning("Telemetry event NOT sent (App Insights not available): %s", event_name)
        return

    try:
        # Build event properties
        event_properties = {
            "SimulationId": str(simulation_id),
            "SimulationType": simulation_type,
            **(properties or {}),
        }

        # Send custom event using azure-monitor-events-extension
        # This writes to AppEvents table in Log Analytics
        if _track_event_func:
            _track_event_func(event_name, event_properties)
            logger.info("Telemetry event sent: %s (simulation_id=%s)", event_name, simulation_id)
        else:
            logger.warning("track_event function not available - event dropped: %s", event_name)

        # Also add to current span for trace correlation
        from opentelemetry import trace

        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("simulation.id", str(simulation_id))
            current_span.set_attribute("simulation.type", simulation_type)
    except Exception as e:
        logger.warning("Failed to track telemetry event: %s", e)


def add_simulation_to_current_span(simulation_id: UUID, simulation_type: str) -> None:
    """Add simulation ID to the current OpenTelemetry span.

    This enables correlation of HTTP requests with simulation events
    in Application Insights.

    Args:
        simulation_id: The simulation ID to add.
        simulation_type: Type of simulation.
    """
    if not _appinsights_available:
        return

    try:
        from opentelemetry import trace

        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("simulation.id", str(simulation_id))
            current_span.set_attribute("simulation.type", simulation_type)
    except Exception as e:
        logger.warning("Failed to add simulation to span: %s", e)


# Initialize on module load
_check_appinsights()
