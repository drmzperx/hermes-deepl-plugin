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
