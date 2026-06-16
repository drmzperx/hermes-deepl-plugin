"""Hermes tool handlers for the DeepL plugin.

Contract: each handler takes (args: dict, **kwargs) and returns a JSON string.
Handlers never raise — every failure becomes {"error": ..., "status": ...}.
"""
from __future__ import annotations

import json
import os

from . import deepl_client

# Target base languages for which DeepL supports the `formality` parameter.
FORMALITY_BASE = {"DE", "FR", "IT", "ES", "NL", "PL", "PT", "JA", "RU"}


def _key() -> str:
    return os.environ.get("DEEPL_API_KEY", "").strip()


def _err(status: int, message: str) -> str:
    return json.dumps({"error": message, "status": status})


def _map_deepl_error(exc: "deepl_client.DeepLError") -> str:
    status = exc.status
    if status == 403:
        message = "Invalid or inactive DeepL API key"
    elif status == 456:
        message = "DeepL quota exceeded"
    elif status == 429:
        message = "DeepL rate limit exceeded; retry later"
    elif status == 400:
        message = f"Bad request: {exc.message}"
    elif status == 0:
        message = f"Network error: {exc.message}"
    else:
        message = f"DeepL error ({status}): {exc.message}"
    return _err(status, message)


def translate(args: dict, **kwargs) -> str:
    try:
        text = args.get("text")
        if isinstance(text, str):
            texts = [text]
        elif isinstance(text, list) and text and all(isinstance(t, str) for t in text):
            texts = text
        else:
            return _err(0, "`text` must be a non-empty string or array of strings")

        target_lang = (args.get("target_lang") or "").strip()
        if not target_lang:
            return _err(0, "`target_lang` is required (e.g. 'HU')")

        key = _key()
        if not key:
            return _err(0, "DEEPL_API_KEY not set")

        notes = []
        formality = args.get("formality") or None
        if formality:
            base = target_lang.upper().split("-")[0]
            if base not in FORMALITY_BASE:
                notes.append(
                    f"formality dropped: not supported for target {target_lang}"
                )
                formality = None

        result = deepl_client.translate(
            key=key,
            texts=texts,
            target_lang=target_lang,
            source_lang=(args.get("source_lang") or None),
            formality=formality,
            preserve_formatting=args.get("preserve_formatting"),
            base_url=(os.environ.get("DEEPL_API_URL") or None),
        )

        translations = [
            {
                "text": t.get("text", ""),
                "detected_source_lang": t.get("detected_source_lang", ""),
            }
            for t in result.get("translations", [])
        ]
        out = {"translations": translations, "target_lang": target_lang}
        if notes:
            out["notes"] = notes
        return json.dumps(out, ensure_ascii=False)
    except deepl_client.DeepLError as exc:
        return _map_deepl_error(exc)
    except Exception as exc:  # never raise out of a handler
        return _err(0, f"Unexpected error: {exc}")


def deepl_usage(args: dict, **kwargs) -> str:
    try:
        key = _key()
        if not key:
            return _err(0, "DEEPL_API_KEY not set")
        result = deepl_client.usage(key=key, base_url=(os.environ.get("DEEPL_API_URL") or None))
        count = int(result.get("character_count", 0))
        limit = int(result.get("character_limit", 0))
        percent = round(100.0 * count / limit, 2) if limit else 0.0
        return json.dumps(
            {"character_count": count, "character_limit": limit, "percent_used": percent}
        )
    except deepl_client.DeepLError as exc:
        return _map_deepl_error(exc)
    except Exception as exc:
        return _err(0, f"Unexpected error: {exc}")
