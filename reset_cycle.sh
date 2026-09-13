#!/usr/bin/env bash

# Reset a Scribe cycle directory.
# Usage:
#   ./reset_cycle.sh 2026-02
#   ./reset_cycle.sh 2026-02 --full   (also deletes originals/)
#
# Safe by design:
# - Only operates inside src/scribe/output/cycles/<cycle>
# - Will refuse to run if path is suspicious

set -e

CYCLE="$1"
MODE="$2"

if [[ -z "$CYCLE" ]]; then
  echo "Usage: $0 YYYY-MM [--full]"
  exit 1
fi

if [[ ! "$CYCLE" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
  echo "Error: cycle must be in YYYY-MM format"
  exit 1
fi

BASE_DIR="src/scribe/output/cycles"
CYCLE_DIR="$BASE_DIR/$CYCLE"

if [[ ! -d "$CYCLE_DIR" ]]; then
  echo "Cycle directory does not exist: $CYCLE_DIR"
  exit 1
fi

# Safety check: refuse to operate outside expected path
if [[ "$CYCLE_DIR" != src/scribe/output/cycles/* ]]; then
  echo "Refusing to operate on unexpected path: $CYCLE_DIR"
  exit 1
fi

echo "Resetting cycle: $CYCLE_DIR"
echo "Mode: ${MODE:-derived-only}"

# Remove derived artifacts
echo "Removing derived artifacts..."
rm -f "$CYCLE_DIR"/manifest.json
rm -f "$CYCLE_DIR"/minutes_*.tex
rm -f "$CYCLE_DIR"/minutes_*.pdf
rm -f "$CYCLE_DIR"/*.log
rm -f "$CYCLE_DIR"/*.aux
rm -f "$CYCLE_DIR"/*.out
rm -f "$CYCLE_DIR"/*.toc

rm -rf "$CYCLE_DIR"/pdf
rm -rf "$CYCLE_DIR"/png

mkdir -p "$CYCLE_DIR"/pdf
mkdir -p "$CYCLE_DIR"/png

# Optional full reset
if [[ "$MODE" == "--full" ]]; then
  echo "Removing originals..."
  rm -rf "$CYCLE_DIR"/originals
  mkdir -p "$CYCLE_DIR"/originals
fi

echo "Reset complete."