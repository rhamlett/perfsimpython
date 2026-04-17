"""Application settings with environment variable support.

Uses Pydantic Settings for configuration management with automatic
environment variable loading and validation.
"""

from functools import lru_cache

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

    # GitHub repository configuration (optional - link hidden if not set)
    github_repo_name: str | None = None  # Repository name (e.g., "perfsimpython")
    github_user_name: str | None = None  # GitHub user or organization name

    # i18n / Translation configuration
    ui_language: str = "en"  # ISO 639-1 language code (e.g., "es", "fr", "zh")
    translator_api_key: str | None = None  # Azure Translator API key
    translator_endpoint: str = "https://api.cognitive.microsofttranslator.com"
    translator_region: str = "eastus"  # Azure region of Translator resource

    @property
    def health_probe_rate_clamped(self) -> int:
        """Get health probe rate clamped to minimum 100ms."""
        return max(100, self.health_probe_rate)

    @property
    def idle_timeout_seconds(self) -> int:
        """Get idle timeout in seconds (0 = disabled)."""
        return self.idle_timeout_minutes * 60

    @property
    def github_url(self) -> str | None:
        """Get constructed GitHub URL if both repo and user are configured."""
        if self.github_repo_name and self.github_user_name:
            return f"https://github.com/{self.github_user_name}/{self.github_repo_name}"
        return None


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Returns:
        Singleton Settings instance with values loaded from environment.
    """
    return Settings()
