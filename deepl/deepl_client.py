"""Thin DeepL HTTP client — standard library only.

Knows DeepL's wire format and nothing about Hermes. All network failures and
non-2xx responses are normalized to DeepLError(status, message).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_TIMEOUT = 30.0
FREE_URL = "https://api-free.deepl.com/v2"
PRO_URL = "https://api.deepl.com/v2"
_USER_AGENT = "hermes-deepl-plugin/1.0.0"


class DeepLError(Exception):
    """Normalized DeepL failure. status == 0 means network/transport error."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.message = message


def endpoint_for_key(key: str, override: str | None = None) -> str:
    """Pick the DeepL base URL. Override wins; else Free if key ends in ':fx'."""
    if override:
        if urllib.parse.urlparse(override).scheme not in ("http", "https"):
            raise ValueError("DEEPL_API_URL override must be an http(s) URL")
        return override.rstrip("/")
    if key and key.strip().endswith(":fx"):
        return FREE_URL
    return PRO_URL


def _read(req: urllib.request.Request, timeout: float) -> dict:
    """Execute a urllib request; parse JSON; normalize errors to DeepLError."""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = ""
        raise DeepLError(exc.code, detail or (exc.reason or "HTTP error"))
    except urllib.error.URLError as exc:
        raise DeepLError(0, str(exc.reason))
    except Exception as exc:  # pragma: no cover - defensive
        raise DeepLError(0, str(exc))


def _post_form(url: str, fields: list[tuple[str, str]], key: str, timeout: float) -> dict:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"DeepL-Auth-Key {key}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", _USER_AGENT)
    return _read(req, timeout)


def _get(url: str, key: str, timeout: float) -> dict:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"DeepL-Auth-Key {key}")
    req.add_header("User-Agent", _USER_AGENT)
    return _read(req, timeout)


def translate(*, key, texts, target_lang, source_lang=None, formality=None,
              preserve_formatting=None, base_url=None, timeout=DEFAULT_TIMEOUT) -> dict:
    """Translate one or more texts. Returns DeepL's parsed JSON response."""
    endpoint = endpoint_for_key(key, base_url)
    fields = [("target_lang", target_lang)]
    for text in texts:
        fields.append(("text", text))
    if source_lang:
        fields.append(("source_lang", source_lang))
    if formality:
        fields.append(("formality", formality))
    if preserve_formatting is not None:
        fields.append(("preserve_formatting", "1" if preserve_formatting else "0"))
    return _post_form(endpoint + "/translate", fields, key, timeout)


def usage(*, key, base_url=None, timeout=DEFAULT_TIMEOUT) -> dict:
    """Return DeepL account usage: character_count and character_limit."""
    endpoint = endpoint_for_key(key, base_url)
    return _get(endpoint + "/usage", key, timeout)
