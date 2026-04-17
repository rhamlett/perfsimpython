"""Translation startup service — runs at app startup.

Translates UI strings and HTML documents from English to the configured
target language. Called in the FastAPI lifespan BEFORE probe and metrics
services start.
"""

import asyncio
import logging
import re
from pathlib import Path

from src.config.settings import Settings
from src.services.translation_service import TranslationService

logger = logging.getLogger(__name__)

# HTML documents to translate (relative to static directory)
TRANSLATABLE_HTML_DOCS = [
    "docs.html",
    "azure-diagnostics.html",
    "azure-load-testing.html",
    "azure-deployment.html",
]

# Delay between document translations (seconds) to avoid API rate limits
INTER_DOCUMENT_DELAY = 10

# ISO 639-1 language code validation
LANGUAGE_CODE_REGEX = re.compile(r"^[a-z]{2,3}(-[a-zA-Z]{2,4})?$")


async def run_startup_translation(settings: Settings) -> None:
    """Run translation at app startup.

    Phase 1: Translate UI strings (en.json → {lang}.json)
    Phase 2: Translate HTML documents with delay between each
    """
    language = settings.ui_language.strip().lower() if settings.ui_language else "en"

    if language == "en":
        logger.info("[i18n] UI language is English — no translation needed")
        return

    if not LANGUAGE_CODE_REGEX.match(language):
        logger.error(
            "[i18n] Invalid language code '%s' — must be 2-3 letter ISO code. Falling back to English.",
            language,
        )
        return

    if not settings.translator_api_key:
        logger.warning(
            "[i18n] UI_LANGUAGE is '%s' but TRANSLATOR_API_KEY is not set. "
            "UI will display English.",
            language,
        )
        return

    translation_service = TranslationService(
        api_key=settings.translator_api_key,
        endpoint=settings.translator_endpoint,
        region=settings.translator_region,
    )

    static_dir = Path(__file__).resolve().parent.parent / "static"
    locales_path = static_dir / "locales"

    # Phase 1: Translate UI strings
    logger.info("[i18n] Phase 1: Translating UI strings to '%s'...", language)
    success = await translation_service.ensure_translation(language, locales_path)
    if not success:
        logger.error("[i18n] Phase 1 failed — UI will display English")
        return

    # Phase 2: Translate HTML documents
    logger.info("[i18n] Phase 2: Translating HTML documents to '%s'...", language)
    for i, doc_name in enumerate(TRANSLATABLE_HTML_DOCS):
        source_path = static_dir / doc_name
        if not source_path.exists():
            logger.warning("[i18n] Skipping missing document: %s", doc_name)
            continue

        doc_success = await translation_service.ensure_document_translation(source_path, language)
        if not doc_success:
            logger.warning(
                "[i18n] Failed to translate %s — English version will be served", doc_name
            )

        # Delay between documents (but not after the last one)
        if i < len(TRANSLATABLE_HTML_DOCS) - 1:
            logger.info("[i18n] Waiting %ds before next document...", INTER_DOCUMENT_DELAY)
            await asyncio.sleep(INTER_DOCUMENT_DELAY)

    logger.info("[i18n] Startup translation complete for '%s'", language)
