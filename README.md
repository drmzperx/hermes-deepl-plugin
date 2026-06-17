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

The plugin directory is `deepl/`. Symlink **it** into your Hermes plugins dir
using an **absolute** path, then enable it:

```bash
# run from the repo root:
ln -sfn "$(pwd)/deepl" ~/.hermes/plugins/deepl
hermes plugins enable deepl
```

> ⚠️ **The symlink target must be an absolute path.** `ln -s` resolves a
> *relative* target from the **link's own directory** (`~/.hermes/plugins/`),
> not from your current directory — so `ln -s deepl …` or
> `ln -s workspace/hermes-deepl-plugin/deepl …` creates a **dangling** link, and
> `hermes plugins enable deepl` then fails with
> *"Plugin 'deepl' is not installed or bundled."* Using `"$(pwd)/deepl"` (or a
> full `/home/you/…/deepl`) avoids this. The `-sfn` flags make the command safe
> to re-run — they replace an existing or broken link in place.

Verify the link resolves and the manifest is readable through it:

```bash
readlink -f ~/.hermes/plugins/deepl      # should print the real .../deepl path
cat ~/.hermes/plugins/deepl/plugin.yaml  # should print the manifest
```

Set your DeepL key (Free keys end in `:fx`; the plugin auto-selects the Free or
Pro endpoint). The manifest gates on this via `requires_env`, so **the plugin
stays inactive until `DEEPL_API_KEY` is set in the environment Hermes runs in**:

```bash
export DEEPL_API_KEY="your-key-here"
```

Open a **new** Hermes session (enabling takes effect on the next session) — the
banner should list `deepl: translate, deepl_usage`. Verify with `/plugins`.

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
