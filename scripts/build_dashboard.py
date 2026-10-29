"""Refresh the publication archive without rebuilding any report issue."""
import argparse
from pathlib import Path
from render_report import regenerate_index, generate_sitemap_and_robots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'reports')
    args = parser.parse_args()
    regenerate_index(args.reports_dir)
    generate_sitemap_and_robots(args.reports_dir)


if __name__ == '__main__':
    main()
