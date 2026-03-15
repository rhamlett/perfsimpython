"""Application settings with environment variable support.

Uses Pydantic Settings for configuration management with automatic
environment variable loading and validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings.

    Attributes:
        ws_heartbeat_interval: WebSocket metrics broadcast interval in milliseconds.
        health_probe_rate: Health probe interval in milliseconds (min 100ms).
        idle_timeout_minutes: Minutes of inactivity before app goes idle.
        page_footer: Custom footer text for attribution.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # WebSocket configuration
    ws_heartbeat_interval: int = 500  # milliseconds

    # Health probe configuration
    health_probe_rate: int = 200  # milliseconds (default 5 probes/sec)

    # Idle timeout configuration
    idle_timeout_minutes: int = 20  # minutes before app goes idle (0 = disabled)

    # Page footer configuration (HTML allowed)
    page_footer: str | None = None  # Custom footer text for attribution

    @property
    def health_probe_rate_clamped(self) -> int:
        """Get health probe rate clamped to minimum 100ms."""
        return max(100, self.health_probe_rate)

    @property
    def idle_timeout_seconds(self) -> int:
        """Get idle timeout in seconds (0 = disabled)."""
        return self.idle_timeout_minutes * 60


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Returns:
        Singleton Settings instance with values loaded from environment.
    """
    return Settings()
