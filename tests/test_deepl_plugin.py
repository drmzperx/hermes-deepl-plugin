"""Tests for the Hermes DeepL plugin. HTTP boundary is always mocked."""
import sys
import pathlib

# Make the repo root importable so `import deepl` resolves to the plugin package.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from deepl import deepl_client  # noqa: E402


def test_endpoint_free_key():
    assert deepl_client.endpoint_for_key("abc-123:fx") == "https://api-free.deepl.com/v2"


def test_endpoint_pro_key():
    assert deepl_client.endpoint_for_key("abc-123") == "https://api.deepl.com/v2"


def test_endpoint_override_wins():
    assert deepl_client.endpoint_for_key("abc:fx", "http://localhost:9/v2/") == "http://localhost:9/v2"


def test_deepl_error_attrs():
    err = deepl_client.DeepLError(456, "quota")
    assert err.status == 456
    assert err.message == "quota"
