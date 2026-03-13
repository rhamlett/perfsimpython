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
        app_env: Application environment (development, staging, production).
        log_level: Logging verbosity level.
        host: Server host address.
        port: Server port number.
        ws_heartbeat_interval: WebSocket metrics broadcast interval in milliseconds.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application environment
    app_env: Literal["development", "staging", "production"] = "development"

    # Logging configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # WebSocket configuration
    ws_heartbeat_interval: int = 500  # milliseconds

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Returns:
        Singleton Settings instance with values loaded from environment.
    """
    return Settings()
