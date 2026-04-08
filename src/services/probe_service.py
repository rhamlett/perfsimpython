"""Server-side health probe service.

Runs a background thread that makes real HTTP requests to the app's
own health endpoint at a configurable interval.  This ensures
Application Insights and AppLens see continuous health probe traffic
regardless of whether a browser has the dashboard open.

The probe pauses automatically when the application enters idle state
and resumes when activity is recorded.

Probe URL selection:
    - Azure App Service: ``https://{WEBSITE_HOSTNAME}/api/health/ping``
      (routes through the Azure frontend so AppLens sees the traffic)
    - Azure Container Apps: ``https://{CONTAINER_APP_HOSTNAME}/api/health/ping``
    - Local development: ``http://localhost:{PORT}/api/health/ping``
"""

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Default and slow-request probe intervals (milliseconds).
_SLOW_REQUEST_INTERVAL_MS = 5000


@dataclass
class ProbeResult:
    """A single health probe measurement.

    Attributes:
        timestamp: Unix timestamp (seconds) when the probe was sent.
        latency_ms: Round-trip response time in milliseconds.
        success: Whether the probe received a successful response.
        error: Error message if the probe failed (empty string on success).
    """

    timestamp: float
    latency_ms: float
    success: bool
    error: str = ""


class ProbeService:
    """Background health probe that generates continuous HTTP traffic.

    Probe results are stored in a thread-safe buffer so the WebSocket
    broadcast loop can include them in its periodic messages.  The
    dashboard consumes these results — it does not send its own HTTP
    probes.

    Attributes:
        _thread: Dedicated daemon thread running the probe loop.
        _running: Flag controlling the probe loop lifetime.
        _probe_url: Resolved URL for the health probe endpoint.
        _interval_ms: Current delay between probes in milliseconds.
        _normal_interval_ms: Probe interval outside of slow-request mode.
        _probe_count: Total successful probes sent.
        _error_count: Total probe failures.
        _last_latency_ms: Latency of the most recent successful probe.
        _results_buffer: Thread-safe deque of recent ProbeResults.
        _results_lock: Lock protecting the results buffer.
    """

    def __init__(self) -> None:
        """Initialise the probe service (does not start probing)."""
        self._thread: threading.Thread | None = None
        self._running = False
        self._probe_url: str = ""
        self._interval_ms: int = 200
        self._normal_interval_ms: int = 200
        self._probe_count: int = 0
        self._error_count: int = 0
        self._last_latency_ms: float = 0
        self._results_buffer: deque[ProbeResult] = deque(maxlen=200)
        self._results_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, port: int = 8080) -> None:
        """Start the probe loop in a dedicated background thread.

        Args:
            port: Fallback port for local development (overridden by
                  the ``PORT`` environment variable when present).
        """
        if self._running:
            return

        from src.config.settings import get_settings

        settings = get_settings()
        self._interval_ms = settings.health_probe_rate_clamped
        self._normal_interval_ms = self._interval_ms

        # Determine probe URL — Azure fronts produce AppLens-visible traffic.
        hostname = os.environ.get("WEBSITE_HOSTNAME")
        container_hostname = os.environ.get("CONTAINER_APP_HOSTNAME")

        if hostname:
            self._probe_url = f"https://{hostname}/api/health/ping"
        elif container_hostname:
            self._probe_url = f"https://{container_hostname}/api/health/ping"
        else:
            actual_port = int(os.environ.get("PORT", str(port)))
            self._probe_url = f"http://localhost:{actual_port}/api/health/ping"

        logger.info(
            "Probe URL: %s (interval: %dms)",
            self._probe_url,
            self._interval_ms,
        )

        self._running = True
        self._thread = threading.Thread(
            target=self._probe_loop,
            name="probe-service",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the probe loop and wait for the thread to exit."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Probe service stopped")

    # ------------------------------------------------------------------
    # Slow-request mode
    # ------------------------------------------------------------------

    def set_slow_request_mode(self, enabled: bool) -> None:
        """Switch between normal and slow-request probe intervals.

        During slow-request simulations the probe rate is reduced to
        avoid contention with the deliberately slow traffic.

        Args:
            enabled: ``True`` to slow probes to 5 s, ``False`` to restore.
        """
        if enabled:
            self._interval_ms = _SLOW_REQUEST_INTERVAL_MS
        else:
            self._interval_ms = self._normal_interval_ms
        logger.info("Probe interval changed to %dms", self._interval_ms)

    # ------------------------------------------------------------------
    # Result retrieval (called from the async broadcast loop)
    # ------------------------------------------------------------------

    def drain_results(self) -> list[dict]:
        """Return and clear all buffered probe results.

        Returns a list of dicts suitable for JSON serialisation in the
        WebSocket broadcast message.
        """
        with self._results_lock:
            results = [
                {
                    "timestamp": r.timestamp,
                    "latencyMs": round(r.latency_ms, 2),
                    "success": r.success,
                    "error": r.error,
                }
                for r in self._results_buffer
            ]
            self._results_buffer.clear()
        return results

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def _probe_loop(self) -> None:
        """Background loop that sends probes on a fixed interval.

        Runs in a dedicated OS thread (not the asyncio event loop) so
        it can detect event-loop blocking just like the .NET sister app.
        """
        from src.services.idle_service import idle_service

        # Wait for the server to finish starting up.
        time.sleep(5)

        logger.info("Probe service started")

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            while self._running:
                try:
                    # Skip probing while the app is idle.
                    if idle_service.is_idle:
                        time.sleep(1)
                        continue

                    start = time.perf_counter()
                    resp = client.get(
                        self._probe_url,
                        headers={"X-Probe-Request": "true"},
                    )
                    latency_ms = (time.perf_counter() - start) * 1000

                    self._last_latency_ms = latency_ms
                    self._probe_count += 1

                    result = ProbeResult(
                        timestamp=time.time(),
                        latency_ms=latency_ms,
                        success=resp.is_success,
                        error="" if resp.is_success else f"HTTP {resp.status_code}",
                    )

                except Exception as exc:
                    latency_ms = (time.perf_counter() - start) * 1000
                    self._error_count += 1
                    if self._error_count % 10 == 1:
                        logger.warning(
                            "Probe error: %s (count=%d)",
                            exc,
                            self._error_count,
                        )
                    result = ProbeResult(
                        timestamp=time.time(),
                        latency_ms=latency_ms,
                        success=False,
                        error=str(exc),
                    )

                with self._results_lock:
                    self._results_buffer.append(result)

                time.sleep(self._interval_ms / 1000)

        logger.info("Probe loop exited")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_latency_ms(self) -> float:
        """Latency of the most recent successful probe in milliseconds."""
        return self._last_latency_ms

    @property
    def probe_count(self) -> int:
        """Total number of successful probes sent."""
        return self._probe_count


probe_service = ProbeService()
