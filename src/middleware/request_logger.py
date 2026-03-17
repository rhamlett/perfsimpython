"""Request logging middleware.

Logs incoming requests and outgoing responses for debugging
and monitoring purposes. Also tracks request latencies for
real-time dashboard display.
"""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.services.request_latency_service import request_latency_service

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware that logs HTTP requests and responses.

    Logs the following information:
    - Incoming request method and path
    - Request processing duration
    - Response status code
    - Any errors that occur

    Also tracks request latencies for all API endpoints
    to provide real-time visibility in the dashboard.

    Log levels:
    - INFO: Successful requests
    - WARNING: 4xx responses
    - ERROR: 5xx responses
    """

    # Paths to exclude from logging (high-frequency endpoints)
    EXCLUDED_FROM_LOGGING = {
        "/api/health",
        "/api/health/ping",
        "/api/metrics",
        "/ws/metrics",
    }

    # Paths to exclude from latency tracking (websocket, static files)
    EXCLUDED_FROM_LATENCY = {
        "/ws/metrics",
    }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and log details.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response from the handler.
        """
        path = request.url.path
        method = request.method

        # Check what to track
        should_log = path not in self.EXCLUDED_FROM_LOGGING
        should_track_latency = path.startswith("/api/") and path not in self.EXCLUDED_FROM_LATENCY

        # Skip entirely for non-API paths that are excluded
        if not should_log and not should_track_latency:
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Get request details for logging
        client_host = request.client.host if request.client else "unknown"

        # Log incoming request (only if not excluded)
        if should_log:
            logger.debug(
                "Request started: %s %s from %s",
                method,
                path,
                client_host,
            )

        try:
            # Process the request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = response.status_code

            # Record latency for dashboard display
            if should_track_latency:
                request_latency_service.record_request(
                    path=path,
                    method=method,
                    status_code=status_code,
                    latency_ms=duration_ms,
                )

            # Log the completed request (only if not excluded)
            if should_log:
                # Choose log level based on status code
                if status_code >= 500:
                    log_func = logger.error
                elif status_code >= 400:
                    log_func = logger.warning
                else:
                    log_func = logger.info

                log_func(
                    "%s %s - %d (%.2fms)",
                    method,
                    path,
                    status_code,
                    duration_ms,
                )

            return response

        except Exception as exc:
            # Calculate duration even for errors
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Record latency for errors too (status 500)
            if should_track_latency:
                request_latency_service.record_request(
                    path=path,
                    method=method,
                    status_code=500,
                    latency_ms=duration_ms,
                )

            # Log the error
            if should_log:
                logger.error(
                    "%s %s - ERROR (%.2fms): %s",
                    method,
                    path,
                    duration_ms,
                    str(exc),
                )

            # Re-raise to be handled by error handler middleware
            raise


def configure_logging(log_level: str = "INFO") -> None:
    """Configure the application logging.

    Args:
        log_level: The logging level to use.
    """
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
