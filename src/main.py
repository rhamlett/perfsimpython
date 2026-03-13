"""Application entry point for uvicorn.

Run with: python -m src.main
Or: uvicorn src.main:app --reload
"""

import uvicorn

from src.config.settings import get_settings


def main() -> None:
    """Start the uvicorn server with configured settings."""
    settings = get_settings()

    uvicorn.run(
        "src.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
