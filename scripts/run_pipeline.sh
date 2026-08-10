#!/bin/bash
set -euo pipefail

# Generic tekt.observer track pipeline runner.
#
# Runs (as applicable to the track):
#   discover / gather  ->  enrich  ->  classify  ->  trends  ->  synthesize  ->  render markdown
#
# Stages are dispatched conditionally:
# - Discovery source depends on flags:
#     --live      : use scripts/feed_gather.py with the track's source registry
#     (default)   : if scripts/<track>_discover.py exists use it (ai_topics),
#                   else write an empty discovery artifact (market_watch fixture).
# - Enrich runs when --live is set.
# - Classify runs when scripts/<track>_classify.py exists.
# - Trends runs when the classify step wrote an organized artifact.
# - Synthesize runs when scripts/<track>_synthesize_digest.py exists.
# - Render always runs when a digest JSON exists.
#
# All work happens in a scratch JOB_AGENT_ROOT so the tracked working tree
# stays clean (mirroring scripts/test_track_workflow.sh).

usage() {
  cat <<EOF
Usage: $0 --track <slug> [--live] [--today YYYY-MM-DD] [--audience <id>] [--scratch <path>] [--registry <path>]

Options:
  --track SLUG        Track name under tracks/<slug>/  (required)
  --live              Use feed_gather to pull from the track's source registry
  --today YYYY-MM-DD  Date to run for (default: today)
  --audience ID       Audience id passed to synthesize (default per track)
  --scratch PATH      Scratch root (default: tests/tmp/<track>)
  --registry PATH     Override the source registry path
  -h, --help          Show this help
EOF
}

TRACK=""
LIVE=0
TODAY=""
AUDIENCE=""
SCRATCH=""
REGISTRY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --track)     TRACK="$2"; shift 2 ;;
    --live)      LIVE=1; shift ;;
    --today)     TODAY="$2"; shift 2 ;;
    --audience)  AUDIENCE="$2"; shift 2 ;;
    --scratch)   SCRATCH="$2"; shift 2 ;;
    --registry)  REGISTRY="$2"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$TRACK" ]]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$ROOT/.venv/bin/python"
TODAY="${TODAY:-$(date +%F)}"
SCRATCH="${SCRATCH:-$ROOT/tests/tmp/$TRACK}"
REGISTRY_DEFAULT="$ROOT/shared/schemas/${TRACK}_source_registry.json"
REGISTRY="${REGISTRY:-$REGISTRY_DEFAULT}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing repo-local virtualenv at $ROOT/.venv." >&2
  echo "Run: bash scripts/bootstrap_venv.sh --no-chromium" >&2
  exit 1
fi

TRACK_DIR="$ROOT/tracks/$TRACK"
if [[ ! -d "$TRACK_DIR" ]]; then
  echo "No such track: $TRACK_DIR" >&2
  exit 1
fi

echo "[pipeline] track=$TRACK today=$TODAY live=$LIVE scratch=$SCRATCH"

# --- Scratch setup ---------------------------------------------------------
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH/tracks/$TRACK" "$SCRATCH/shared" "$SCRATCH/artifacts/discovery/$TRACK"
cp -R "$ROOT/scripts" "$SCRATCH/scripts"
ln -s "$ROOT/shared/schemas" "$SCRATCH/shared/schemas"
cp "$ROOT/shared/digest_schema.md" "$SCRATCH/shared/digest_schema.md"
ln -s "$ROOT/.venv" "$SCRATCH/.venv"
if [[ -d "$ROOT/profile" ]]; then
  mkdir -p "$SCRATCH/profile"
  [[ -d "$ROOT/profile/personas" ]] && ln -s "$ROOT/profile/personas" "$SCRATCH/profile/personas"
fi
for f in sources.json source_state.json prefs.md AGENTS.md; do
  [[ -f "$TRACK_DIR/$f" ]] && cp "$TRACK_DIR/$f" "$SCRATCH/tracks/$TRACK/$f"
done

# --- 1. Discover / gather --------------------------------------------------
if [[ "$LIVE" -eq 1 ]]; then
  if [[ ! -f "$REGISTRY" ]]; then
    echo "[pipeline] --live requires a source registry; none at $REGISTRY" >&2
    exit 1
  fi
  echo "[pipeline] gather (feed_gather, $REGISTRY)"
  "$PYTHON_BIN" "$SCRATCH/scripts/feed_gather.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$TODAY" --registry "$REGISTRY"
  echo "[pipeline] enrich (feed_enrich, cached at artifacts/enrichment/$TRACK/urls.json)"
  "$PYTHON_BIN" "$SCRATCH/scripts/feed_enrich.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$TODAY"
else
  DISC_SCRIPT="$SCRATCH/scripts/${TRACK}_discover.py"
  if [[ -f "$DISC_SCRIPT" ]]; then
    echo "[pipeline] discover (${TRACK}_discover)"
    "$PYTHON_BIN" "$DISC_SCRIPT" --root "$SCRATCH" --track "$TRACK" --date "$TODAY"
  else
    echo "[pipeline] fixture mode: no ${TRACK}_discover.py, writing empty discovery artifact"
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
fi

# --- 2. Classify -----------------------------------------------------------
CLASSIFY_SCRIPT="$SCRATCH/scripts/${TRACK}_classify.py"
if [[ -f "$CLASSIFY_SCRIPT" ]]; then
  echo "[pipeline] classify (${TRACK}_classify)"
  "$PYTHON_BIN" "$CLASSIFY_SCRIPT" --root "$SCRATCH" --track "$TRACK" --date "$TODAY"
else
  echo "[pipeline] no ${TRACK}_classify.py; skipping classify + trends + synthesize"
fi

# --- 3. Trends -------------------------------------------------------------
if [[ -f "$SCRATCH/artifacts/organized/$TRACK/$TODAY.json" ]]; then
  echo "[pipeline] trends (track_trends)"
  "$PYTHON_BIN" "$SCRATCH/scripts/track_trends.py" --root "$SCRATCH" --track "$TRACK" --date "$TODAY"
  echo "[pipeline] rerank per audience (track_rerank, with-feedback)"
  "$PYTHON_BIN" "$SCRATCH/scripts/track_rerank.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$TODAY" --with-feedback || \
    echo "[pipeline] rerank failed (continuing)"
  echo "[pipeline] per-audience digests (synthesize_audience_digests)"
  "$PYTHON_BIN" "$SCRATCH/scripts/synthesize_audience_digests.py" \
    --root "$SCRATCH" --track "$TRACK" --date "$TODAY" || \
    echo "[pipeline] per-audience synth failed (continuing)"
fi

# --- 4. Synthesize digest --------------------------------------------------
SYNTH_SCRIPT="$SCRATCH/scripts/${TRACK}_synthesize_digest.py"
if [[ -f "$SYNTH_SCRIPT" && -f "$SCRATCH/artifacts/organized/$TRACK/$TODAY.json" ]]; then
  echo "[pipeline] synthesize (${TRACK}_synthesize_digest)"
  SYNTH_ARGS=(--root "$SCRATCH" --track "$TRACK" --date "$TODAY")
  if [[ -n "$AUDIENCE" ]]; then SYNTH_ARGS+=(--audience "$AUDIENCE"); fi
  "$PYTHON_BIN" "$SYNTH_SCRIPT" "${SYNTH_ARGS[@]}" || echo "[pipeline] synthesize failed (continuing)"
fi

# --- 5. Render markdown digest ---------------------------------------------
DIGEST_JSON="$SCRATCH/artifacts/digests/$TRACK/$TODAY.json"
if [[ -f "$DIGEST_JSON" ]]; then
  mkdir -p "$SCRATCH/tracks/$TRACK/digests"
  echo "[pipeline] render_digest"
  "$PYTHON_BIN" "$SCRATCH/scripts/render_digest.py" \
    --track "$TRACK" --date "$TODAY" \
    --input "$DIGEST_JSON" \
    --output "$SCRATCH/tracks/$TRACK/digests/$TODAY.md" \
    --latest-output "$SCRATCH/artifacts/digests/$TRACK/latest.json"
fi

# --- Summary ---------------------------------------------------------------
echo
echo "Mode:              $([[ $LIVE -eq 1 ]] && echo live || echo fixture)"
echo "Scratch root:      $SCRATCH"
[[ -f "$SCRATCH/artifacts/discovery/$TRACK/$TODAY.json" ]] && \
  echo "Discovery:         $SCRATCH/artifacts/discovery/$TRACK/$TODAY.json"
[[ -f "$SCRATCH/artifacts/organized/$TRACK/$TODAY.json"  ]] && \
  echo "Organized:         $SCRATCH/artifacts/organized/$TRACK/$TODAY.json"
[[ -f "$SCRATCH/artifacts/trends/$TRACK/$TODAY.json"     ]] && \
  echo "Trends:            $SCRATCH/artifacts/trends/$TRACK/$TODAY.json"
[[ -f "$DIGEST_JSON"                                      ]] && \
  echo "Digest JSON:       $DIGEST_JSON"
[[ -f "$SCRATCH/tracks/$TRACK/digests/$TODAY.md"          ]] && \
  echo "Digest markdown:   $SCRATCH/tracks/$TRACK/digests/$TODAY.md"
[[ "$LIVE" -eq 1 && -f "$SCRATCH/artifacts/enrichment/$TRACK/urls.json" ]] && \
  echo "Enrichment cache:  $SCRATCH/artifacts/enrichment/$TRACK/urls.json"
echo
echo "Generate site:     $PYTHON_BIN scripts/render_html.py --root $SCRATCH --out site/"
echo "Serve live:        $PYTHON_BIN scripts/serve_html.py --root $SCRATCH"
