"""Stable report identifiers shared by all pipeline stages."""

from datetime import date


def report_key(month: str, period: str = "1mo", market_type: str = "all") -> str:
    if date.fromisoformat(f"{month}-01").strftime("%Y-%m") != month:
        raise ValueError("month must use YYYY-MM format")
    if period not in ("1mo", "3mo", "6mo", "12mo"):
        raise ValueError(f"Unsupported period: {period}")
    if market_type not in ("all", "sale", "rent"):
        raise ValueError(f"Unsupported market type: {market_type}")
    return month + (f"_{period}" if period != "1mo" else "") + (f"_{market_type}" if market_type != "all" else "")
