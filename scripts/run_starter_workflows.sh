#!/bin/bash
set -euo pipefail

# Populate one local workspace with all tracked starter workflows.

usage() {
  cat <<EOF
Usage: $0 [--scratch PATH] [--today YYYY-MM-DD] [--live] [--serve]

Seeds viewable sample signals for ai_topics, market_watch, and job_watch into
one scratch root. --live replaces the samples with current keyless feed data.
With --serve, opens the loopback portfolio viewer after the runs finish.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRATCH="$ROOT/tests/tmp/starter-workflows"
TODAY=""
SERVE=0
LIVE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scratch) SCRATCH="$2"; shift 2 ;;
    --today) TODAY="$2"; shift 2 ;;
    --live) LIVE=1; shift ;;
    --serve) SERVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$LIVE" -eq 1 ]]; then
  COMMON=(--live --scratch "$SCRATCH")
  if [[ -n "$TODAY" ]]; then COMMON+=(--today "$TODAY"); fi
  bash "$SCRIPT_DIR/run_pipeline.sh" --track ai_topics "${COMMON[@]}"
  bash "$SCRIPT_DIR/run_pipeline.sh" --track market_watch "${COMMON[@]}" --append
  bash "$SCRIPT_DIR/run_pipeline.sh" --track job_watch "${COMMON[@]}" --append
else
  SEED_ARGS=(--root "$ROOT" --out "$SCRATCH")
  if [[ -n "$TODAY" ]]; then SEED_ARGS+=(--date "$TODAY"); fi
  "$ROOT/.venv/bin/python" "$SCRIPT_DIR/seed_starter_workspace.py" "${SEED_ARGS[@]}"
fi

echo
echo "Starter workspace: $SCRATCH"
echo "View it with:      $ROOT/.venv/bin/python $SCRIPT_DIR/serve_html.py --root $SCRATCH"

if [[ "$SERVE" -eq 1 ]]; then
  exec "$ROOT/.venv/bin/python" "$SCRIPT_DIR/serve_html.py" --root "$SCRATCH"
fi
