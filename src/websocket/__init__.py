"""WebSocket package for Performance Problem Simulator.

Contains WebSocket connection management for real-time updates.
"""

from src.websocket.metrics_broadcaster import ConnectionManager, connection_manager

__all__ = ["ConnectionManager", "connection_manager"]
