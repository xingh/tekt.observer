#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$ROOT/.venv/bin/python"

cd "$ROOT"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing repo-local virtualenv at $ROOT/.venv." >&2
  echo "Run: bash scripts/bootstrap_venv.sh" >&2
  exit 1
fi

bash -n scripts/run_track.sh
bash -n scripts/bootstrap_machine.sh
bash -n scripts/setup_machine.sh
bash -n scripts/install_bwrap_apparmor.sh
bash -n scripts/install_scheduler.sh
bash -n scripts/run_scheduled_jobs.sh
bash -n scripts/sync_to_logseq.sh
bash -n scripts/test_track_workflow.sh
bash -n scripts/sync_claude_skills.sh
bash -n tests/e2e/fake_codex.sh
"$PYTHON_BIN" -m compileall -q scripts
bash scripts/sync_claude_skills.sh --check
"$PYTHON_BIN" scripts/render_discovery_modes_md.py --check
"$PYTHON_BIN" scripts/generate_watchers.py --check

if [[ -d "$ROOT/frontend/node_modules" ]]; then
  npm --prefix frontend run build
  npm --prefix frontend test
else
  echo "Skipping frontend checks because frontend/node_modules is absent; run npm install in frontend/." >&2
fi

PYTEST_ARGS=("$@")
if [[ ${#PYTEST_ARGS[@]} -eq 0 ]]; then
  PYTEST_ARGS=(-q)
fi

"$PYTHON_BIN" -m pytest tests "${PYTEST_ARGS[@]}"
