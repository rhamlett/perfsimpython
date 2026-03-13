"""WebSocket connection manager for real-time metrics broadcasting.

Manages WebSocket connections and broadcasts metrics updates
to all connected dashboard clients.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time dashboard updates.

    This class handles:
    - Connection/disconnection of dashboard clients
    - Broadcasting metrics to all connected clients
    - Connection health tracking

    Attributes:
        active_connections: Set of currently connected WebSocket clients.
        _lock: Async lock for thread-safe connection management.
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(
            "WebSocket connected. Total connections: %d",
            len(self.active_connections),
        )

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send data to all connected WebSocket clients.

        Failed sends (disconnected clients) are handled gracefully
        by removing the connection and continuing with others.

        Args:
            data: The data to broadcast as JSON.
        """
        if not self.active_connections:
            return

        message = json.dumps(data)
        disconnected: list[WebSocket] = []

        async with self._lock:
            connections = list(self.active_connections)

        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.debug("Failed to send to WebSocket: %s", str(e))
                disconnected.append(websocket)

        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self.active_connections.discard(ws)
            logger.info(
                "Removed %d disconnected clients. Active: %d",
                len(disconnected),
                len(self.active_connections),
            )

    async def send_personal(self, websocket: WebSocket, data: dict[str, Any]) -> bool:
        """Send data to a specific WebSocket client.

        Args:
            websocket: The target WebSocket connection.
            data: The data to send as JSON.

        Returns:
            True if send was successful, False otherwise.
        """
        try:
            await websocket.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.debug("Failed to send personal message: %s", str(e))
            self.disconnect(websocket)
            return False

    @property
    def connection_count(self) -> int:
        """Get the number of active connections.

        Returns:
            Count of currently connected clients.
        """
        return len(self.active_connections)

    def disconnect(self, websocket: WebSocket) -> None:
        """Synchronously remove a WebSocket connection from the manager.

        Use this for non-async contexts (like exception handlers).

        Args:
            websocket: The WebSocket connection to remove.
        """
        self.active_connections.discard(websocket)
        logger.info(
            "WebSocket disconnected (sync). Total connections: %d",
            len(self.active_connections),
        )

    async def disconnect_all(self) -> None:
        """Close and remove all active WebSocket connections.

        Used during application shutdown.
        """
        async with self._lock:
            connections = list(self.active_connections)
            self.active_connections.clear()

        for websocket in connections:
            try:
                await websocket.close()
            except Exception as e:
                logger.debug("Error closing WebSocket: %s", str(e))

        logger.info("Disconnected all %d WebSocket clients", len(connections))


# Global singleton instance
connection_manager = ConnectionManager()
