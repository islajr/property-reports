"""
scripts/compute_metrics.py

Reads the neighbourhood_snapshots CSV and produces a structured JSON metrics file
for a given reporting period (defaults to the prior calendar month).

All internal prices are in kobo (integer). NGN conversions happen here for display,
but the raw kobo values are preserved in the JSON for downstream verification.

Usage:
    python scripts/compute_metrics.py --month 2026-06
    python scripts/compute_metrics.py --csv path/to/snapshots.csv --month 2026-06
    python scripts/compute_metrics.py --month 2026-06 --all-weeks
        (includes weeks from prior months if the date range spans them)

Output:
    data/metrics_2026-06.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KOBO_PER_NGN = 100
DEFAULT_CSV = Path(__file__).parent.parent / "data" / "neighbourhood_snapshots.csv"
DATA_DIR = Path(__file__).parent.parent / "data"

MIN_LISTINGS_EXPENSIVE = 5   # lowered slightly due to price_type split
MIN_LISTINGS_AFFORDABLE = 3   # lowered slightly due to price_type split


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def kobo_to_ngn(kobo: float | None) -> float | None:
    """Convert kobo integer to NGN float. Returns None for null values."""
    if kobo is None or pd.isna(kobo):
        return None
    return kobo / KOBO_PER_NGN


def fmt_ngn(kobo: float | None, dp: int = 2) -> str:
    """Format a kobo value as a NGN string with commas."""
    ngn = kobo_to_ngn(kobo)
    if ngn is None:
        return "N/A"
    return f"₦{ngn:,.{dp}f}"


def period_label(month_str: str) -> str:
    """'2026-06' → 'June 2026'"""
    dt = date.fromisoformat(f"{month_str}-01")
    return dt.strftime("%B %Y")


def month_date_range(month_str: str) -> tuple[date, date]:
    """Return (first_day, last_day) for a month string like '2026-06'."""
    year, month = int(month_str[:4]), int(month_str[5:7])
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def get_period_dates(month_str: str, period_str: str) -> tuple[date, date, str]:
    """
    Given an end month YYYY-MM and a period (1mo, 3mo, 6mo, 12mo),
    returns (start_date, end_date, label).
    """
    year, month = int(month_str[:4]), int(month_str[5:7])
    
    months_to_subtract = {
        "1mo": 0,
        "3mo": 2,
        "6mo": 5,
        "12mo": 11,
    }.get(period_str, 0)
    
    start_month = month - months_to_subtract
    start_year = year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
        
    first_date = date(start_year, start_month, 1)
    
    if month == 12:
        last_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_date = date(year, month + 1, 1) - timedelta(days=1)
        
    if period_str == "1mo":
        label = first_date.strftime("%B %Y")
    else:
        label = f"{first_date.strftime('%B %Y')} – {date(year, month, 1).strftime('%B %Y')}"
        
    return first_date, last_date, label


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def load_snapshots(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Normalise column names to lowercase stripped
    df.columns = [c.strip().lower() for c in df.columns]

    required = {
        "city", "neighbourhood", "snapshot_week",
        "active_listing_count", "new_listings_count",
        "price_reduced_count", "median_price_kobo", "property_class",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df["snapshot_week"] = pd.to_datetime(df["snapshot_week"]).dt.date
    df["city"] = df["city"].str.strip().str.upper()
    df["neighbourhood"] = df["neighbourhood"].str.strip()
    df["property_class"] = df["property_class"].str.strip().str.upper()

    # Numeric safety — coerce bad values to NaN
    for col in ["active_listing_count", "new_listings_count",
                "price_reduced_count", "median_price_kobo",
                "p25", "p75", "p90", "avg_days_on_market"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filter out short lets
    if "price_type" in df.columns:
        df = df[df["price_type"] != "FOR_SHORT_LET"].copy()

    return df


def filter_to_period(df: pd.DataFrame, first: date, last: date, label_str: str) -> pd.DataFrame:
    mask = (df["snapshot_week"] >= first) & (df["snapshot_week"] <= last)
    filtered = df[mask].copy()
    if filtered.empty:
        raise ValueError(
            f"No snapshot rows found for period {label_str} "
            f"({first} to {last}). Check the CSV date range."
        )
    return filtered


def compute_overall(df: pd.DataFrame, month_str: str, period_label_str: str, period_str: str) -> dict[str, Any]:
    """High-level summary metrics for the reporting period."""
    weeks = sorted(df["snapshot_week"].unique())
    num_weeks = len(weeks)

    total_snapshots = len(df)
    cities = sorted(df["city"].unique().tolist())
    unique_neighbourhoods = df["neighbourhood"].nunique()

    total_active_cumulative = int(df["active_listing_count"].sum())
    total_new_listings = int(df["new_listings_count"].sum())
    total_price_reductions = int(df["price_reduced_count"].sum())

    # Peak active listings: latest week's sum across all neighbourhoods
    latest_week = weeks[-1]
    peak_active = int(df[df["snapshot_week"] == latest_week]["active_listing_count"].sum())

    # Earliest week active total
    earliest_week = weeks[0]
    earliest_active = int(df[df["snapshot_week"] == earliest_week]["active_listing_count"].sum())

    # Growth: (peak - earliest) / earliest
    growth_pct = None
    if earliest_active > 0:
        growth_pct = round((peak_active - earliest_active) / earliest_active * 100, 1)

    # Overall median price across all snapshots (median of medians — note this
    # in the report as it conflates listing types; per-neighbourhood is more meaningful)
    overall_median_kobo = df["median_price_kobo"].median()

    # Weekly median price trajectory
    weekly_medians = (
        df.groupby("snapshot_week")["median_price_kobo"]
        .median()
        .sort_index()
    )
    first_weekly_median_kobo = float(weekly_medians.iloc[0]) if len(weekly_medians) > 0 else None
    last_weekly_median_kobo = float(weekly_medians.iloc[-1]) if len(weekly_medians) > 0 else None

    report_month_val = month_str if period_str == "1mo" else f"{month_str}_{period_str}"

    return {
        "report_month": report_month_val,
        "report_period_label": period_label_str,
        "weeks": [str(w) for w in weeks],
        "num_weeks": num_weeks,
        "date_range": {
            "start": str(weeks[0]),
            "end": str(weeks[-1]),
        },
        "cities": cities,
        "num_cities": len(cities),
        "total_snapshot_records": total_snapshots,
        "unique_neighbourhoods": unique_neighbourhoods,
        "cumulative_active_listings": total_active_cumulative,
        "total_new_listings": total_new_listings,
        "total_price_reductions": total_price_reductions,
        "peak_active_listings": peak_active,
        "earliest_active_listings": earliest_active,
        "active_listings_growth_pct": growth_pct,
        "overall_median_price_kobo": float(overall_median_kobo) if pd.notna(overall_median_kobo) else None,
        "overall_median_price_ngn": kobo_to_ngn(overall_median_kobo),
        "first_week_median_price_kobo": first_weekly_median_kobo,
        "last_week_median_price_kobo": last_weekly_median_kobo,
    }


def compute_weekly_aggregates(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Week-by-week totals across all neighbourhoods."""
    rows = []
    for week, grp in df.groupby("snapshot_week"):
        active = int(grp["active_listing_count"].sum())
        new_listings = int(grp["new_listings_count"].sum())
        price_reductions = int(grp["price_reduced_count"].sum())
        median_kobo = grp["median_price_kobo"].median()
        rows.append({
            "week": str(week),
            "active_listing_count": active,
            "new_listings_count": new_listings,
            "price_reduced_count": price_reductions,
            "median_price_kobo": float(median_kobo) if pd.notna(median_kobo) else None,
            "median_price_ngn": kobo_to_ngn(median_kobo),
        })
    return sorted(rows, key=lambda r: r["week"])


def compute_inventory_ranking(df: pd.DataFrame, top_n: int = 10) -> list[dict[str, Any]]:
    """Most active neighbourhoods by average weekly active listing count."""
    avg = (
        df.groupby(["city", "neighbourhood"])["active_listing_count"]
        .mean()
        .reset_index()
        .rename(columns={"active_listing_count": "avg_weekly_active"})
        .sort_values("avg_weekly_active", ascending=False)
        .head(top_n)
    )
    results = []
    for rank, (_, row) in enumerate(avg.iterrows(), start=1):
        results.append({
            "rank": rank,
            "city": row["city"],
            "neighbourhood": row["neighbourhood"],
            "avg_weekly_active_listings": round(float(row["avg_weekly_active"]), 1),
        })
    return results


def compute_pricing_tiers(
    df: pd.DataFrame,
    top_n: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    """
    Most expensive and most affordable neighbourhoods by average median price.

    Filters:
    - Expensive: only neighbourhoods whose average weekly active listing count >= MIN_LISTINGS_EXPENSIVE
    - Affordable: only neighbourhoods whose average weekly active listing count >= MIN_LISTINGS_AFFORDABLE
    """
    # Per-neighbourhood aggregates
    agg = df.groupby(["city", "neighbourhood"]).agg(
        avg_median_price_kobo=("median_price_kobo", "mean"),
        avg_weekly_active=("active_listing_count", "mean"),
        avg_dom=("avg_days_on_market", "mean"),
        num_weeks=("snapshot_week", "nunique"),
    ).reset_index()

    expensive = (
        agg[agg["avg_weekly_active"] >= MIN_LISTINGS_EXPENSIVE]
        .sort_values("avg_median_price_kobo", ascending=False)
        .head(top_n)
    )
    affordable = (
        agg[agg["avg_weekly_active"] >= MIN_LISTINGS_AFFORDABLE]
        .sort_values("avg_median_price_kobo", ascending=True)
        .head(top_n)
    )

    def _build(rows: pd.DataFrame) -> list[dict[str, Any]]:
        out = []
        for rank, (_, row) in enumerate(rows.iterrows(), start=1):
            kobo = row["avg_median_price_kobo"]
            dom = row["avg_dom"]
            out.append({
                "rank": rank,
                "city": row["city"],
                "neighbourhood": row["neighbourhood"],
                "avg_median_price_kobo": float(kobo) if pd.notna(kobo) else None,
                "avg_median_price_ngn": kobo_to_ngn(kobo),
                "avg_days_on_market": round(float(dom), 1) if pd.notna(dom) else None,
                "num_weeks_observed": int(row["num_weeks"]),
            })
        return out

    return {
        "most_expensive": _build(expensive),
        "most_affordable": _build(affordable),
        "filter_note": {
            "expensive_min_listings": MIN_LISTINGS_EXPENSIVE,
            "affordable_min_listings": MIN_LISTINGS_AFFORDABLE,
        },
    }


def compute_city_breakdown(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Per-city summary metrics."""
    breakdown = {}
    for city, grp in df.groupby("city"):
        num_neighbourhoods = grp["neighbourhood"].nunique()
        total_active = int(grp["active_listing_count"].sum())
        total_new = int(grp["new_listings_count"].sum())
        total_reductions = int(grp["price_reduced_count"].sum())
        median_kobo = grp["median_price_kobo"].median()

        # Top neighbourhood by avg active
        top_hood = (
            grp.groupby("neighbourhood")["active_listing_count"]
            .mean()
            .idxmax()
        )
        breakdown[city] = {
            "city": city,
            "num_neighbourhoods": num_neighbourhoods,
            "cumulative_active_listings": total_active,
            "total_new_listings": total_new,
            "total_price_reductions": total_reductions,
            "median_price_kobo": float(median_kobo) if pd.notna(median_kobo) else None,
            "median_price_ngn": kobo_to_ngn(median_kobo),
            "top_neighbourhood_by_activity": top_hood,
        }
    return breakdown


def compute_price_reduction_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """Week-by-week price reduction events and concentration by city."""
    total = int(df["price_reduced_count"].sum())

    by_city = (
        df.groupby("city")["price_reduced_count"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    city_breakdown = [
        {"city": row["city"], "total_reductions": int(row["price_reduced_count"])}
        for _, row in by_city.iterrows()
    ]

    # Week with the most reductions
    weekly = df.groupby("snapshot_week")["price_reduced_count"].sum()
    peak_week = str(weekly.idxmax()) if len(weekly) > 0 else None
    peak_week_count = int(weekly.max()) if len(weekly) > 0 else 0

    return {
        "total_price_reductions": total,
        "peak_week": peak_week,
        "peak_week_count": peak_week_count,
        "by_city": city_breakdown,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def compute_all_metrics(df: pd.DataFrame, month_str: str, period_label_str: str, period_str: str) -> dict[str, Any]:
    """Helper to calculate the full set of metrics for a filtered dataset."""
    return {
        "overall": compute_overall(df, month_str, period_label_str, period_str),
        "weekly_aggregates": compute_weekly_aggregates(df),
        "inventory_ranking": compute_inventory_ranking(df),
        "pricing_tiers": compute_pricing_tiers(df),
        "city_breakdown": compute_city_breakdown(df),
        "price_reduction_analysis": compute_price_reduction_analysis(df),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute monthly market metrics from neighbourhood snapshots CSV."
    )
    parser.add_argument(
        "--month",
        required=True,
        help="Reporting month in YYYY-MM format, e.g. 2026-06",
    )
    parser.add_argument(
        "--period",
        default="1mo",
        choices=["1mo", "3mo", "6mo", "12mo"],
        help="Reporting period window length (default: 1mo)",
    )
    parser.add_argument(
        "--type",
        default="all",
        choices=["all", "sale", "rent"],
        help="Report type: all (combined), sale (sales only), or rent (rentals only)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help=f"Path to the snapshots CSV. Defaults to {DEFAULT_CSV}",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path. Defaults to data/metrics_YYYY-MM[_period].json",
    )
    args = parser.parse_args()

    # Validate month format
    try:
        date.fromisoformat(f"{args.month}-01")
    except ValueError:
        print(f"ERROR: --month must be in YYYY-MM format, got '{args.month}'", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(args.csv) if args.csv else DEFAULT_CSV
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}", file=sys.stderr)
        print("Run scripts/export_data.py first, or pass --csv path/to/file.csv", file=sys.stderr)
        sys.exit(1)

    # Determine start date, end date, and text label based on period
    first_date, last_date, period_label_str = get_period_dates(args.month, args.period)

    suffix = "" if args.period == "1mo" else f"_{args.period}"
    out_path = Path(args.out) if args.out else DATA_DIR / f"metrics_{args.month}{suffix}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading snapshots from {csv_path} ...")
    df = load_snapshots(csv_path)
    print(f"  Total rows loaded: {len(df):,}")

    print(f"Filtering to period {period_label_str} ({first_date} to {last_date}) ...")
    period_df = filter_to_period(df, first_date, last_date, period_label_str)
    weeks = sorted(period_df["snapshot_week"].unique())
    print(f"  Rows in period: {len(period_df):,}  |  Weeks: {[str(w) for w in weeks]}")

    print(f"Computing metrics (type: {args.type}) ...")
    metrics = {
        "type": args.type,
        "sales": None,
        "rentals": None
    }

    if args.type in ("all", "sale"):
        sales_df = period_df[period_df["price_type"] == "FOR_SALE"]
        if not sales_df.empty:
            metrics["sales"] = compute_all_metrics(sales_df, args.month, period_label_str, args.period)
            metrics["sales"]["classes"] = {}
            for prop_class, grp in sales_df.groupby("property_class"):
                filtered_grp = grp[grp["active_listing_count"] >= 3].copy()
                if not filtered_grp.empty:
                    metrics["sales"]["classes"][prop_class] = compute_all_metrics(filtered_grp, args.month, period_label_str, args.period)
        else:
            print("  WARNING: No Sales records found in period.")

    if args.type in ("all", "rent"):
        rent_df = period_df[period_df["price_type"] == "FOR_RENT"]
        if not rent_df.empty:
            metrics["rentals"] = compute_all_metrics(rent_df, args.month, period_label_str, args.period)
            metrics["rentals"]["classes"] = {}
            for prop_class, grp in rent_df.groupby("property_class"):
                filtered_grp = grp[grp["active_listing_count"] >= 3].copy()
                if not filtered_grp.empty:
                    metrics["rentals"]["classes"][prop_class] = compute_all_metrics(filtered_grp, args.month, period_label_str, args.period)
        else:
            print("  WARNING: No Rentals records found in period.")

    with open(out_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(f"\n✓ Metrics written to {out_path}")

    # Print sanity check
    print("\n--- Sanity check ---")
    print(f"  Period:               {period_label_str}")
    print(f"  Weeks covered:        {len(weeks)}")
    if metrics["sales"]:
        ov = metrics["sales"]["overall"]
        print(f"  [SALES] Cumulative Active: {ov['cumulative_active_listings']:,} | Peak Active: {ov['peak_active_listings']:,} | Median Price: {fmt_ngn(ov['overall_median_price_kobo'])}")
    if metrics["rentals"]:
        ov = metrics["rentals"]["overall"]
        print(f"  [RENTALS] Cumulative Active: {ov['cumulative_active_listings']:,} | Peak Active: {ov['peak_active_listings']:,} | Median Price: {fmt_ngn(ov['overall_median_price_kobo'])}/yr")
    print("--------------------")


if __name__ == "__main__":
    main()
