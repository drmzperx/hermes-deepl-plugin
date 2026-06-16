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
