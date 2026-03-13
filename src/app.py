"""FastAPI application configuration and factory.

This module creates and configures the FastAPI application with
all middleware, routers, and static file serving.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from src.config.settings import get_settings
from src.middleware.error_handler import error_handler_middleware
from src.middleware.request_logger import RequestLoggerMiddleware, configure_logging
from src.routers import admin, blocking, cpu, crash, health, memory, metrics, slow
from src.services.metrics_service import MetricsService
from src.services.simulation_tracker import SimulationTracker
from src.websocket.metrics_broadcaster import ConnectionManager

logger = logging.getLogger(__name__)

# WebSocket connection manager
ws_manager = ConnectionManager()

# Background task reference
_metrics_broadcast_task: asyncio.Task | None = None


async def _broadcast_metrics() -> None:
    """Background task that broadcasts metrics to connected WebSocket clients.

    Runs every 500ms while the application is running.
    """
    metrics_service = MetricsService()
    simulation_tracker = SimulationTracker()

    while True:
        try:
            if ws_manager.active_connections:
                # Gather system metrics
                system_metrics = metrics_service.get_system_metrics()
                process_metrics = metrics_service.get_process_metrics()
                active_simulations = simulation_tracker.get_all_simulations()

                # Build message payload
                message = {
                    "type": "metrics",
                    "data": {
                        "system": {
                            "cpu_percent": system_metrics.cpu_percent,
                            "memory_percent": system_metrics.memory_percent,
                            "memory_available_mb": round(
                                system_metrics.memory_available_bytes / (1024 * 1024), 2
                            ),
                            "memory_total_mb": round(
                                system_metrics.memory_total_bytes / (1024 * 1024), 2
                            ),
                        },
                        "process": {
                            "cpu_percent": process_metrics.cpu_percent,
                            "memory_mb": round(process_metrics.memory_rss_bytes / (1024 * 1024), 2),
                            "threads": process_metrics.threads,
                        },
                        "simulations": {
                            "active_count": len(active_simulations),
                            "items": [
                                {
                                    "id": str(sim.id),
                                    "type": sim.type.value,
                                    "started_at": sim.started_at.isoformat(),
                                    "params": sim.params,
                                }
                                for sim in active_simulations
                            ],
                        },
                    },
                }

                await ws_manager.broadcast(message)

            # Wait 500ms before next broadcast
            await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Metrics broadcast task cancelled")
            break
        except Exception as e:
            logger.error("Error broadcasting metrics: %s", e)
            await asyncio.sleep(1)  # Wait longer on error


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan event handler.

    Handles startup and shutdown events for the application.

    Args:
        _app: The FastAPI application instance (unused but required by FastAPI).

    Yields:
        None during the application lifetime.
    """
    # Startup
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Performance Problem Simulator starting in %s mode",
        settings.app_env,
    )

    # Start background metrics broadcast task
    global _metrics_broadcast_task
    _metrics_broadcast_task = asyncio.create_task(_broadcast_metrics())
    logger.info("Started metrics broadcast task")

    yield

    # Shutdown
    logger.info("Performance Problem Simulator shutting down")

    # Cancel the metrics broadcast task
    if _metrics_broadcast_task:
        _metrics_broadcast_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _metrics_broadcast_task
        logger.info("Stopped metrics broadcast task")

    # Close all WebSocket connections
    await ws_manager.disconnect_all()

    # Clean up any running simulations
    from src.services.cpu_stress_service import cpu_stress_service
    from src.services.memory_pressure_service import memory_pressure_service

    cpu_stress_service.stop_all()
    memory_pressure_service.release_all()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    # Create the FastAPI app
    app = FastAPI(
        title="Performance Problem Simulator",
        description="Educational tool for simulating performance problems to practice Azure diagnostics",
        version="1.0.0",
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
        openapi_url="/api/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Register middleware (order matters - first registered = last executed)
    app.add_middleware(RequestLoggerMiddleware)
    error_handler_middleware(app)

    # Register routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(metrics.router, prefix="/api", tags=["metrics"])
    app.include_router(cpu.router, prefix="/api", tags=["cpu"])
    app.include_router(memory.router, prefix="/api", tags=["memory"])
    app.include_router(blocking.router, prefix="/api", tags=["blocking"])
    app.include_router(slow.router, prefix="/api", tags=["slow"])
    app.include_router(crash.router, prefix="/api", tags=["crash"])
    app.include_router(admin.router, prefix="/api", tags=["admin"])
    app.include_router(admin.failed_requests_router, prefix="/api", tags=["failed-requests"])

    # WebSocket endpoint for real-time metrics
    @app.websocket("/ws/metrics")
    async def websocket_metrics(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time metrics streaming.

        Clients connect to receive periodic metrics updates.
        """
        await ws_manager.connect(websocket)
        try:
            while True:
                # Keep connection alive, receive any messages (for ping/pong)
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception as e:
            logger.error("WebSocket error: %s", e)
            ws_manager.disconnect(websocket)

    # Mount static files if directory exists
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


# Create the application instance
app = create_app()
