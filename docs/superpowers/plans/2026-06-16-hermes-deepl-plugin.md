# Hermes DeepL Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a drop-in Hermes Agent plugin that exposes a DeepL-backed `translate` tool (Hungarian-first) plus a `deepl_usage` quota tool.

**Architecture:** Pure-stdlib Python plugin. A thin `deepl_client.py` owns all DeepL HTTP (endpoint auto-detect, auth, error mapping); `tools.py` holds the two Hermes handlers (input validation, the Hungarian formality guard, error→JSON mapping); `schemas.py` is pure tool-schema data; `__init__.py` wires schemas→handlers via `register(ctx)`. The plugin files live in a clean-named `deepl/` package subdir so relative imports work both inside Hermes (which loads the dir as a package) and under plain pytest.

**Tech Stack:** Python 3.8+ standard library only (`urllib`, `json`, `os`). pytest for tests. No third-party runtime dependencies.

## Global Constraints

- **No third-party runtime deps.** Standard library only. (pytest is test-only.)
- **Handler contract (verbatim from Hermes guide):** `def handler(args: dict, **kwargs) -> str`. Always return a JSON string (success and error alike). Never raise — catch everything, return error JSON.
- **Tool registration API:** `ctx.register_tool(name=, toolset=, schema=, handler=)`. Toolset is `deepl`.
- **Secret:** `DEEPL_API_KEY` read from the environment. Optional `DEEPL_API_URL` base-URL override.
- **Endpoint auto-detect:** key ending in `:fx` → `https://api-free.deepl.com/v2`; else `https://api.deepl.com/v2`; `DEEPL_API_URL`/`base_url` override wins.
- **Auth header:** `Authorization: DeepL-Auth-Key <key>`.
- **Formality-supporting target base languages (verbatim set):** `DE, FR, IT, ES, NL, PL, PT, JA, RU`. Any other target (including `HU`) drops `formality` with a note.
- **Error status mapping:** 403→invalid key, 456→quota exceeded, 429→rate limit, 400→bad request (echo message), 0→network error, else→generic. Missing key → `status: 0`.
- **JSON output uses `ensure_ascii=False`** so Hungarian characters are preserved literally.
- **Commits:** no Claude/Co-Authored-By footer.

**Plugin file layout (final):**
```
hermes-deepl-plugin/            # repo root (git)
├── deepl/                      # THE plugin dir — install target
│   ├── plugin.yaml
│   ├── __init__.py             # register(ctx)
│   ├── deepl_client.py         # stdlib HTTP client
│   ├── schemas.py              # tool schemas (pure data)
│   └── tools.py                # handlers
├── tests/test_deepl_plugin.py
├── docs/superpowers/...        # spec + this plan
├── README.md
└── .gitignore
```

**Test import bootstrap (every test relies on this — defined in Task 1):** the test file inserts the repo root on `sys.path` and imports the plugin as the package `deepl`, e.g. `from deepl import deepl_client, tools, schemas`.

---

### Task 1: DeepL client foundation — `DeepLError` + `endpoint_for_key`

**Files:**
- Create: `deepl/__init__.py` (empty placeholder for now — package marker; real `register` added in Task 5)
- Create: `deepl/deepl_client.py`
- Test: `tests/test_deepl_plugin.py`

**Interfaces:**
- Produces:
  - `class DeepLError(Exception)` with attributes `.status: int`, `.message: str`.
  - `endpoint_for_key(key: str, override: str | None = None) -> str` — returns base URL with no trailing slash.
  - Module constants `FREE_URL`, `PRO_URL`, `DEFAULT_TIMEOUT`.

- [ ] **Step 1: Confirm pytest is available**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest --version`
Expected: prints a pytest version. If it errors with "No module named pytest", run `python3 -m pip install --user pytest` and re-run.

- [ ] **Step 2: Write the failing test (creates the test file + import bootstrap)**

Create `tests/test_deepl_plugin.py`:

```python
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v`
Expected: collection error / ImportError — `deepl` package or `deepl_client` not found.

- [ ] **Step 4: Create the package marker and client module**

Create `deepl/__init__.py`:

```python
"""Hermes DeepL translation plugin (package marker; register() added later)."""
```

Create `deepl/deepl_client.py`:

```python
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
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
cd ~/workspace/hermes-deepl-plugin
git add deepl/__init__.py deepl/deepl_client.py tests/test_deepl_plugin.py
git commit -m "feat: DeepL client foundation (DeepLError, endpoint_for_key)"
```

---

### Task 2: DeepL client requests — `translate()` and `usage()`

**Files:**
- Modify: `deepl/deepl_client.py`
- Test: `tests/test_deepl_plugin.py`

**Interfaces:**
- Consumes: `endpoint_for_key`, `DeepLError` (Task 1).
- Produces:
  - `translate(*, key, texts: list[str], target_lang: str, source_lang=None, formality=None, preserve_formatting=None, base_url=None, timeout=DEFAULT_TIMEOUT) -> dict` — returns DeepL's parsed JSON, e.g. `{"translations": [{"detected_source_lang": "EN", "text": "..."}]}`.
  - `usage(*, key, base_url=None, timeout=DEFAULT_TIMEOUT) -> dict` — returns `{"character_count": N, "character_limit": N}`.
  - Internal HTTP boundary `_post_form(url, fields, key, timeout) -> dict` and `_get(url, key, timeout) -> dict` (tests monkeypatch these).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_deepl_plugin.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v -k "translate or usage"`
Expected: FAIL — `module 'deepl.deepl_client' has no attribute 'translate'`.

- [ ] **Step 3: Append the request functions to `deepl/deepl_client.py`**

Add at the end of `deepl/deepl_client.py`:

```python
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


def _post_form(url: str, fields: list, key: str, timeout: float) -> dict:
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v`
Expected: all passing (8 tests so far).

- [ ] **Step 5: Commit**

```bash
cd ~/workspace/hermes-deepl-plugin
git add deepl/deepl_client.py tests/test_deepl_plugin.py
git commit -m "feat: DeepL client translate() and usage() requests"
```

---

### Task 3: Tool schemas

**Files:**
- Create: `deepl/schemas.py`
- Test: `tests/test_deepl_plugin.py`

**Interfaces:**
- Produces: `TRANSLATE: dict` and `DEEPL_USAGE: dict` — OpenAI-style function schemas with keys `name`, `description`, `parameters`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_deepl_plugin.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v -k schema`
Expected: FAIL — `No module named 'deepl.schemas'`.

- [ ] **Step 3: Create `deepl/schemas.py`**

```python
"""Tool schemas — exactly what the LLM reads to decide when to call a tool."""

TRANSLATE = {
    "name": "translate",
    "description": (
        "Translate text using the DeepL machine-translation API. Use this "
        "WHENEVER you need to produce or read Hungarian (or any other) "
        "language text instead of translating it yourself — DeepL gives "
        "higher-quality Hungarian. Accepts a single string or an array of "
        "strings (batch, up to 50). Returns one translation per input."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ],
                "description": "Text to translate: a single string or an array of strings.",
            },
            "target_lang": {
                "type": "string",
                "description": (
                    "DeepL target language code, e.g. 'HU' (Hungarian), "
                    "'EN-GB', 'EN-US', 'DE'. Required."
                ),
            },
            "source_lang": {
                "type": "string",
                "description": "Optional DeepL source language code. Omit to auto-detect.",
            },
            "formality": {
                "type": "string",
                "enum": ["default", "more", "less", "prefer_more", "prefer_less"],
                "description": (
                    "Optional formality. Ignored for targets that do not "
                    "support it (including Hungarian)."
                ),
            },
            "preserve_formatting": {
                "type": "boolean",
                "description": "Optional. If true, DeepL preserves original formatting.",
            },
        },
        "required": ["text", "target_lang"],
    },
}

DEEPL_USAGE = {
    "name": "deepl_usage",
    "description": (
        "Report DeepL API character usage for the billing period "
        "(characters used, limit, and percent used). Call before large "
        "translation jobs to check remaining quota."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
    },
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v -k schema`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd ~/workspace/hermes-deepl-plugin
git add deepl/schemas.py tests/test_deepl_plugin.py
git commit -m "feat: tool schemas for translate and deepl_usage"
```

---

### Task 4: Tool handlers — `translate`, `deepl_usage`, formality guard, error mapping

**Files:**
- Create: `deepl/tools.py`
- Test: `tests/test_deepl_plugin.py`

**Interfaces:**
- Consumes: `deepl_client.translate`, `deepl_client.usage`, `deepl_client.DeepLError` (Tasks 1–2).
- Produces:
  - `translate(args: dict, **kwargs) -> str` — JSON string.
  - `deepl_usage(args: dict, **kwargs) -> str` — JSON string.
  - Module constant `FORMALITY_BASE: set[str]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_deepl_plugin.py`:

```python
import json  # noqa: E402
from deepl import tools  # noqa: E402


def _set_key(monkeypatch, value="testkey"):
    monkeypatch.setenv("DEEPL_API_KEY", value)


def test_translate_handler_single(monkeypatch):
    _set_key(monkeypatch)
    monkeypatch.setattr(
        deepl_client, "translate",
        lambda **kw: {"translations": [{"detected_source_lang": "EN", "text": "Szia"}]},
    )
    out = json.loads(tools.translate({"text": "Hello", "target_lang": "HU"}))
    assert out["translations"] == [{"text": "Szia", "detected_source_lang": "EN"}]
    assert out["target_lang"] == "HU"
    assert "notes" not in out


def test_translate_handler_drops_formality_for_hu(monkeypatch):
    _set_key(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        deepl_client, "translate",
        lambda **kw: captured.update(kw) or {"translations": []},
    )
    out = json.loads(tools.translate(
        {"text": "Hello", "target_lang": "HU", "formality": "more"}))
    assert captured["formality"] is None
    assert any("formality dropped" in n for n in out["notes"])


def test_translate_handler_keeps_formality_for_de(monkeypatch):
    _set_key(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        deepl_client, "translate",
        lambda **kw: captured.update(kw) or {"translations": []},
    )
    json.loads(tools.translate(
        {"text": "Hello", "target_lang": "DE", "formality": "more"}))
    assert captured["formality"] == "more"


def test_translate_handler_missing_key(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    out = json.loads(tools.translate({"text": "Hello", "target_lang": "HU"}))
    assert out["status"] == 0
    assert "DEEPL_API_KEY" in out["error"]


def test_translate_handler_bad_text(monkeypatch):
    _set_key(monkeypatch)
    out = json.loads(tools.translate({"text": 123, "target_lang": "HU"}))
    assert out["status"] == 0
    assert "text" in out["error"]


def test_translate_handler_maps_quota_error(monkeypatch):
    _set_key(monkeypatch)

    def boom(**kw):
        raise deepl_client.DeepLError(456, "quota")

    monkeypatch.setattr(deepl_client, "translate", boom)
    out = json.loads(tools.translate({"text": "Hello", "target_lang": "HU"}))
    assert out["status"] == 456
    assert "quota" in out["error"].lower()


def test_usage_handler(monkeypatch):
    _set_key(monkeypatch)
    monkeypatch.setattr(
        deepl_client, "usage",
        lambda **kw: {"character_count": 250000, "character_limit": 500000},
    )
    out = json.loads(tools.deepl_usage({}))
    assert out["character_count"] == 250000
    assert out["percent_used"] == 50.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v -k "handler or usage_handler"`
Expected: FAIL — `No module named 'deepl.tools'`.

- [ ] **Step 3: Create `deepl/tools.py`**

```python
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
        result = deepl_client.usage(key=key)
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
cd ~/workspace/hermes-deepl-plugin
git add deepl/tools.py tests/test_deepl_plugin.py
git commit -m "feat: translate and deepl_usage handlers with formality guard and error mapping"
```

---

### Task 5: Plugin registration + manifest

**Files:**
- Modify: `deepl/__init__.py`
- Create: `deepl/plugin.yaml`
- Test: `tests/test_deepl_plugin.py`

**Interfaces:**
- Consumes: `schemas.TRANSLATE`, `schemas.DEEPL_USAGE`, `tools.translate`, `tools.deepl_usage`.
- Produces: `register(ctx)` calling `ctx.register_tool(...)` twice.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_deepl_plugin.py`:

```python
import deepl as deepl_pkg  # noqa: E402


class _FakeCtx:
    def __init__(self):
        self.tools = []

    def register_tool(self, name, toolset, schema, handler):
        self.tools.append(
            {"name": name, "toolset": toolset, "schema": schema, "handler": handler}
        )


def test_register_wires_both_tools():
    ctx = _FakeCtx()
    deepl_pkg.register(ctx)
    names = {t["name"] for t in ctx.tools}
    assert names == {"translate", "deepl_usage"}
    for t in ctx.tools:
        assert t["toolset"] == "deepl"
        assert callable(t["handler"])
        assert t["schema"]["name"] == t["name"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v -k register`
Expected: FAIL — `module 'deepl' has no attribute 'register'`.

- [ ] **Step 3: Replace `deepl/__init__.py` with the real registration**

Overwrite `deepl/__init__.py`:

```python
"""Hermes DeepL translation plugin — registration entrypoint.

register(ctx) is called once at startup. It wires the two tool schemas to
their handlers via ctx.register_tool. If it raises, Hermes disables this
plugin but keeps running, so keep it import-light and side-effect-free.
"""
from __future__ import annotations

from . import schemas, tools


def register(ctx) -> None:
    ctx.register_tool(
        name="translate",
        toolset="deepl",
        schema=schemas.TRANSLATE,
        handler=tools.translate,
    )
    ctx.register_tool(
        name="deepl_usage",
        toolset="deepl",
        schema=schemas.DEEPL_USAGE,
        handler=tools.deepl_usage,
    )
```

Create `deepl/plugin.yaml`:

```yaml
name: deepl
version: 1.0.0
description: "DeepL machine translation for Hermes — high-quality Hungarian (and any-language) translate tool plus a usage/quota tool."
author: "fabianattila83"
provides_tools:
  - translate
  - deepl_usage
requires_env:
  - name: DEEPL_API_KEY
    description: "DeepL API authentication key (Free keys end in ':fx'). Free or Pro both work."
    url: "https://www.deepl.com/your-account/keys"
    secret: true
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/test_deepl_plugin.py -v`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
cd ~/workspace/hermes-deepl-plugin
git add deepl/__init__.py deepl/plugin.yaml tests/test_deepl_plugin.py
git commit -m "feat: register(ctx) wiring and plugin.yaml manifest"
```

---

### Task 6: README + final verification

**Files:**
- Create: `README.md`

**Interfaces:** none (documentation + final gate).

- [ ] **Step 1: Create `README.md`**

````markdown
# hermes-deepl-plugin

A [Hermes Agent](https://hermes-agent.nousresearch.com) plugin that adds a
DeepL-backed `translate` tool — for **high-quality Hungarian** translation
(and any other language pair) — plus a `deepl_usage` quota tool. Pure Python
standard library; no third-party dependencies.

## Tools

| Tool | Purpose |
|---|---|
| `translate` | Translate a string or array of strings via DeepL. Params: `text` (string or array, required), `target_lang` (e.g. `HU`, required), `source_lang` (optional, auto-detected), `formality` (optional), `preserve_formatting` (optional). |
| `deepl_usage` | Report characters used vs. the period limit, and percent used. |

## Install

The plugin directory is `deepl/`. Link (or copy) it into your Hermes plugins dir:

```bash
ln -s "$(pwd)/deepl" ~/.hermes/plugins/deepl
hermes plugins enable deepl
```

Set your DeepL key (Free keys end in `:fx`; the plugin auto-selects the Free or
Pro endpoint):

```bash
export DEEPL_API_KEY="your-key-here"
```

Start Hermes — the banner should list `deepl: translate, deepl_usage`. Verify
with `/plugins`.

## Usage

Ask Hermes naturally, e.g. *"Translate this to Hungarian: …"*. The agent calls
`translate` with `target_lang: "HU"`.

## Notes & limitations

- **Formality + Hungarian:** DeepL does not support `formality` for Hungarian
  targets, so the plugin silently drops `formality` for unsupported targets and
  adds a `note` to the response. Formality affects DE/FR/IT/ES/NL/PL/PT/JA/RU
  targets only.
- **Glossaries:** not included — DeepL glossaries do not currently support
  Hungarian language pairs.
- **Endpoint override:** set `DEEPL_API_URL` to point at a custom base URL
  (testing / proxy).

## Development

```bash
python3 -m pytest tests/ -v
```

Tests mock the HTTP boundary — no DeepL key or network needed.
````

- [ ] **Step 2: Run the full test suite one final time**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 3: Sanity-check the package imports cleanly**

Run: `cd ~/workspace/hermes-deepl-plugin && python3 -c "import sys; sys.path.insert(0,'.'); import deepl; print('register' in dir(deepl)); from deepl import tools, schemas, deepl_client; print('ok')"`
Expected: prints `True` then `ok`.

- [ ] **Step 4: Commit**

```bash
cd ~/workspace/hermes-deepl-plugin
git add README.md
git commit -m "docs: README with install, usage, and limitations"
```

---

## Self-Review

**1. Spec coverage:**
- Stdlib-only plugin → Task 1–2 (`urllib`), Global Constraints. ✓
- `translate` tool (string/batch, target_lang required, source_lang/formality/preserve_formatting) → Tasks 2–4. ✓
- `deepl_usage` tool → Tasks 2, 4. ✓
- Formality guard (drop for HU + note; HU not in supporting set) → Task 4. ✓
- Endpoint auto-detect (`:fx`) + `DEEPL_API_URL` override → Task 1 (`endpoint_for_key`). ✓
- Auth header → Task 2 (`_post_form`/`_get`). ✓
- Error mapping (403/456/429/400/0) + missing key → Task 4. ✓
- `plugin.yaml` manifest + `requires_env` secret → Task 5. ✓
- `register(ctx)` two `register_tool` calls → Task 5. ✓
- README with install/caveats → Task 6. ✓
- Tests with mocked HTTP, all spec cases → Tasks 1–5. ✓
- Glossary out of scope → omitted everywhere. ✓
- `ensure_ascii=False` for Hungarian → Task 4. ✓

**2. Placeholder scan:** No TBD/TODO/"add error handling"/"similar to Task N". All code shown in full. ✓

**3. Type consistency:** `endpoint_for_key(key, override)`, `translate(*, key, texts, target_lang, ...)`, `usage(*, key, ...)`, `DeepLError(status, message)`, handler names `translate`/`deepl_usage`, toolset `deepl`, `FORMALITY_BASE` — used identically in client, handlers, tests, and `register`. ✓

**Note on layout deviation from spec:** the spec listed plugin files at repo root; this plan nests them in a `deepl/` package subdir so relative imports (`from . import ...`) work both inside Hermes and under pytest, and so the install target is a clean `deepl` dir. Functionally identical surface.
