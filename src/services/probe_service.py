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

import httpx

logger = logging.getLogger(__name__)


class ProbeService:
    """Background health probe that generates continuous HTTP traffic.

    Attributes:
        _thread: Dedicated daemon thread running the probe loop.
        _running: Flag controlling the probe loop lifetime.
        _probe_url: Resolved URL for the health probe endpoint.
        _interval_ms: Delay between probes in milliseconds.
        _probe_count: Total successful probes sent.
        _error_count: Total probe failures.
        _last_latency_ms: Latency of the most recent successful probe.
    """

    def __init__(self) -> None:
        """Initialise the probe service (does not start probing)."""
        self._thread: threading.Thread | None = None
        self._running = False
        self._probe_url: str = ""
        self._interval_ms: int = 200
        self._probe_count: int = 0
        self._error_count: int = 0
        self._last_latency_ms: float = 0

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
                    client.get(
                        self._probe_url,
                        headers={"X-Probe-Request": "true"},
                    )
                    latency_ms = (time.perf_counter() - start) * 1000

                    self._last_latency_ms = latency_ms
                    self._probe_count += 1

                except Exception as exc:
                    self._error_count += 1
                    if self._error_count % 10 == 1:
                        logger.warning(
                            "Probe error: %s (count=%d)",
                            exc,
                            self._error_count,
                        )

                time.sleep(self._interval_ms / 1000)

        logger.info("Probe loop exited")

    @property
    def last_latency_ms(self) -> float:
        """Latency of the most recent successful probe in milliseconds."""
        return self._last_latency_ms

    @property
    def probe_count(self) -> int:
        """Total number of successful probes sent."""
        return self._probe_count


probe_service = ProbeService()
