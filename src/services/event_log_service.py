"""Event log service for recording simulation events.

This service maintains a time-ordered log of simulation events
for display in the dashboard and debugging purposes.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from uuid import UUID


@dataclass
class SimulationEvent:
    """Represents a simulation event.

    Attributes:
        timestamp: When the event occurred.
        event_type: Type of event (start, stop, error, info).
        simulation_type: Type of simulation this event relates to.
        simulation_id: ID of the related simulation.
        message: Human-readable event description.
        data: Additional event data.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_type: str = "info"
    simulation_type: str = ""
    simulation_id: str | None = None
    message: str = ""
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert event to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "simulation_type": self.simulation_type,
            "simulation_id": self.simulation_id,
            "message": self.message,
            "data": self.data,
        }


class EventLogService:
    """Manages simulation event logging with a fixed-size buffer.

    This service maintains a circular buffer of recent events,
    automatically discarding oldest events when capacity is reached.

    Attributes:
        _events: Circular buffer of events.
        _max_events: Maximum number of events to retain.
        _lock: Thread lock for safe concurrent access.
    """

    def __init__(self, max_events: int = 100) -> None:
        """Initialize the event log service.

        Args:
            max_events: Maximum number of events to retain.
        """
        self._events: deque[SimulationEvent] = deque(maxlen=max_events)
        self._max_events = max_events
        self._lock = Lock()

    def log(
        self,
        event_type: str,
        simulation_type: str,
        message: str,
        simulation_id: UUID | None = None,
        data: dict | None = None,
    ) -> SimulationEvent:
        """Log a new simulation event.

        Args:
            event_type: Type of event (start, stop, error, info).
            simulation_type: Type of simulation this event relates to.
            message: Human-readable event description.
            simulation_id: ID of the related simulation (optional).
            data: Additional event data (optional).

        Returns:
            The created event.
        """
        event = SimulationEvent(
            event_type=event_type,
            simulation_type=simulation_type,
            simulation_id=str(simulation_id) if simulation_id else None,
            message=message,
            data=data or {},
        )
        with self._lock:
            self._events.append(event)
        return event

    def log_start(
        self,
        simulation_type: str,
        simulation_id: UUID,
        message: str,
        data: dict | None = None,
    ) -> SimulationEvent:
        """Log a simulation start event.

        Args:
            simulation_type: Type of simulation being started.
            simulation_id: ID of the simulation.
            message: Description of the start event.
            data: Additional event data.

        Returns:
            The created event.
        """
        return self.log("start", simulation_type, message, simulation_id, data)

    def log_stop(
        self,
        simulation_type: str,
        simulation_id: UUID | None = None,
        message: str = "Simulation stopped",
        data: dict | None = None,
    ) -> SimulationEvent:
        """Log a simulation stop event.

        Args:
            simulation_type: Type of simulation being stopped.
            simulation_id: ID of the simulation (optional for stop-all).
            message: Description of the stop event.
            data: Additional event data.

        Returns:
            The created event.
        """
        return self.log("stop", simulation_type, message, simulation_id, data)

    def log_error(
        self,
        simulation_type: str,
        message: str,
        simulation_id: UUID | None = None,
        data: dict | None = None,
    ) -> SimulationEvent:
        """Log a simulation error event.

        Args:
            simulation_type: Type of simulation that encountered an error.
            message: Error description.
            simulation_id: ID of the simulation (optional).
            data: Additional error data.

        Returns:
            The created event.
        """
        return self.log("error", simulation_type, message, simulation_id, data)

    def log_event(
        self,
        event_type: str,
        message: str,
        metadata: dict | None = None,
    ) -> SimulationEvent:
        """Convenience method to log a simple event without simulation context.

        This is a simpler API for logging events that don't need full
        simulation tracking. Uses event_type as simulation_type for
        proper icon/color display in the dashboard.

        Args:
            event_type: Type of event (e.g., "memory_pressure", "blocking").
            message: Human-readable event description.
            metadata: Additional event data (optional).

        Returns:
            The created event.
        """
        return self.log(
            event_type=event_type,
            simulation_type=event_type,
            message=message,
            simulation_id=None,
            data=metadata,
        )

    def get_recent(self, count: int = 50) -> list[SimulationEvent]:
        """Get the most recent events.

        Args:
            count: Maximum number of events to return.

        Returns:
            List of recent events, newest first.
        """
        with self._lock:
            events = list(self._events)
        # Return newest first
        return list(reversed(events[-count:]))

    def get_by_type(self, simulation_type: str) -> list[SimulationEvent]:
        """Get all events for a specific simulation type.

        Args:
            simulation_type: Type of simulation to filter by.

        Returns:
            List of matching events, newest first.
        """
        with self._lock:
            events = [e for e in self._events if e.simulation_type == simulation_type]
        return list(reversed(events))

    def clear(self) -> int:
        """Clear all events.

        Returns:
            The number of events that were cleared.
        """
        with self._lock:
            count = len(self._events)
            self._events.clear()
            return count

    def get_events_since(self, since: datetime) -> list[SimulationEvent]:
        """Get all events since a given timestamp.

        Args:
            since: Timestamp to filter from (exclusive).

        Returns:
            List of events newer than the given timestamp, oldest first.
        """
        with self._lock:
            events = [e for e in self._events if e.timestamp > since]
        return events


# Global singleton instance
event_log_service = EventLogService()
