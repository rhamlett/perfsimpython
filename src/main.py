"""Application entry point for uvicorn.

Run with: python -m src.main
Or: uvicorn src.main:app --reload
"""

import uvicorn


def main() -> None:
    """Start the uvicorn server with configured settings."""
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8080,
    )


if __name__ == "__main__":
    main()
