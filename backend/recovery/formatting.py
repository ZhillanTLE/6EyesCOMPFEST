"""
formatting.py — Indonesian number formatting.

Thousands separated by dots, decimals by comma: IDR 24.640.000, -10,3%, 3,81s.
Applied at the formatter and never stored pre-formatted, which is where the
prototype went wrong -- its seed held "-11.2%" with a dot while its runtime
formatter produced commas, so the same screen showed both conventions.
"""
from __future__ import annotations

from typing import Optional


def idr(amount: Optional[int]) -> str:
    if amount is None:
        return "-"
    return "IDR " + "{:,.0f}".format(amount).replace(",", ".")


def pct(fraction: Optional[float], signed: bool = True) -> str:
    """0.1123 -> '-11,2%' (signed: a saving is shown as a price drop)."""
    if fraction is None:
        return "-"
    value = fraction * 100
    body = "{:.1f}".format(abs(value)).replace(".", ",")
    if not signed:
        return body + "%"
    return ("-" if value > 0 else "+") + body + "%"


def plain_pct(fraction: Optional[float]) -> str:
    if fraction is None:
        return "-"
    return "{:.1f}".format(fraction * 100).replace(".", ",") + "%"


def seconds(ms: Optional[int]) -> str:
    if ms is None:
        return "-"
    return "{:.2f}".format(ms / 1000.0).replace(".", ",") + "s"
