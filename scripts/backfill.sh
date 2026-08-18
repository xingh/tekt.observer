#!/bin/bash
set -euo pipefail

# Simulate the pipeline for a range of past dates using REAL historical data.
#
# For each date D in the requested range:
#   1. feed_gather.py --for-date D              (real per-day windows: server-side
#                                                for HN Algolia, pubDate filter for
#                                                RSS/Atom — historical feeds return
#                                                fewer items the further back you go)
#   2. feed_enrich.py                            (per-URL OG cache, shared across dates)
#   3. <track>_classify.py                       (keyword classifier)
#   4. track_trends.py                           (aggregate + day-over-day velocity)
#   5. track_rerank.py --with-feedback           (per-audience rerank, incl. feedback boosts)
#   6. synthesize_audience_digests.py            (I7 per-audience digest variants)
#   7. <track>_synthesize_digest.py              (persona digest)
#
# The scratch tree is preserved across invocations, so batching (e.g. days 1-4,
# then 5-8, then 9-12) accumulates rather than replaces.

usage() {
  cat <<EOF
Usage: $0 --track <slug> --dates 'YYYY-MM-DD YYYY-MM-DD ...'
       $0 --track <slug> --start YYYY-MM-DD --end YYYY-MM-DD

  --track SLUG      Track name under tracks/<slug>/
  --dates 'A B ...' Space-separated list of dates
  --start / --end   Inclusive UTC date range
  --keep-scratch    Do not wipe existing scratch tree (default: keep)
  --reset-scratch   Wipe scratch tree before starting
EOF
}

TRACK=""
DATES=""
START=""
END=""
RESET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --track)         TRACK="$2"; shift 2 ;;
    --dates)         DATES="$2"; shift 2 ;;
    --start)         START="$2"; shift 2 ;;
    --end)           END="$2"; shift 2 ;;
    --keep-scratch)  RESET=0; shift ;;
    --reset-scratch) RESET=1; shift ;;
    -h|--help)       usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$TRACK" ]]; then
  usage >&2; exit 2
fi

if [[ -z "$DATES" && -z "$START" ]]; then
  usage >&2; exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$ROOT/.venv/bin/python"
SCRATCH="$ROOT/tests/tmp/$TRACK"
REGISTRY="$ROOT/shared/schemas/${TRACK}_source_registry.json"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing repo-local virtualenv at $ROOT/.venv." >&2
  exit 1
fi

# Expand --start/--end into DATES if needed
if [[ -z "$DATES" ]]; then
  cur="$START"
  while [[ "$cur" != $(date -d "$END +1 day" +%F) ]]; do
    DATES="$DATES $cur"
    cur=$(date -d "$cur +1 day" +%F)
  done
fi

if [[ "$RESET" == 1 ]]; then
  rm -rf "$SCRATCH"
fi

# Ensure scratch tree exists with scripts + schemas (mirror run_pipeline.sh setup).
# Always refresh scripts/ so backfill runs pick up the current repo copy even
# when the scratch tree was created by a prior invocation.
mkdir -p "$SCRATCH/tracks/$TRACK" "$SCRATCH/shared" "$SCRATCH/artifacts/discovery/$TRACK"
rm -rf "$SCRATCH/scripts"
cp -R "$ROOT/scripts" "$SCRATCH/scripts"
[[ ! -e "$SCRATCH/shared/schemas" ]] && ln -s "$ROOT/shared/schemas" "$SCRATCH/shared/schemas"
cp "$ROOT/shared/digest_schema.md" "$SCRATCH/shared/digest_schema.md"
[[ ! -e "$SCRATCH/.venv" ]] && ln -s "$ROOT/.venv" "$SCRATCH/.venv"
if [[ -d "$ROOT/profile" ]]; then
  mkdir -p "$SCRATCH/profile"
  [[ -d "$ROOT/profile/personas" && ! -e "$SCRATCH/profile/personas" ]] && \
    ln -s "$ROOT/profile/personas" "$SCRATCH/profile/personas"
fi
for f in sources.json source_state.json prefs.md AGENTS.md; do
  [[ -f "$ROOT/tracks/$TRACK/$f" ]] && cp "$ROOT/tracks/$TRACK/$f" "$SCRATCH/tracks/$TRACK/$f"
done

CLASSIFY="$SCRATCH/scripts/${TRACK}_classify.py"
SYNTH="$SCRATCH/scripts/${TRACK}_synthesize_digest.py"

# Guard: skip any date in the future — historical fetch has nothing to return
# for tomorrow, and empty artifacts are misleading noise.
TODAY_UTC=$(date -u +%F)
FILTERED=""
SKIPPED=""
for D in $DATES; do
  if [[ "$D" > "$TODAY_UTC" ]]; then
    SKIPPED="$SKIPPED $D"
  else
    FILTERED="$FILTERED $D"
  fi
done
if [[ -n "$SKIPPED" ]]; then
  echo "[backfill] skipping future dates:$SKIPPED" >&2
fi
DATES="$FILTERED"
if [[ -z "$DATES" ]]; then
  echo "[backfill] nothing to do — all requested dates are in the future" >&2
  exit 0
fi

echo "[backfill] track=$TRACK scratch=$SCRATCH"
echo "[backfill] dates:$DATES"

for D in $DATES; do
  echo "[backfill] === $D ==="
  # 1) gather (real per-day window)
  "$PYTHON_BIN" "$SCRATCH/scripts/feed_gather.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$D" \
    --registry "$REGISTRY" --for-date "$D" 2>&1 | tail -3

  # 2) enrich (uses shared URL cache)
  "$PYTHON_BIN" "$SCRATCH/scripts/feed_enrich.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$D" 2>&1 | tail -1

  # 3-7) deterministic stages
  "$PYTHON_BIN" "$CLASSIFY"                                            --root "$SCRATCH" --track "$TRACK" --date "$D" >/dev/null
  "$PYTHON_BIN" "$SCRATCH/scripts/track_trends.py"                     --root "$SCRATCH" --track "$TRACK" --date "$D" >/dev/null
  "$PYTHON_BIN" "$SCRATCH/scripts/track_rerank.py"                     --root "$SCRATCH" --track "$TRACK" --date "$D" --with-feedback >/dev/null
  "$PYTHON_BIN" "$SCRATCH/scripts/synthesize_audience_digests.py"      --root "$SCRATCH" --track "$TRACK" --date "$D" >/dev/null
  "$PYTHON_BIN" "$SYNTH"                                               --root "$SCRATCH" --track "$TRACK" --date "$D" >/dev/null

  mkdir -p "$SCRATCH/tracks/$TRACK/digests"
  "$PYTHON_BIN" "$SCRATCH/scripts/render_digest.py" \
    --track "$TRACK" --date "$D" \
    --input "$SCRATCH/artifacts/digests/$TRACK/$D.json" \
    --output "$SCRATCH/tracks/$TRACK/digests/$D.md" \
    --latest-output "$SCRATCH/artifacts/digests/$TRACK/latest.json" >/dev/null || true

  echo "  wrote artifacts for $D"
done

echo "[backfill] $TRACK: done"
