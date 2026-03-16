"""Idle monitoring service for tracking application activity.

This service tracks user activity and determines when the application
should enter idle mode to reduce unnecessary network traffic to
AppLens and Application Insights.
"""

from datetime import UTC, datetime
from threading import Lock

from src.config.settings import get_settings


class IdleService:
    """Manages application idle state based on user activity.

    Tracks the last activity timestamp and determines if the application
    should be considered idle (no health probes should be sent).

    The idle timeout is configurable via IDLE_TIMEOUT_MINUTES environment
    variable (default: 20 minutes).

    Attributes:
        _last_activity: Timestamp of last user activity.
        _is_idle: Current idle state.
        _lock: Thread lock for safe concurrent access.
    """

    def __init__(self) -> None:
        """Initialize the idle service."""
        self._last_activity: datetime = datetime.now(UTC)
        self._is_idle: bool = False
        self._lock = Lock()

    def record_activity(self, _source: str = "unknown") -> None:
        """Record user activity to reset the idle timer.

        Args:
            _source: Description of activity source (e.g., "page_load", "api_call").
        """
        settings = get_settings()

        # Skip if idle timeout is disabled
        if settings.idle_timeout_minutes <= 0:
            return

        with self._lock:
            was_idle = self._is_idle
            self._last_activity = datetime.now(UTC)

            if was_idle:
                self._is_idle = False
                # Note: Wake-up message is logged client-side in dashboard.js

    def check_idle_state(self) -> bool:
        """Check and update the idle state.

        Returns:
            True if the application is currently idle, False otherwise.
        """
        settings = get_settings()

        # If idle timeout is disabled, never go idle
        if settings.idle_timeout_minutes <= 0:
            return False

        with self._lock:
            now = datetime.now(UTC)
            idle_threshold = settings.idle_timeout_seconds
            seconds_since_activity = (now - self._last_activity).total_seconds()

            should_be_idle = seconds_since_activity >= idle_threshold

            # Update idle state (message is logged client-side in dashboard.js)
            if should_be_idle and not self._is_idle:
                self._is_idle = True

            return self._is_idle

    @property
    def is_idle(self) -> bool:
        """Get current idle state without updating it."""
        with self._lock:
            return self._is_idle

    @property
    def last_activity(self) -> datetime:
        """Get timestamp of last recorded activity."""
        with self._lock:
            return self._last_activity

    def get_seconds_until_idle(self) -> int:
        """Get seconds remaining until app goes idle.

        Returns:
            Seconds until idle, or -1 if idle timeout is disabled.
        """
        settings = get_settings()

        if settings.idle_timeout_minutes <= 0:
            return -1

        with self._lock:
            now = datetime.now(UTC)
            seconds_since_activity = (now - self._last_activity).total_seconds()
            remaining = settings.idle_timeout_seconds - seconds_since_activity
            return max(0, int(remaining))


# Singleton instance
idle_service = IdleService()
