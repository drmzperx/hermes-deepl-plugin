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


def test_translate_single_builds_request(monkeypatch):
    captured = {}

    def fake_post(url, fields, key, timeout):
        captured["url"] = url
        captured["fields"] = fields
        captured["key"] = key
        return {"translations": [{"detected_source_lang": "EN", "text": "Szia"}]}

    monkeypatch.setattr(deepl_client, "_post_form", fake_post)
    result = deepl_client.translate(key="k:fx", texts=["Hello"], target_lang="HU")

    assert captured["url"] == "https://api-free.deepl.com/v2/translate"
    assert ("target_lang", "HU") in captured["fields"]
    assert ("text", "Hello") in captured["fields"]
    assert captured["key"] == "k:fx"
    assert result["translations"][0]["text"] == "Szia"


def test_translate_batch_repeats_text_fields(monkeypatch):
    captured = {}

    def fake_post(url, fields, key, timeout):
        captured["fields"] = fields
        return {"translations": []}

    monkeypatch.setattr(deepl_client, "_post_form", fake_post)
    deepl_client.translate(key="k", texts=["one", "two"], target_lang="HU")

    text_values = [v for (k, v) in captured["fields"] if k == "text"]
    assert text_values == ["one", "two"]


def test_translate_optional_fields(monkeypatch):
    captured = {}

    def fake_post(url, fields, key, timeout):
        captured["fields"] = fields
        return {"translations": []}

    monkeypatch.setattr(deepl_client, "_post_form", fake_post)
    deepl_client.translate(
        key="k", texts=["x"], target_lang="DE",
        source_lang="EN", formality="more", preserve_formatting=True,
    )
    fields = dict(captured["fields"])
    assert fields["source_lang"] == "EN"
    assert fields["formality"] == "more"
    assert fields["preserve_formatting"] == "1"


def test_usage_calls_get(monkeypatch):
    def fake_get(url, key, timeout):
        assert url == "https://api.deepl.com/v2/usage"
        return {"character_count": 100, "character_limit": 500000}

    monkeypatch.setattr(deepl_client, "_get", fake_get)
    result = deepl_client.usage(key="k")
    assert result["character_count"] == 100


from deepl import schemas  # noqa: E402


def test_translate_schema_shape():
    s = schemas.TRANSLATE
    assert s["name"] == "translate"
    assert "description" in s and s["description"]
    params = s["parameters"]
    assert params["type"] == "object"
    assert "target_lang" in params["required"]
    # text accepts a string OR an array of strings
    assert "oneOf" in params["properties"]["text"]


def test_usage_schema_shape():
    s = schemas.DEEPL_USAGE
    assert s["name"] == "deepl_usage"
    assert s["parameters"]["type"] == "object"
    assert s["parameters"].get("properties", {}) == {}
