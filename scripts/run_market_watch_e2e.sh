#!/bin/bash
set -euo pipefail

# End-to-end run for the market_watch track.
#
# Default (fixture) mode: reuses tracks/market_watch/sources.json local
# fixture pointing at test_workflow HTML — will match zero items but the
# schema pipeline still validates.
#
# --live mode: gather from shared/schemas/market_watch_source_registry.json
# (Fed / SEC / BoE / Yahoo Finance / HN Algolia earnings + funding),
# enrich with OpenGraph, classify against watchlist, compute trends,
# synthesize digest, render markdown.

LIVE=0
if [[ "${1:-}" == "--live" ]]; then
  LIVE=1
  shift
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$ROOT/.venv/bin/python"
TRACK="market_watch"
TODAY="${MARKET_WATCH_TODAY:-$(date +%F)}"
SCRATCH="${MARKET_WATCH_SCRATCH:-$ROOT/tests/tmp/market_watch}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing repo-local virtualenv at $ROOT/.venv." >&2
  echo "Run: bash scripts/bootstrap_venv.sh --no-chromium" >&2
  exit 1
fi

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH/tracks/$TRACK" "$SCRATCH/shared"
cp -R "$ROOT/scripts" "$SCRATCH/scripts"
ln -s "$ROOT/shared/schemas" "$SCRATCH/shared/schemas"
cp "$ROOT/shared/digest_schema.md" "$SCRATCH/shared/digest_schema.md"
ln -s "$ROOT/.venv" "$SCRATCH/.venv"

if [[ -d "$ROOT/profile/personas" ]]; then
  mkdir -p "$SCRATCH/profile"
  ln -s "$ROOT/profile/personas" "$SCRATCH/profile/personas"
fi

cp "$ROOT/tracks/$TRACK/sources.json" "$SCRATCH/tracks/$TRACK/sources.json"
cp "$ROOT/tracks/$TRACK/source_state.json" "$SCRATCH/tracks/$TRACK/source_state.json"
cp "$ROOT/tracks/$TRACK/prefs.md" "$SCRATCH/tracks/$TRACK/prefs.md"
cp "$ROOT/tracks/$TRACK/AGENTS.md" "$SCRATCH/tracks/$TRACK/AGENTS.md"

# 1. Discover / gather
mkdir -p "$SCRATCH/artifacts/discovery/$TRACK"
if [[ "$LIVE" -eq 1 ]]; then
  "$PYTHON_BIN" "$SCRATCH/scripts/ai_topics_gather.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$TODAY" \
    --registry "$ROOT/shared/schemas/market_watch_source_registry.json"
  "$PYTHON_BIN" "$SCRATCH/scripts/ai_topics_enrich.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$TODAY"
else
  echo "[market_watch] fixture mode: skipping fetch, writing empty discovery artifact"
  cat > "$SCRATCH/artifacts/discovery/$TRACK/$TODAY.json" <<JSON
{
  "schema_version": 1,
  "track": "$TRACK",
  "today": "$TODAY",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "mode": "discover",
  "sources": []
}
JSON
  cp "$SCRATCH/artifacts/discovery/$TRACK/$TODAY.json" "$SCRATCH/artifacts/discovery/$TRACK/latest.json"
fi

# 2. Classify against watchlist
"$PYTHON_BIN" "$SCRATCH/scripts/market_watch_classify.py" \
  --root "$SCRATCH" --track "$TRACK" --date "$TODAY"

# 2a. Trends (reused across tracks)
"$PYTHON_BIN" "$SCRATCH/scripts/ai_topics_trends.py" \
  --root "$SCRATCH" --track "$TRACK" --date "$TODAY"

# 3. Synthesize digest (portfolio alerts + situational awareness)
"$PYTHON_BIN" "$SCRATCH/scripts/market_watch_synthesize_digest.py" \
  --root "$SCRATCH" --track "$TRACK" --date "$TODAY"

# 4. Render markdown digest
mkdir -p "$SCRATCH/tracks/$TRACK/digests"
"$PYTHON_BIN" "$SCRATCH/scripts/render_digest.py" \
  --track "$TRACK" --date "$TODAY" \
  --input "$SCRATCH/artifacts/digests/$TRACK/$TODAY.json" \
  --output "$SCRATCH/tracks/$TRACK/digests/$TODAY.md" \
  --latest-output "$SCRATCH/artifacts/digests/$TRACK/latest.json"

echo
echo "Mode:              $([[ $LIVE -eq 1 ]] && echo live || echo fixture)"
echo "Scratch root:      $SCRATCH"
echo "Discovery:         $SCRATCH/artifacts/discovery/$TRACK/$TODAY.json"
echo "Organized:         $SCRATCH/artifacts/organized/$TRACK/$TODAY.json"
echo "Trends:            $SCRATCH/artifacts/trends/$TRACK/$TODAY.json"
echo "Digest JSON:       $SCRATCH/artifacts/digests/$TRACK/$TODAY.json"
echo "Digest markdown:   $SCRATCH/tracks/$TRACK/digests/$TODAY.md"
if [[ "$LIVE" -eq 1 ]]; then
  echo "Enrichment cache:  $SCRATCH/artifacts/enrichment/$TRACK/urls.json"
fi
echo
echo "Generate site:     $PYTHON_BIN scripts/render_html.py --root $SCRATCH --out site/"
echo "Serve live:        $PYTHON_BIN scripts/serve_html.py --root $SCRATCH"
