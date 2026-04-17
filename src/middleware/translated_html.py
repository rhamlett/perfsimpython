"""Translated HTML middleware — serves pre-translated HTML documents.

ASGI middleware that intercepts GET requests for known translatable HTML
files and serves the translated version if it exists on disk. For example,
a request for /docs.html when UI_LANGUAGE=es will serve docs.es.html if
it was created by the translation startup service.

Must be registered BEFORE the StaticFiles mount in app.py.
"""

import logging
from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config.settings import Settings

logger = logging.getLogger(__name__)

# HTML files that have translatable content
TRANSLATABLE_FILES = {
    "docs.html",
    "azure-diagnostics.html",
    "azure-load-testing.html",
    "azure-deployment.html",
}


class TranslatedHtmlMiddleware:
    """ASGI middleware that serves translated HTML documents when available."""

    def __init__(self, app: ASGIApp, settings: Settings, static_dir: Path) -> None:
        self.app = app
        self._language = settings.ui_language.strip().lower() if settings.ui_language else "en"
        self._static_dir = static_dir

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._language == "en":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        if request.method != "GET":
            await self.app(scope, receive, send)
            return

        # Normalize path: strip leading slash, handle root → index.html
        path = request.url.path.lstrip("/")
        if not path:
            path = "index.html"

        # Only intercept known translatable files
        filename = path.split("/")[-1] if "/" in path else path
        if filename not in TRANSLATABLE_FILES:
            await self.app(scope, receive, send)
            return

        # Check for translated version: docs.html → docs.es.html
        source = Path(filename)
        translated_name = source.with_suffix(f".{self._language}{source.suffix}").name
        translated_path = self._static_dir / translated_name

        if translated_path.exists():
            logger.debug("[i18n] Serving translated: %s → %s", filename, translated_name)
            response = FileResponse(str(translated_path), media_type="text/html")
            await response(scope, receive, send)
            return

        # No translated version — fall through to original
        await self.app(scope, receive, send)
