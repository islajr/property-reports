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


def validate_metrics_identity(metrics: dict, month: str, period: str, market_type: str) -> None:
    key = report_key(month, period, market_type)
    if metrics.get("type", "all") != market_type:
        raise ValueError("Metrics market type does not match --type.")
    source_key = metrics.get("_source", {}).get("report_key")
    if source_key is not None and source_key != key:
        raise ValueError("Metrics report key does not match the requested report.")
    found = False
    for market, expected_type in (("sales", "sale"), ("rentals", "rent")):
        section = metrics.get(market)
        if section:
            found = True
            if market_type not in ("all", expected_type):
                raise ValueError(f"Unexpected {market} metrics for --type {market_type}.")
            if section["overall"]["report_month"] != report_key(month, period):
                raise ValueError("Metrics month or period does not match the requested report.")
    if not found:
        raise ValueError("No populated market metrics found.")


def require_closed_month(month: str, today: date | None = None) -> None:
    """Publication uses completed calendar months; previews may inspect open periods."""
    report_key(month)
    today = today or date.today()
    if date.fromisoformat(month + '-01') >= today.replace(day=1):
        raise ValueError('The reporting month is still open or in the future. Publish only after month-end; use an isolated preview for drafts.')
