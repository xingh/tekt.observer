#!/bin/bash
set -euo pipefail

# End-to-end deterministic run for the ai_topics track (I1 preview).
#
# Sets up a scratch JOB_AGENT_ROOT, points ai_topics at the local HTML
# fixture, runs discovery -> classify -> synthesize digest -> render markdown.
# No provider CLI required. Prints artifact paths so scripts/render_html.py
# can be pointed at the scratch root.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$ROOT/.venv/bin/python"
TRACK="ai_topics"
TODAY="${AI_TOPICS_TODAY:-$(date +%F)}"
AUDIENCE="${AI_TOPICS_AUDIENCE:-architects}"
SCRATCH="${AI_TOPICS_SCRATCH:-$ROOT/tests/tmp/ai_topics}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing repo-local virtualenv at $ROOT/.venv." >&2
  echo "Run: bash scripts/bootstrap_venv.sh --no-chromium" >&2
  exit 1
fi

FIXTURE="$ROOT/tests/fixtures/ai_topics/knowledge_memory_board.html"
if [[ ! -f "$FIXTURE" ]]; then
  echo "Missing fixture: $FIXTURE" >&2
  exit 1
fi

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH/tracks/$TRACK" "$SCRATCH/shared"
cp -R "$ROOT/scripts" "$SCRATCH/scripts"
ln -s "$ROOT/shared/schemas" "$SCRATCH/shared/schemas"
cp "$ROOT/shared/digest_schema.md" "$SCRATCH/shared/digest_schema.md"
ln -s "$ROOT/.venv" "$SCRATCH/.venv"

FIXTURE_URL="file://$FIXTURE"
"$PYTHON_BIN" - "$ROOT/tracks/$TRACK/sources.json" "$SCRATCH/tracks/$TRACK/sources.json" "$FIXTURE_URL" <<'PY'
import json, sys, pathlib
src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])
url = sys.argv[3]
data = json.loads(src.read_text())
for s in data["sources"]:
    if s["id"] == "local_test_board":
        s["url"] = url
        s["name"] = "AI Knowledge and Memory Feed"
dst.write_text(json.dumps(data, indent=2) + "\n")
PY

cp "$ROOT/tracks/$TRACK/source_state.json" "$SCRATCH/tracks/$TRACK/source_state.json"
cp "$ROOT/tracks/$TRACK/prefs.md" "$SCRATCH/tracks/$TRACK/prefs.md"
cp "$ROOT/tracks/$TRACK/AGENTS.md" "$SCRATCH/tracks/$TRACK/AGENTS.md"

# 1. Discover (topic-tracker discovery, not job-search discovery)
mkdir -p "$SCRATCH/artifacts/discovery/$TRACK"
"$PYTHON_BIN" "$SCRATCH/scripts/ai_topics_discover.py" \
  --root "$SCRATCH" --track "$TRACK" --date "$TODAY"

# 2. Classify
"$PYTHON_BIN" "$SCRATCH/scripts/ai_topics_classify.py" --root "$SCRATCH" --date "$TODAY"

# 3. Synthesize digest
"$PYTHON_BIN" "$SCRATCH/scripts/ai_topics_synthesize_digest.py" \
  --root "$SCRATCH" --date "$TODAY" --audience "$AUDIENCE"

# 4. Render markdown digest (scripts copied into scratch, so ROOT resolves there)
mkdir -p "$SCRATCH/tracks/$TRACK/digests"
"$PYTHON_BIN" "$SCRATCH/scripts/render_digest.py" \
  --track "$TRACK" --date "$TODAY" \
  --input "$SCRATCH/artifacts/digests/$TRACK/$TODAY.json" \
  --output "$SCRATCH/tracks/$TRACK/digests/$TODAY.md" \
  --latest-output "$SCRATCH/artifacts/digests/$TRACK/latest.json"

echo
echo "Scratch root:      $SCRATCH"
echo "Discovery:         $SCRATCH/artifacts/discovery/$TRACK/$TODAY.json"
echo "Organized:         $SCRATCH/artifacts/organized/$TRACK/$TODAY.json"
echo "Digest JSON:       $SCRATCH/artifacts/digests/$TRACK/$TODAY.json"
echo "Digest markdown:   $SCRATCH/tracks/$TRACK/digests/$TODAY.md"
echo
echo "Generate site:     $PYTHON_BIN scripts/render_html.py --root $SCRATCH --out site/"
echo "Serve live:        $PYTHON_BIN scripts/serve_html.py --root $SCRATCH"
