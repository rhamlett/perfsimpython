"""Translation service — Azure Translator Text API integration.

Translates UI strings (en.json → {lang}.json) and HTML documents using
Azure Cognitive Services Translator Text API. Uses hash-based caching
to skip translation when source content hasn't changed.
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import re
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Maximum elements per API batch (API limit: 1000, we use 100)
MAX_BATCH_SIZE = 100

# Maximum characters per API batch (API limit: 50,000, we leave margin)
MAX_BATCH_CHARS = 49_000

# Regex to match {placeholder} tokens
PLACEHOLDER_REGEX = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")

# Regex to strip notranslate span tags from translated output.
# Handles double quotes, single quotes, and HTML entities — all three
# appear unpredictably in real API responses.
NOTRANSLATE_SPAN_REGEX = re.compile(
    r'<span\s+class\s*=\s*(?:"|&quot;|\')notranslate(?:"|&quot;|\')>(.*?)</span>',
    re.DOTALL,
)

# Regex to split HTML into tags and text segments
HTML_TAG_REGEX = re.compile(r"(<[^>]+>)")

# Regex to detect opening no-translate elements
NO_TRANSLATE_ELEMENT_OPEN_REGEX = re.compile(r"<(code|pre|script|style|svg)[\s>]", re.IGNORECASE)

# Retry delays in seconds for 429 rate-limit responses
RETRY_DELAYS = [5, 15, 30, 60]


class TranslationService:
    """Translates UI strings and HTML documents from English to a target language."""

    def __init__(self, api_key: str, endpoint: str, region: str) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._region = region

    async def ensure_translation(self, target_language: str, locales_path: Path) -> bool:
        """Ensure a translated locale file exists for the specified language.

        Uses SHA256 hash caching to skip re-translation when source hasn't changed.
        """
        if not target_language or target_language.lower() == "en":
            return True

        en_file = locales_path / "en.json"
        target_file = locales_path / f"{target_language}.json"

        if not en_file.exists():
            logger.error("[i18n] English source file not found: %s", en_file)
            return False

        try:
            en_content = en_file.read_text(encoding="utf-8")
            source_hash = self._compute_hash(en_content)

            # Check cache
            if target_file.exists():
                try:
                    existing = json.loads(target_file.read_text(encoding="utf-8"))
                    if existing.get("_meta", {}).get("source_hash") == source_hash:
                        logger.info(
                            "[i18n] Translation for %s is up to date (hash: %s)",
                            target_language,
                            source_hash[:8],
                        )
                        return True
                    logger.info(
                        "[i18n] Translation for %s exists but source changed, re-translating",
                        target_language,
                    )
                except (json.JSONDecodeError, KeyError):
                    logger.warning(
                        "[i18n] Existing translation for %s is invalid, re-translating",
                        target_language,
                    )

            if not self._api_key:
                logger.warning(
                    "[i18n] UI_LANGUAGE is '%s' but TRANSLATOR_API_KEY is not configured.",
                    target_language,
                )
                return False

            # Parse English strings (skip _meta)
            en_doc = json.loads(en_content)
            source_strings: dict[str, str] = {
                k: v for k, v in en_doc.items() if k != "_meta" and isinstance(v, str)
            }

            if not source_strings:
                logger.warning("[i18n] No translatable strings found in en.json")
                return False

            # Load no-translate terms
            no_translate_terms = self._load_no_translate_terms(locales_path)

            logger.info(
                "[i18n] Translating %d strings to %s (%d protected terms)...",
                len(source_strings),
                target_language,
                len(no_translate_terms),
            )

            # Translate in batches
            translated: dict[str, str] = {}
            keys = list(source_strings.keys())
            i = 0

            while i < len(keys):
                batch_keys: list[str] = []
                batch_texts: list[str] = []
                batch_chars = 0

                while i < len(keys) and len(batch_keys) < MAX_BATCH_SIZE:
                    wrapped = self._wrap_no_translate_terms(
                        source_strings[keys[i]], no_translate_terms
                    )
                    if batch_chars + len(wrapped) > MAX_BATCH_CHARS and batch_keys:
                        break
                    batch_keys.append(keys[i])
                    batch_texts.append(wrapped)
                    batch_chars += len(wrapped)
                    i += 1

                translations = await self._translate_batch(batch_texts, target_language)
                if translations is None:
                    logger.error(
                        "[i18n] Translation API failed for batch starting at index %d",
                        i - len(batch_keys),
                    )
                    return False

                for j, key in enumerate(batch_keys):
                    translated[key] = self._strip_no_translate_tags(translations[j])

                # Inter-batch delay (2 seconds)
                if i < len(keys):
                    await asyncio.sleep(2)

            # Build output
            output: dict[str, object] = {
                "_meta": {
                    "source_hash": source_hash,
                    "source_lang": "en",
                    "target_lang": target_language,
                    "generated": _iso_now(),
                    "generator": "Azure Cognitive Services Translator",
                },
            }
            output.update(translated)

            target_file.write_text(
                json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info(
                "[i18n] Translation complete: %d strings written to %s",
                len(translated),
                target_file,
            )
            return True

        except Exception:
            logger.exception("[i18n] Translation failed for %s", target_language)
            return False

    async def ensure_document_translation(
        self, source_html_path: Path, target_language: str
    ) -> bool:
        """Ensure a translated HTML document exists for the specified language.

        Uses SHA256 hash caching embedded as an HTML comment on the first line.
        """
        if not target_language or target_language.lower() == "en":
            return True

        if not source_html_path.exists():
            logger.error("[i18n] HTML source file not found: %s", source_html_path)
            return False

        try:
            source_content = source_html_path.read_text(encoding="utf-8")
            source_hash = self._compute_hash(source_content)
            target_path = self._get_translated_html_path(source_html_path, target_language)
            source_name = source_html_path.name

            # Check cache
            if target_path.exists():
                first_line = target_path.read_text(encoding="utf-8").split("\n", 1)[0]
                if f"source_hash:{source_hash}" in first_line:
                    logger.info(
                        "[i18n] Document translation for %s (%s) is up to date (hash: %s)",
                        source_name,
                        target_language,
                        source_hash[:8],
                    )
                    return True
                logger.info(
                    "[i18n] Document translation for %s (%s) exists but source changed",
                    source_name,
                    target_language,
                )

            if not self._api_key:
                logger.warning(
                    "[i18n] Cannot translate %s — TRANSLATOR_API_KEY not configured.",
                    source_name,
                )
                return False

            # Load no-translate terms
            locales_path = source_html_path.parent / "locales"
            no_translate_terms = self._load_no_translate_terms(locales_path)

            # Extract translatable segments
            segments = self._extract_translatable_segments(source_content)
            translatable = [s for s in segments if s["translatable"] and s["text"].strip()]

            if not translatable:
                logger.warning("[i18n] No translatable text found in %s", source_name)
                return False

            logger.info(
                "[i18n] Translating document %s to %s: %d text segments...",
                source_name,
                target_language,
                len(translatable),
            )

            # Translate in character-aware batches
            si = 0
            batch_index = 0

            while si < len(translatable):
                batch: list[dict] = []
                batch_texts: list[str] = []
                batch_chars = 0

                while si < len(translatable) and len(batch) < MAX_BATCH_SIZE:
                    wrapped = self._wrap_no_translate_terms(
                        translatable[si]["text"], no_translate_terms
                    )
                    if batch_chars + len(wrapped) > MAX_BATCH_CHARS and batch:
                        break
                    batch.append(translatable[si])
                    batch_texts.append(wrapped)
                    batch_chars += len(wrapped)
                    si += 1

                translations = await self._translate_batch(batch_texts, target_language)
                if translations is None:
                    logger.error(
                        "[i18n] Document translation API failed for %s at batch %d",
                        source_name,
                        batch_index,
                    )
                    return False

                for j, seg in enumerate(batch):
                    seg["translated"] = self._strip_no_translate_tags(translations[j])

                batch_index += 1

                # Inter-batch delay (2 seconds)
                if si < len(translatable):
                    await asyncio.sleep(2)

            # Reassemble translated HTML
            parts: list[str] = [
                f"<!-- source_hash:{source_hash} lang:{target_language}"
                f" generated:{_iso_now()} -->\n"
            ]
            for seg in segments:
                if seg["translatable"] and seg.get("translated"):
                    parts.append(seg["translated"])
                else:
                    parts.append(seg["text"])

            target_path.write_text("".join(parts), encoding="utf-8")
            logger.info(
                "[i18n] Document translation complete: %s → %s (%d segments)",
                source_name,
                target_path.name,
                len(translatable),
            )
            return True

        except Exception:
            logger.exception("[i18n] Document translation failed for %s", source_html_path.name)
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _translate_batch(self, texts: list[str], target_language: str) -> list[str] | None:
        """Call Azure Translator API with retry on 429."""
        request_body = [{"Text": t} for t in texts]
        url = (
            f"{self._endpoint}/translate?api-version=3.0"
            f"&from=en&to={target_language}&textType=html"
        )
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Ocp-Apim-Subscription-Region": self._region,
        }

        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=request_body)

                if response.status_code == 200:
                    data = response.json()
                    return [item["translations"][0]["text"] for item in data]

                if response.status_code == 429 and attempt < len(RETRY_DELAYS):
                    delay = RETRY_DELAYS[attempt]
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        with contextlib.suppress(ValueError):
                            delay = int(retry_after)
                    logger.warning(
                        "[i18n] Rate limited (attempt %d/%d). Retrying in %ds...",
                        attempt + 1,
                        len(RETRY_DELAYS) + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.error(
                    "[i18n] Azure Translator API returned %d: %s",
                    response.status_code,
                    response.text[:500],
                )
                return None

            except Exception:
                logger.exception("[i18n] Translation API request failed")
                return None

        return None

    def _load_no_translate_terms(self, locales_path: Path) -> list[str]:
        """Load no-translate terms sorted longest-first."""
        nt_file = locales_path / "no-translate.json"
        if not nt_file.exists():
            return []
        try:
            doc = json.loads(nt_file.read_text(encoding="utf-8"))
            terms = [t for t in doc.get("terms", []) if isinstance(t, str) and t]
            terms.sort(key=len, reverse=True)
            return terms
        except Exception:
            logger.warning("[i18n] Failed to load no-translate.json")
            return []

    def _wrap_no_translate_terms(self, text: str, terms: list[str]) -> str:
        """Wrap placeholders and no-translate terms in notranslate spans."""
        # Wrap {placeholder} tokens first
        text = PLACEHOLDER_REGEX.sub(r'<span class="notranslate">\g<0></span>', text)

        for term in terms:
            escaped = re.escape(term)
            pattern = re.compile(rf"(?<![a-zA-Z]){escaped}(?![a-zA-Z])")
            text = pattern.sub(f'<span class="notranslate">{term}</span>', text)

        return text

    @staticmethod
    def _strip_no_translate_tags(text: str) -> str:
        """Strip notranslate span tags — handles all three quote styles."""
        return NOTRANSLATE_SPAN_REGEX.sub(r"\1", text)

    @staticmethod
    def _compute_hash(content: str) -> str:
        """SHA256 hash, first 16 hex chars."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _get_translated_html_path(source: Path, language: str) -> Path:
        """e.g., docs.html → docs.es.html"""
        return source.with_suffix(f".{language}{source.suffix}")

    @staticmethod
    def _extract_translatable_segments(html: str) -> list[dict]:
        """Split HTML into translatable text and non-translatable markup."""
        segments: list[dict] = []
        parts = HTML_TAG_REGEX.split(html)

        no_translate_depth: dict[str, int] = {}
        inside_no_translate = False

        for part in parts:
            if not part:
                continue

            if part.startswith("<") and part.endswith(">"):
                segments.append({"text": part, "translatable": False})
                # Update no-translate state
                open_match = NO_TRANSLATE_ELEMENT_OPEN_REGEX.search(part)
                if open_match:
                    tag = open_match.group(1).lower()
                    no_translate_depth[tag] = no_translate_depth.get(tag, 0) + 1
                elif part.startswith("</"):
                    closing = part[2:].rstrip("> ").lower()
                    if closing in no_translate_depth:
                        if no_translate_depth[closing] <= 1:
                            del no_translate_depth[closing]
                        else:
                            no_translate_depth[closing] -= 1
                inside_no_translate = any(v > 0 for v in no_translate_depth.values())
            else:
                should_translate = not inside_no_translate and bool(part.strip())
                segments.append({"text": part, "translatable": should_translate})

        return segments


def _iso_now() -> str:
    """Current UTC time in ISO 8601."""
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
