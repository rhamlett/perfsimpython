"""Request latency tracking service.

Tracks HTTP request latencies for all API endpoints to provide
real-time visibility into application responsiveness during simulations.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RequestLatencyRecord:
    """A single request latency measurement.

    Attributes:
        timestamp: Unix timestamp of when the request completed.
        path: The API endpoint path.
        method: HTTP method (GET, POST, etc.).
        status_code: HTTP response status code.
        latency_ms: Request duration in milliseconds.
    """

    timestamp: float
    path: str
    method: str
    status_code: int
    latency_ms: float


@dataclass
class RequestLatencyService:
    """Service for tracking and aggregating request latencies.

    Maintains a rolling window of recent request latencies and provides
    aggregated statistics for dashboard display.

    Attributes:
        max_records: Maximum number of records to keep in history.
        _records: Deque of recent latency records.
        _lock: Thread lock for safe concurrent access.
    """

    max_records: int = 1000
    _records: deque = field(default_factory=lambda: deque(maxlen=1000))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        """Initialize the deque with the correct maxlen."""
        self._records = deque(maxlen=self.max_records)

    def record_request(
        self,
        path: str,
        method: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record a completed request's latency.

        Args:
            path: The API endpoint path.
            method: HTTP method.
            status_code: Response status code.
            latency_ms: Request duration in milliseconds.
        """
        record = RequestLatencyRecord(
            timestamp=time.time(),
            path=path,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        with self._lock:
            self._records.append(record)

    def get_recent_latencies(self, max_age_seconds: float = 5.0) -> list[dict]:
        """Get recent latency records within the specified time window.

        Args:
            max_age_seconds: Maximum age of records to return.

        Returns:
            List of latency records as dictionaries, newest first.
        """
        cutoff = time.time() - max_age_seconds
        with self._lock:
            recent = [
                {
                    "timestamp": r.timestamp,
                    "path": r.path,
                    "method": r.method,
                    "statusCode": r.status_code,
                    "latencyMs": round(r.latency_ms, 2),
                }
                for r in self._records
                if r.timestamp > cutoff
            ]
        # Return newest first
        return list(reversed(recent))

    def get_latest_latency(self) -> dict | None:
        """Get the most recent latency record.

        Returns:
            The most recent record as a dictionary, or None if no records.
        """
        with self._lock:
            if not self._records:
                return None
            r = self._records[-1]
            return {
                "timestamp": r.timestamp,
                "path": r.path,
                "method": r.method,
                "statusCode": r.status_code,
                "latencyMs": round(r.latency_ms, 2),
            }

    def get_stats(self, max_age_seconds: float = 60.0) -> dict:
        """Get aggregate statistics for recent requests.

        Args:
            max_age_seconds: Time window for statistics.

        Returns:
            Dictionary with count, min, max, avg latency statistics.
        """
        cutoff = time.time() - max_age_seconds
        with self._lock:
            recent = [r.latency_ms for r in self._records if r.timestamp > cutoff]

        if not recent:
            return {
                "count": 0,
                "minMs": 0,
                "maxMs": 0,
                "avgMs": 0,
            }

        return {
            "count": len(recent),
            "minMs": round(min(recent), 2),
            "maxMs": round(max(recent), 2),
            "avgMs": round(sum(recent) / len(recent), 2),
        }

    def clear(self) -> None:
        """Clear all recorded latencies."""
        with self._lock:
            self._records.clear()


# Global singleton instance
request_latency_service = RequestLatencyService()
