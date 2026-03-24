"""Telemetry service for Application Insights correlation.

Provides simulation ID tracking and correlation with Azure Application Insights
telemetry via OpenTelemetry. The simulation ID is propagated to telemetry
allowing correlation of dashboard events with server-side logs.

EDUCATIONAL NOTE: Application Insights is optional - the app runs without it,
just doesn't send telemetry. Azure App Service sets APPLICATIONINSIGHTS_CONNECTION_STRING
automatically when App Insights is enabled in the portal.
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
_tracer = None


def _check_appinsights() -> bool:
    """Check if Application Insights/OpenTelemetry is available."""
    global _appinsights_available, _tracer

    # Check for connection string
    conn_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn_string:
        logger.debug("Application Insights not configured (no connection string)")
        return False

    # Try to import OpenTelemetry
    try:
        from opentelemetry.trace import get_tracer

        _tracer = get_tracer(__name__)
        _appinsights_available = True
        logger.info("Application Insights integration enabled")
        return True
    except ImportError:
        logger.debug("OpenTelemetry not installed - Application Insights correlation disabled")
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

    Args:
        event_name: Name of the event (e.g., "SimulationStarted", "SimulationEnded").
        simulation_id: The unique simulation ID.
        simulation_type: Type of simulation (e.g., "cpu_stress", "memory_pressure").
        properties: Additional properties to include in the event.
    """
    if not _appinsights_available:
        logger.debug("Telemetry event not sent (App Insights not available): %s", event_name)
        return

    try:
        from opentelemetry import trace

        # Get current span and add simulation attributes
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.set_attribute("simulation.id", str(simulation_id))
            current_span.set_attribute("simulation.type", simulation_type)
            current_span.add_event(
                event_name,
                attributes={
                    "SimulationId": str(simulation_id),
                    "SimulationType": simulation_type,
                    **(properties or {}),
                },
            )

        logger.debug(
            "Tracked telemetry event: %s (simulation_id=%s, type=%s)",
            event_name,
            simulation_id,
            simulation_type,
        )
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
