#!/usr/bin/env bash

# Rebuild a Scribe cycle end-to-end:
#   reset -> run_cycle -> build_minutes
#
# Usage:
#   ./rebuild_cycle.sh 2026-02 regular
#   ./rebuild_cycle.sh 2026-02 open --apply
#   ./rebuild_cycle.sh 2026-02 association --apply --force --skip-unknown
#   ./rebuild_cycle.sh 2026-02 regular --full --apply --query "in:inbox has:attachment newer_than:30d"
#
# Notes:
# - Default mode is safe: no Gmail writes/downloads unless --apply is passed.
# - Uses your venv python from PATH (activate venv first).

set -e

CYCLE="$1"
MEETING_TYPE="$2"
shift 2 || true

if [[ -z "$CYCLE" || -z "$MEETING_TYPE" ]]; then
  echo "Usage: $0 YYYY-MM regular|open|association [--full] [--apply] [--force] [--skip-unknown] [--keep-going] [--max N] [--query '...']"
  exit 1
fi

if [[ ! "$CYCLE" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
  echo "Error: cycle must be in YYYY-MM format"
  exit 1
fi

if [[ "$MEETING_TYPE" != "regular" && "$MEETING_TYPE" != "open" && "$MEETING_TYPE" != "association" ]]; then
  echo "Error: meeting type must be one of: regular, open, association"
  exit 1
fi

# Defaults
FULL_RESET=false
APPLY=false
FORCE=false
SKIP_UNKNOWN=false
KEEP_GOING=true
MAX=25
QUERY="in:inbox has:attachment newer_than:14d"

# Parse flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full)
      FULL_RESET=true
      shift
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --skip-unknown)
      SKIP_UNKNOWN=true
      shift
      ;;
    --keep-going)
      KEEP_GOING=true
      shift
      ;;
    --no-keep-going)
      KEEP_GOING=false
      shift
      ;;
    --max)
      MAX="$2"
      shift 2
      ;;
    --query)
      QUERY="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 2
      ;;
  esac
done

echo "=== Rebuild Cycle ==="
echo "Cycle: $CYCLE"
echo "Meeting type: $MEETING_TYPE"
echo "Full reset: $FULL_RESET"
echo "Apply (Gmail writes/downloads): $APPLY"
echo "Force restage: $FORCE"
echo "Skip unknown: $SKIP_UNKNOWN"
echo "Keep going: $KEEP_GOING"
echo "Max: $MAX"
echo "Query: $QUERY"
echo

# 1) Reset
if $FULL_RESET; then
  ./reset_cycle.sh "$CYCLE" --full
else
  ./reset_cycle.sh "$CYCLE"
fi

# 2) Run cycle pipeline
CMD=(python -m src.scribe.cli.run_cycle --cycle "$CYCLE" --max "$MAX" --query "$QUERY")

if $APPLY; then
  CMD+=(--apply)
fi
if $FORCE; then
  CMD+=(--force)
fi
if $SKIP_UNKNOWN; then
  CMD+=(--skip-unknown)
fi
if $KEEP_GOING; then
  CMD+=(--keep-going)
fi

echo
echo "=== Running pipeline ==="
printf '%q ' "${CMD[@]}"
echo
"${CMD[@]}"

# 3) Build minutes
echo
echo "=== Building minutes PDF ==="
python -m src.scribe.cli.build_minutes --cycle "$CYCLE" --type "$MEETING_TYPE"

echo
echo "=== Done ==="
echo "Cycle root: src/scribe/output/cycles/$CYCLE"