"""Request logging middleware.

Logs incoming requests and outgoing responses for debugging
and monitoring purposes.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware that logs HTTP requests and responses.

    Logs the following information:
    - Incoming request method and path
    - Request processing duration
    - Response status code
    - Any errors that occur

    Log levels:
    - INFO: Successful requests
    - WARNING: 4xx responses
    - ERROR: 5xx responses
    """

    # Paths to exclude from logging (high-frequency endpoints)
    EXCLUDED_PATHS = {
        "/api/health",
        "/api/metrics",
        "/ws/metrics",
    }

    async def dispatch(self, request: Request, call_next: Callable):
        """Process the request and log details.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response from the handler.
        """
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Get request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        # Log incoming request
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

            # Choose log level based on status code
            if status_code >= 500:
                log_func = logger.error
            elif status_code >= 400:
                log_func = logger.warning
            else:
                log_func = logger.info

            # Log the completed request
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

            # Log the error
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
