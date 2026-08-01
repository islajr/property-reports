"""
scripts/export_data.py

Exports the neighbourhood_snapshots table from Supabase to a local CSV file
for offline report generation. Requires SUPABASE_DB_URL in .env.

Usage:
    python scripts/export_data.py
    python scripts/export_data.py --out data/neighbourhood_snapshots.csv

For one-off use during development, you can also export directly from the
Supabase dashboard (Table Editor → Export CSV) and place the file at
data/neighbourhood_snapshots.csv.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"

EXPORT_QUERY = """
WITH weeks AS (
    SELECT DISTINCT date_trunc('week', snapshot_week)::DATE AS snapshot_week
    FROM (
        SELECT generate_series(
            '2026-04-06'::DATE,
            date_trunc('week', CURRENT_DATE)::DATE,
            '1 week'::INTERVAL
        )::DATE AS snapshot_week
    ) s
),
active_listings_per_week AS (
    SELECT
        l.id AS listing_id,
        l.city,
        l.neighbourhood,
        l.price_type,
        market.classify_property(l.title, l.property_type, l.bedrooms) AS property_class,
        l.price_kobo,
        l.first_seen_at,
        l.last_seen_at,
        w.snapshot_week
    FROM raw_data.scraped_listings l
    CROSS JOIN weeks w
    WHERE l.first_seen_at::DATE <= w.snapshot_week + 6
      AND (l.listing_status = 'ACTIVE' OR l.last_seen_at::DATE >= w.snapshot_week)
      AND l.city IS NOT NULL
      AND l.neighbourhood IS NOT NULL
      AND l.price_type IS NOT NULL
),
new_listings_per_week AS (
    SELECT
        l.city,
        l.neighbourhood,
        l.price_type,
        market.classify_property(l.title, l.property_type, l.bedrooms) AS property_class,
        w.snapshot_week,
        COUNT(*) as new_count
    FROM raw_data.scraped_listings l
    CROSS JOIN weeks w
    WHERE l.first_seen_at::DATE >= w.snapshot_week
      AND l.first_seen_at::DATE <= w.snapshot_week + 6
      AND l.city IS NOT NULL
      AND l.neighbourhood IS NOT NULL
      AND l.price_type IS NOT NULL
    GROUP BY l.city, l.neighbourhood, l.price_type, property_class, w.snapshot_week
),
weekly_reductions AS (
    SELECT
        h.listing_id,
        w.snapshot_week,
        COUNT(*) as reduced_count
    FROM raw_data.listing_history h
    CROSS JOIN weeks w
    WHERE h.event_type = 'PRICE_CHANGE'
      AND h.new_value < h.old_value
      AND h.event_date >= w.snapshot_week
      AND h.event_date <= w.snapshot_week + 6
    GROUP BY h.listing_id, w.snapshot_week
)
SELECT
    md5(a.city || a.neighbourhood || a.snapshot_week::text || a.price_type || a.property_class) AS id,
    a.city,
    a.neighbourhood,
    a.snapshot_week,
    a.price_type,
    a.property_class,
    ROUND(AVG(GREATEST(1.0, EXTRACT(EPOCH FROM (LEAST(a.last_seen_at, (a.snapshot_week + 7)::TIMESTAMP) - a.first_seen_at)) / 86400.0))::NUMERIC, 1) AS avg_days_on_market,
    NOW() AS computed_at,
    COUNT(a.listing_id) AS active_listing_count,
    COALESCE(MAX(n.new_count), 0) AS new_listings_count,
    COALESCE(SUM(r.reduced_count), 0) AS price_reduced_count,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY a.price_kobo) AS median_price_kobo,
    percentile_cont(0.25) WITHIN GROUP (ORDER BY a.price_kobo) AS p25,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY a.price_kobo) AS p75,
    percentile_cont(0.90) WITHIN GROUP (ORDER BY a.price_kobo) AS p90
FROM active_listings_per_week a
LEFT JOIN new_listings_per_week n ON a.city = n.city AND a.neighbourhood = n.neighbourhood AND a.price_type = n.price_type AND a.property_class = n.property_class AND a.snapshot_week = n.snapshot_week
LEFT JOIN weekly_reductions r ON a.listing_id = r.listing_id AND a.snapshot_week = r.snapshot_week
GROUP BY a.city, a.neighbourhood, a.snapshot_week, a.price_type, a.property_class
ORDER BY a.snapshot_week ASC, a.city ASC, a.neighbourhood ASC, a.price_type ASC, a.property_class ASC;
"""


def export_to_csv(db_url: str, out_path: Path) -> None:
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to Supabase ...")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print("Executing export query ...")
    cursor.execute(EXPORT_QUERY)
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]

    print(f"Fetched {len(rows):,} rows. Writing to {out_path} ...")

    import csv
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        writer.writerows(rows)

    cursor.close()
    conn.close()
    print(f"✓ Export complete: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export neighbourhood snapshots from Supabase.")
    parser.add_argument(
        "--out",
        default=str(DATA_DIR / "neighbourhood_snapshots.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not set. Add it to .env or set it in the environment.", file=sys.stderr)
        sys.exit(1)

    export_to_csv(db_url, Path(args.out))


if __name__ == "__main__":
    main()
