"""Bounded background subprocess operations for the local management server."""

from __future__ import annotations

import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from portfolio_state import ID_RE, PortfolioStateError
from source_config import file_lock, write_json_atomic

STATES = {"queued", "running", "needs_input", "validating", "first_run", "ready", "failed", "cancelled"}
ACTIVE = {"queued", "running", "needs_input", "validating", "first_run"}
MAX_LOG_CHARS = 64_000


def _now(): return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class OperationManager:
    def __init__(self, root: Path):
        self.root = Path(root); self.path = self.root / "logs" / "portfolio-operations.json"
        self._processes: dict[str, subprocess.Popen] = {}; self._guard = threading.Lock()
    def _load(self):
        if not self.path.exists(): return {"schema_version": 1, "operations": []}
        try: value = json.loads(self.path.read_text())
        except json.JSONDecodeError as exc: raise PortfolioStateError(f"invalid operation state: {exc}") from exc
        return value
    def list(self): return self._load()["operations"]
    def get(self, op_id):
        return next((x for x in self.list() if x["id"] == op_id), None)
    def _update(self, op_id: str, **changes):
        with file_lock(self.path):
            data = self._load(); op = next(x for x in data["operations"] if x["id"] == op_id)
            op.update(changes); op["updated_at"] = _now(); write_json_atomic(self.path, data); return dict(op)
    def create(self, track: str, kind: str, command: list[str], *, initial_state="queued"):
        if not ID_RE.fullmatch(track): raise PortfolioStateError("invalid track")
        if kind not in {"setup", "run", "validate_sources", "schedule"}: raise PortfolioStateError("invalid operation kind")
        if initial_state not in STATES: raise PortfolioStateError("invalid operation state")
        with file_lock(self.path):
            data = self._load()
            if any(x["track"] == track and x["state"] in ACTIVE for x in data["operations"]):
                raise PortfolioStateError("track already has an active operation")
            op = {"id": uuid.uuid4().hex, "track": track, "kind": kind, "state": initial_state,
                  "created_at": _now(), "updated_at": _now(), "log": "", "returncode": None}
            data["operations"].append(op); data["operations"] = data["operations"][-200:]
            write_json_atomic(self.path, data)
        if command: threading.Thread(target=self._run, args=(op["id"], command), daemon=True).start()
        return op
    def _run(self, op_id: str, command: list[str]):
        self._update(op_id, state="running")
        try:
            process = subprocess.Popen(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            with self._guard: self._processes[op_id] = process
            output, _ = process.communicate(); state = "ready" if process.returncode == 0 else "failed"
            self._update(op_id, state=state, returncode=process.returncode, log=output[-MAX_LOG_CHARS:])
        except Exception as exc: self._update(op_id, state="failed", log=str(exc)[-MAX_LOG_CHARS:])
        finally:
            with self._guard: self._processes.pop(op_id, None)
    def cancel(self, op_id: str):
        op = self.get(op_id)
        if not op: raise PortfolioStateError("unknown operation")
        with self._guard:
            process = self._processes.get(op_id)
            if process: process.terminate()
        return self._update(op_id, state="cancelled")
