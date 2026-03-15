"""Activity tracking middleware.

Records API activity to prevent the application from going idle.
Load test traffic and user interactions will reset the idle timer.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class ActivityTrackerMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks API activity to reset the idle timer.

    Any API call (except health probes and static files) will count as
    activity and reset the idle timer. This ensures that:
    - Load test traffic prevents the app from going idle
    - User interactions via API keep the app awake
    - health probes don't count as activity (to allow proper idle detection)
    """

    # Paths that should NOT count as activity (health probes)
    EXCLUDED_PATHS = {
        "/api/health",
        "/api/config",
        "/api/sku",
        "/api/metrics",
        "/ws/metrics",
    }

    # Path prefixes to exclude (static files, docs)
    EXCLUDED_PREFIXES = (
        "/css/",
        "/js/",
        "/docs",
        "/redoc",
        "/openapi.json",
    )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and record activity if applicable.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            Response from the handler.
        """
        path = request.url.path

        # Skip activity recording for excluded paths
        should_record = (
            path not in self.EXCLUDED_PATHS
            and not path.startswith(self.EXCLUDED_PREFIXES)
            and not path.endswith(('.html', '.css', '.js', '.svg', '.ico', '.png', '.jpg'))
        )

        if should_record and path.startswith("/api/"):
            # Import here to avoid circular imports
            from src.services.idle_service import idle_service
            idle_service.record_activity(source=f"api:{path}")

        return await call_next(request)
