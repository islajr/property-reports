#!/usr/bin/env python3
"""
run.py

The unified entry point and build tool for the property-reports pipeline.
Orchestrates the export, analysis, narrative generation, and PDF rendering.

Usage:
    # 1. Render a single month (June 2026) with placeholder narrative:
    python run.py --month 2026-06 --placeholder

    # 2. Render a 3-month report ending in June 2026, pulling fresh data:
    python run.py --month 2026-06 --period 3mo --export

    # 3. Render a 6-month report with real Gemini narratives:
    python run.py --month 2026-06 --period 6mo
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified build script for property-reports."
    )
    parser.add_argument(
        "--month",
        required=True,
        help="Target reporting month (end month) in YYYY-MM format, e.g. 2026-06",
    )
    parser.add_argument(
        "--period",
        default="1mo",
        choices=["1mo", "3mo", "6mo", "12mo"],
        help="Reporting period window length (default: 1mo)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export fresh data from Supabase before generating the report",
    )
    parser.add_argument(
        "--placeholder",
        action="store_true",
        help="Force placeholder narrative mode (bypasses Gemini API key check)",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF rendering via WeasyPrint",
    )
    parser.add_argument(
        "--issue",
        type=int,
        default=None,
        help="Issue number override",
    )
    args = parser.parse_args()

    # Determine paths relative to this script
    root_dir = Path(__file__).parent.resolve()
    venv_python = root_dir / ".venv" / "bin" / "python"
    
    # Fallback to sys.executable if venv python doesn't exist
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    # Step 1: Export data if requested
    if args.export:
        print("=== Step 1: Exporting data from Supabase ===")
        run_cmd([python_bin, str(root_dir / "scripts" / "export_data.py")])

    # Step 2: Compute metrics
    print(f"=== Step 2: Computing metrics for {args.month} ({args.period} period) ===")
    metrics_cmd = [
        python_bin,
        str(root_dir / "scripts" / "compute_metrics.py"),
        "--month", args.month,
        "--period", args.period,
    ]
    run_cmd(metrics_cmd)

    # Step 3: Generate narrative
    print("=== Step 3: Generating report narrative ===")
    narrative_cmd = [
        python_bin,
        str(root_dir / "scripts" / "generate_narrative.py"),
        "--month", args.month,
        "--period", args.period,
    ]
    if args.placeholder:
        narrative_cmd.append("--placeholder")
    run_cmd(narrative_cmd)

    # Step 4: Render report html & pdf
    print("=== Step 4: Rendering HTML & PDF reports ===")
    render_cmd = [
        python_bin,
        str(root_dir / "scripts" / "render_report.py"),
        "--month", args.month,
        "--period", args.period,
    ]
    if args.no_pdf:
        render_cmd.append("--no-pdf")
    if args.issue is not None:
        render_cmd.extend(["--issue", str(args.issue)])
    run_cmd(render_cmd)

    # Done
    suffix = "" if args.period == "1mo" else f"_{args.period}"
    out_folder = f"reports/{args.month}{suffix}"
    print(f"\n✓ Build completed successfully!")
    print(f"  Generated HTML: file://{(root_dir / out_folder / 'index.html').resolve()}")
    if not args.no_pdf:
        print(f"  Generated PDF:  file://{(root_dir / out_folder / 'report.pdf').resolve()}")


if __name__ == "__main__":
    main()
