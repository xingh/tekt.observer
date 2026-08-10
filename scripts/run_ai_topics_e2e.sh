#!/bin/bash
# Back-compat wrapper. The real work lives in scripts/run_pipeline.sh.
# Prefer: bash scripts/run_pipeline.sh --track ai_topics [--live]

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/run_pipeline.sh" --track ai_topics "$@"
