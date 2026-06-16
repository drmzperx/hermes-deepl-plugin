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
        return override.rstrip("/")
    if key and key.strip().endswith(":fx"):
        return FREE_URL
    return PRO_URL
