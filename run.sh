#!/bin/bash
# run.sh
#
# Unified build script and orchestrator for the property-reports pipeline.
#
# Usage:
#   # Render a single month with placeholder narratives:
#   ./run.sh --month 2026-06 --placeholder
#
#   # Render a 3-month report, pulling fresh data from Supabase first:
#   ./run.sh --month 2026-06 --period 3mo --export
#
#   # Render a 6-month report with real Gemini narratives:
#   ./run.sh --month 2026-06 --period 6mo

set -e

# Default values
PERIOD="1mo"
EXPORT=false
PLACEHOLDER=false
NO_PDF=false
ISSUE=""
MONTH=""

show_help() {
  echo "Usage: ./run.sh [options]"
  echo ""
  echo "Options:"
  echo "  -m, --month YYYY-MM    Target reporting month (end month) (required)"
  echo "  -p, --period PERIOD    Period window (1mo, 3mo, 6mo, 12mo; default: 1mo)"
  echo "  -e, --export           Pull fresh snapshots from Supabase first"
  echo "  --placeholder          Use placeholder narratives (bypasses Gemini API)"
  echo "  --no-pdf               Skip PDF generation via WeasyPrint"
  echo "  -i, --issue NUMBER     Set a custom issue number override"
  echo "  -h, --help             Show this help message"
  exit 0
}

# Parse options
while [[ $# -gt 0 ]]; do
  case $1 in
    -m|--month)
      MONTH="$2"
      shift 2
      ;;
    -p|--period)
      PERIOD="$2"
      shift 2
      ;;
    -e|--export)
      EXPORT=true
      shift
      ;;
    --placeholder)
      PLACEHOLDER=true
      shift
      ;;
    --no-pdf)
      NO_PDF=true
      shift
      ;;
    -i|--issue)
      ISSUE="$2"
      shift 2
      ;;
    -h|--help)
      show_help
      ;;
    *)
      echo "ERROR: Unknown option: $1"
      show_help
      ;;
  esac
done

if [ -z "$MONTH" ]; then
  echo "ERROR: --month YYYY-MM is required."
  echo ""
  show_help
fi

# Locate project root directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python"

# Fallback if venv is not set up
if [ ! -f "$PYTHON" ]; then
  PYTHON="python3"
fi

# Step 1: Export data
if [ "$EXPORT" = true ]; then
  echo "=== Step 1: Exporting data from Supabase ==="
  "$PYTHON" "$DIR/scripts/export_data.py"
fi

# Step 2: Compute metrics
echo "=== Step 2: Computing metrics for $MONTH ($PERIOD period) ==="
"$PYTHON" "$DIR/scripts/compute_metrics.py" --month "$MONTH" --period "$PERIOD"

# Step 3: Generate narrative
echo "=== Step 3: Generating report narrative ==="
NARRATIVE_ARGS=("--month" "$MONTH" "--period" "$PERIOD")
if [ "$PLACEHOLDER" = true ]; then
  NARRATIVE_ARGS+=("--placeholder")
fi
"$PYTHON" "$DIR/scripts/generate_narrative.py" "${NARRATIVE_ARGS[@]}"

# Step 4: Render reports
echo "=== Step 4: Rendering HTML & PDF reports ==="
RENDER_ARGS=("--month" "$MONTH" "--period" "$PERIOD")
if [ "$NO_PDF" = true ]; then
  RENDER_ARGS+=("--no-pdf")
fi
if [ -n "$ISSUE" ]; then
  RENDER_ARGS+=("--issue" "$ISSUE")
fi
"$PYTHON" "$DIR/scripts/render_report.py" "${RENDER_ARGS[@]}"

# Done
SUFFIX=""
if [ "$PERIOD" != "1mo" ]; then
  SUFFIX="_$PERIOD"
fi
OUT_FOLDER="reports/${MONTH}${SUFFIX}"

echo ""
echo "✓ Build completed successfully!"
echo "  Generated HTML: file://$DIR/$OUT_FOLDER/index.html"
if [ "$NO_PDF" = false ]; then
  echo "  Generated PDF:  file://$DIR/$OUT_FOLDER/report.pdf"
fi
