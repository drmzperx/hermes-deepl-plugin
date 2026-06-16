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
