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
SELECT
    id,
    city,
    neighbourhood,
    snapshot_week,
    avg_days_on_market,
    computed_at,
    active_listing_count,
    new_listings_count,
    price_reduced_count,
    median_price_kobo,
    p25,
    p75,
    p90
FROM market.neighbourhood_snapshots
ORDER BY snapshot_week ASC, city ASC, neighbourhood ASC;
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
