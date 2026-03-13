"""Global exception handler middleware.

Provides consistent JSON error responses for all unhandled exceptions.
"""

import logging
from collections.abc import Callable
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware that catches unhandled exceptions and returns structured JSON errors.

    This middleware ensures that any unhandled exception in the application
    is caught and returned as a consistent JSON error response, while also
    logging the full exception details for debugging.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        """Process the request and handle any exceptions.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response from the handler or an error response.
        """
        try:
            return await call_next(request)
        except Exception as exc:
            # Log the full exception with traceback
            logger.exception(
                "Unhandled exception for %s %s: %s",
                request.method,
                request.url.path,
                str(exc),
            )

            # Determine error details
            error_detail = str(exc) if str(exc) else type(exc).__name__

            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "detail": error_detail,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": str(request.url.path),
                },
            )


def error_handler_middleware(app: FastAPI) -> None:
    """Register the error handler middleware with the FastAPI application.

    Also registers specific exception handlers for common error types.

    Args:
        app: The FastAPI application instance.
    """
    # Add the general error handler middleware
    app.add_middleware(ErrorHandlerMiddleware)

    # Register specific exception handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions."""
        logger.warning("ValueError for %s: %s", request.url.path, str(exc))
        return JSONResponse(
            status_code=400,
            content={
                "error": "BadRequest",
                "message": "Invalid request parameters",
                "detail": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        """Handle KeyError exceptions."""
        logger.warning("KeyError for %s: %s", request.url.path, str(exc))
        return JSONResponse(
            status_code=404,
            content={
                "error": "NotFound",
                "message": f"Resource not found: {exc}",
                "detail": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
            },
        )
