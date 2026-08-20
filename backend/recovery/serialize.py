"""
serialize.py — snake_case inside, camelCase on the wire.

The data contract in CLAUDE.md is camelCase (`campaignShare`, `usualSpend`,
`freezeExpiresAt`). Python identifiers stay snake_case per PEP 8, so the
conversion happens once, at the JSON boundary, rather than by naming Python
attributes in a foreign convention.
"""
from __future__ import annotations

import re
from typing import Any

_SNAKE = re.compile(r"_([a-z0-9])")


def to_camel(name: str) -> str:
    return _SNAKE.sub(lambda m: m.group(1).upper(), name)


def camelize(value: Any) -> Any:
    """Recursively rewrite dict keys to camelCase. Values are untouched."""
    if isinstance(value, dict):
        return {to_camel(k): camelize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [camelize(v) for v in value]
    return value
