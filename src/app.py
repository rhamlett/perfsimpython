"""FastAPI application configuration and factory.

This module creates and configures the FastAPI application with
all middleware, routers, and static file serving.
"""

import asyncio
import contextlib
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from src.middleware.activity_tracker import ActivityTrackerMiddleware
from src.middleware.error_handler import error_handler_middleware
from src.middleware.request_logger import RequestLoggerMiddleware, configure_logging
from src.routers import admin, blocking, cpu, crash, health, loadtest, memory, metrics, slow
from src.services.event_log_service import event_log_service
from src.services.metrics_service import MetricsService
from src.services.request_latency_service import request_latency_service
from src.services.simulation_tracker import simulation_tracker
from src.websocket.metrics_broadcaster import ConnectionManager

logger = logging.getLogger(__name__)

# WebSocket connection manager
ws_manager = ConnectionManager()

# Background task reference
_metrics_broadcast_task: asyncio.Task | None = None

# Server instance ID - unique per process start, used to detect restarts
# This is more reliable than PID which can be the same in containers (always PID 1)
SERVER_INSTANCE_ID = str(uuid.uuid4())[:8]
SERVER_START_TIME = datetime.now(UTC)


async def _measure_event_loop_lag() -> float:
    """Measure event loop lag in milliseconds.

    Records time before yielding to the event loop and after resuming.
    The difference indicates how backed up the event loop is.
    """
    import time

    start = time.perf_counter()
    await asyncio.sleep(0)
    return (time.perf_counter() - start) * 1000  # Convert to ms


async def _broadcast_metrics() -> None:
    """Background task that broadcasts metrics to connected WebSocket clients.

    Runs every 250ms while the application is running (240 points = 60 seconds).
    Also broadcasts new event log entries since the last broadcast.
    """
    from src.services.idle_service import idle_service

    metrics_service = MetricsService()

    # Track the last time we broadcast events to avoid sending duplicates
    last_event_broadcast = datetime.now(UTC)

    while True:
        try:
            if ws_manager.active_connections:
                # Measure event loop lag
                event_loop_lag_ms = await _measure_event_loop_lag()

                # Count pending asyncio tasks
                all_tasks = asyncio.all_tasks()
                pending_tasks = len([t for t in all_tasks if not t.done()])

                # Gather system metrics
                system_metrics = metrics_service.get_system_metrics()
                process_metrics = metrics_service.get_process_metrics()

                # Clean up expired simulations and their resources
                from src.services.cpu_stress_service import cpu_stress_service
                from src.services.slow_request_service import slow_request_service

                cpu_stress_service.cleanup_finished()
                simulation_tracker.cleanup_expired()
                active_simulations = simulation_tracker.get_all_simulations()

                # Get slow request generator stats
                slow_request_stats = slow_request_service.get_stats()

                # Build message payload
                # Get recent request latencies (last 2 seconds for smooth updates)
                recent_latencies = request_latency_service.get_recent_latencies(max_age_seconds=2.0)

                # Get new events since last broadcast
                new_events = event_log_service.get_events_since(last_event_broadcast)
                last_event_broadcast = datetime.now(UTC)

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
                            "pid": os.getpid(),
                            "instance_id": SERVER_INSTANCE_ID,
                            "started_at": SERVER_START_TIME.isoformat(),
                            "cpu_percent": process_metrics.cpu_percent,
                            "memory_mb": round(process_metrics.memory_rss_bytes / (1024 * 1024), 2),
                            "threads": process_metrics.threads,
                        },
                        "asyncio": {
                            "pending_tasks": pending_tasks,
                            "event_loop_lag_ms": round(event_loop_lag_ms, 2),
                        },
                        "simulations": {
                            "active_count": len(active_simulations),
                            "items": [
                                {
                                    "id": str(sim.id),
                                    "type": sim.type.value,
                                    "started_at": sim.started_at.isoformat(),
                                    "duration_seconds": sim.duration_seconds,
                                    "elapsed_seconds": round(sim.elapsed_seconds, 1),
                                    "params": sim.params,
                                }
                                for sim in active_simulations
                            ],
                        },
                        "slowRequestGenerator": {
                            "is_running": slow_request_stats["is_running"],
                            "generated_count": slow_request_stats["generated_count"],
                            "max_requests": slow_request_stats["max_requests"],
                            "delay_seconds": slow_request_stats["delay_seconds"],
                        },
                        "idle": {
                            "is_idle": idle_service.check_idle_state(),
                            "seconds_until_idle": idle_service.get_seconds_until_idle(),
                        },
                        "requestLatencies": recent_latencies,
                        "events": [event.to_dict() for event in new_events],
                    },
                }

                await ws_manager.broadcast(message)

            # Wait 250ms before next broadcast (240 points = 60 seconds)
            await asyncio.sleep(0.25)

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
    configure_logging()
    logger.info("Performance Problem Simulator starting")

    # Log startup event with hostname
    import os

    hostname = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown"
    event_log_service.log(
        event_type="info",
        simulation_type="system",
        message=f"Application started on {hostname}",
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
    # Configure Azure Monitor / Application Insights (if connection string is set).
    # This must happen before the FastAPI app is created so the OpenTelemetry
    # instrumentor can hook into FastAPI, httpx, logging, etc.
    _conn = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if _conn:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=_conn)
            logger.info("Azure Monitor OpenTelemetry configured")
        except Exception as exc:
            logger.warning("Failed to configure Azure Monitor: %s", exc)

    # Create the FastAPI app
    app = FastAPI(
        title="Performance Problem Simulator",
        description="Educational tool for simulating performance problems to practice Azure diagnostics",
        version="1.0.0",
        docs_url="/swagger",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Register middleware (order matters - first registered = last executed)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(ActivityTrackerMiddleware)
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
    app.include_router(loadtest.router, prefix="/api", tags=["loadtest"])

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
