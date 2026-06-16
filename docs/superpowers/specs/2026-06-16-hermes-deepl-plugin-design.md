# Hermes DeepL Plugin — Design

**Date:** 2026-06-16
**Status:** Design approved, pending spec review

## Purpose

A [Hermes Agent](https://hermes-agent.nousresearch.com) plugin that gives the
agent a DeepL-backed `translate` tool, so that whenever Hermes needs to produce
(or consume) **Hungarian** text it uses DeepL's machine translation instead of
relying on the base LLM's own translation. Hungarian is the headline use case,
but the tool is a general source→target translator.

## Background: the Hermes plugin contract

Confirmed from the official
[Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin)
guide and the bundled `plugins/disk-cleanup` and `plugins/calculator` examples:

- A plugin is a directory containing `plugin.yaml` + `__init__.py` with a
  `register(ctx)` entrypoint.
- Discovery sources: `~/.hermes/plugins/<name>/`, project-level `.hermes/plugins/`,
  or pip entry points. One level of `<category>/<name>` nesting is allowed.
- Plugins are **opt-in**: enabled via `hermes plugins enable <name>`.
- `register(ctx)` wires tools/hooks:
  - `ctx.register_tool(name=, toolset=, schema=, handler=)`
  - `ctx.register_hook(event, fn)` / `ctx.register_command(...)` (not used here)
- A tool **schema** is the OpenAI-style function schema the LLM reads
  (`{name, description, parameters}`).
- A tool **handler** has signature `def handler(args: dict, **kwargs) -> str`.
  It must **always return a JSON string** (success and error alike) and must
  **never raise** — catch everything and return error JSON.
- `plugin.yaml` `requires_env:` gates loading on env vars and prompts for them
  at install time; `secret: true` marks a value as sensitive.
- Plugins run **inside the Hermes process**, so third-party dependencies would
  have to be installed into Hermes' own venv.

## Approach decision

**Pure standard-library plugin (`urllib.request`).** No third-party dependency
(not the official `deepl` SDK, not `httpx`). Rationale: a drop-in plugin that
adds zero install friction and cannot conflict with Hermes' venv. The extra
HTTP-client code is small and fully testable.

## Scope (v1)

### Tools (toolset `deepl`)

1. **`translate`** — the core tool.

   | Param | Type | Required | Notes |
   |---|---|---|---|
   | `text` | string **or** array of strings | yes | Batch: up to 50 strings per DeepL request. |
   | `target_lang` | string | yes | DeepL code, e.g. `HU`, `EN-GB`, `DE`. Description steers the agent to use the tool whenever producing Hungarian. |
   | `source_lang` | string | no | Omit to let DeepL auto-detect. |
   | `formality` | string | no | `default`/`more`/`less`/`prefer_more`/`prefer_less`. See guard below. |
   | `preserve_formatting` | boolean | no | Pass-through to DeepL. |

   Returns:
   ```json
   {
     "translations": [
       {"text": "…", "detected_source_lang": "EN"}
     ],
     "target_lang": "HU",
     "notes": ["formality dropped: not supported for target HU"]
   }
   ```
   `notes` is omitted when empty. When `text` is a single string, the agent
   still receives a one-element `translations` array (uniform shape).

2. **`deepl_usage`** — no parameters. Returns
   `{"character_count": N, "character_limit": N, "percent_used": 0.0}` so the
   agent can check remaining quota before a large job.

### Formality guard (Hungarian)

DeepL returns a 400 error if `formality` is sent for a target language that does
not support it. Hungarian does **not** support formality. The handler keeps a
set of formality-supporting targets (`DE, FR, IT, ES, NL, PL, PT-PT, PT-BR, JA,
RU`, matched case-insensitively on the language part). For any other target the
handler **silently drops `formality`** and appends a human-readable string to
`notes`, rather than letting DeepL error. This means formality is effectively a
no-op for Hungarian, which is expected and documented.

### Out of scope for v1

- **Glossaries.** DeepL glossaries are offered only for a limited set of
  language pairs, and Hungarian is not currently among them, so a glossary tool
  cannot improve Hungarian output today. Dropped from v1; easy to add later as a
  `deepl_glossary` tool if DeepL adds Hungarian support.
- Document translation, the `/languages` endpoint, and any hook-based
  auto-rewriting of agent output.

## Configuration & secrets

- **`DEEPL_API_KEY`** — required, gated via `plugin.yaml` `requires_env`
  (`secret: true`). Read from the environment in the client.
- **`DEEPL_API_URL`** — optional override of the base URL (testing / proxies).
- **Endpoint auto-detection:** if the key ends in `:fx` → DeepL Free
  (`https://api-free.deepl.com/v2`); otherwise DeepL Pro
  (`https://api.deepl.com/v2`). Overridden by `DEEPL_API_URL` when set.
- **Auth:** header `Authorization: DeepL-Auth-Key <key>`.

## Components

| File | Responsibility | Depends on |
|---|---|---|
| `plugin.yaml` | Manifest: `name: deepl`, `provides_tools: [translate, deepl_usage]`, `requires_env: [DEEPL_API_KEY]`. | — |
| `deepl_client.py` | Stdlib HTTP client. `endpoint_for_key()`, `translate(...)`, `usage()`. Builds requests, sets auth, parses JSON, maps HTTP/network errors to a `DeepLError(status, message)`. 30s timeout. Reads no global state beyond env. | `urllib`, `os`, `json` |
| `schemas.py` | The two function schemas the LLM reads. Pure data. | — |
| `tools.py` | Handlers `translate(args, **kwargs) -> str` and `deepl_usage(args, **kwargs) -> str`. Validate inputs, apply the formality guard, call `deepl_client`, serialize results, and convert `DeepLError`/unexpected exceptions into `{error, status}` JSON. Never raise. | `deepl_client`, `schemas` |
| `__init__.py` | `register(ctx)` → two `ctx.register_tool(...)` calls. | `schemas`, `tools` |
| `README.md` | Install (`~/.hermes/plugins/`), `hermes plugins enable deepl`, set `DEEPL_API_KEY`, usage examples, the HU formality/glossary caveats. | — |
| `tests/test_deepl_plugin.py` | pytest suite, HTTP mocked. | `pytest` |

### Boundaries

- `deepl_client.py` knows DeepL's HTTP shape and **nothing** about Hermes — it
  can be unit-tested in isolation and reused outside the plugin.
- `tools.py` knows the Hermes handler contract (dict in, JSON string out, never
  raise) and the formality business rule, but delegates all HTTP to the client.
- `__init__.py` is pure wiring.

## Error handling

Handlers always return a JSON string. The client raises `DeepLError(status, msg)`
for non-2xx responses and network/timeout failures; handlers catch it and return:
```json
{"error": "DeepL quota exceeded", "status": 456}
```
Mapped statuses: `403` invalid/inactive key, `456` quota exceeded, `429`
rate-limited, `400` bad request (echo DeepL's message), `5xx` server error,
network/timeout → `status: 0`. A missing `DEEPL_API_KEY` returns
`{"error": "DEEPL_API_KEY not set", "status": 0}` (the plugin is normally gated
out by `requires_env`, but the handler is defensive).

## Testing strategy (TDD)

pytest, with the HTTP boundary monkeypatched — no live API calls, no key needed.
Cases:
- `endpoint_for_key`: `:fx` suffix → free host; otherwise → pro host;
  `DEEPL_API_URL` override wins.
- `translate`: single string → one-element `translations`; array → batch request
  body has repeated `text` fields; `detected_source_lang` surfaced.
- Formality guard: `formality` present + target `HU` → request omits formality
  and response `notes` explains; target `DE` → formality forwarded.
- `deepl_usage`: parses count/limit, computes `percent_used`.
- Error mapping: 403 / 456 / 429 / 400 / network error → correct `{error,status}`.
- Missing key → defensive error JSON, no HTTP attempted.

## Acceptance

- `hermes plugins enable deepl` then a fresh Hermes session shows
  `deepl: translate, deepl_usage` in the banner.
- Asking Hermes to translate to Hungarian routes through `translate` and returns
  DeepL output.
- `pytest` is green with the HTTP layer mocked.
