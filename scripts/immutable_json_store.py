#!/usr/bin/env python3
"""Append-only JSON event storage with periodic immutable snapshots."""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterator, Mapping

STORE_SCHEMA_VERSION = 1
EVENT_RE = re.compile(r"^(\d{20})-([0-9a-f]{64})\.json$")
SNAPSHOT_RE = re.compile(r"^(\d{20})-([0-9a-f]{64})\.json$")
DEFAULT_COLLECTIONS = ("workspaces", "memberships", "watchers", "sources", "runs", "items", "feedback", "operations", "exports")


class StoreError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _timestamp(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_immutable(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise StoreError(f"immutable file collision: {path}")
        return
    with os.fdopen(descriptor, "wb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    _fsync_directory(path.parent)


def _replace_pointer(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as output:
        output.write(canonical_bytes(value))
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


class ImmutableJsonStore:
    """A hash-chained event log with deterministic point-in-time snapshots.

    Event and snapshot payloads are never updated or deleted. CURRENT is the
    sole mutable file and is only an atomic cache pointer; recovery works by
    validating immutable files even when the pointer is absent.
    """

    def __init__(
        self,
        root: Path,
        *,
        compact_every: int = 100,
        compact_interval_seconds: float = 300,
        clock: Callable[[], dt.datetime] = utc_now,
    ) -> None:
        if compact_every < 1:
            raise ValueError("compact_every must be at least 1")
        if compact_interval_seconds < 0:
            raise ValueError("compact_interval_seconds cannot be negative")
        self.root = Path(root)
        self.events_dir = self.root / "events"
        self.snapshots_dir = self.root / "snapshots"
        self.current_path = self.root / "CURRENT.json"
        self.lock_path = self.root / ".writer.lock"
        self.compact_every = compact_every
        self.compact_interval_seconds = compact_interval_seconds
        self.clock = clock

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            yield

    def _files(self, directory: Path, pattern: re.Pattern[str]) -> list[tuple[int, str, Path]]:
        if not directory.exists():
            return []
        output = []
        for path in directory.iterdir():
            match = pattern.match(path.name)
            if match:
                output.append((int(match.group(1)), match.group(2), path))
        return sorted(output)

    def _read_verified(self, path: Path, expected_hash: str) -> dict[str, Any]:
        payload = path.read_bytes()
        if digest_bytes(payload) != expected_hash:
            raise StoreError(f"hash mismatch: {path}")
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise StoreError(f"invalid JSON: {path}") from exc
        if not isinstance(value, dict):
            raise StoreError(f"expected JSON object: {path}")
        return value

    def _latest_snapshot(self) -> tuple[int, dict[str, Any] | None]:
        snapshots = self._files(self.snapshots_dir, SNAPSHOT_RE)
        if not snapshots:
            return 0, None
        sequence, expected_hash, path = snapshots[-1]
        snapshot = self._read_verified(path, expected_hash)
        if snapshot.get("sequence") != sequence or snapshot.get("schema_version") != STORE_SCHEMA_VERSION:
            raise StoreError(f"invalid snapshot metadata: {path}")
        return sequence, snapshot

    def _events_after(self, sequence: int) -> list[dict[str, Any]]:
        events = []
        previous_hash: str | None = None
        for event_sequence, expected_hash, path in self._files(self.events_dir, EVENT_RE):
            event = self._read_verified(path, expected_hash)
            if event.get("sequence") != event_sequence or event.get("schema_version") != STORE_SCHEMA_VERSION:
                raise StoreError(f"invalid event metadata: {path}")
            if previous_hash is not None and event.get("previous_hash") != previous_hash:
                raise StoreError(f"broken event hash chain: {path}")
            previous_hash = expected_hash
            if event_sequence > sequence:
                events.append(event)
        return events

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {name: {} for name in DEFAULT_COLLECTIONS}

    @staticmethod
    def _apply(state: dict[str, Any], event: Mapping[str, Any]) -> None:
        collection = event.get("collection")
        record_id = event.get("record_id")
        if not isinstance(collection, str) or not isinstance(record_id, str) or not record_id:
            raise StoreError("event collection and record_id must be non-empty strings")
        records = state.setdefault(collection, {})
        if not isinstance(records, dict):
            raise StoreError(f"state collection is not an object: {collection}")
        operation = event.get("operation")
        if operation == "put":
            record = event.get("record")
            if not isinstance(record, dict):
                raise StoreError("put event record must be an object")
            records[record_id] = record
        elif operation == "delete":
            records.pop(record_id, None)
        else:
            raise StoreError(f"unsupported event operation: {operation!r}")

    def read(self) -> dict[str, Any]:
        sequence, snapshot = self._latest_snapshot()
        state = self._empty_state() if snapshot is None else snapshot["state"]
        state = json.loads(json.dumps(state))
        for event in self._events_after(sequence):
            self._apply(state, event)
        return state

    def append(self, collection: str, record_id: str, operation: str, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._locked():
            files = self._files(self.events_dir, EVENT_RE)
            sequence = files[-1][0] + 1 if files else 1
            previous_hash = files[-1][1] if files else None
            event: dict[str, Any] = {
                "schema_version": STORE_SCHEMA_VERSION,
                "sequence": sequence,
                "recorded_at": _timestamp(self.clock()),
                "previous_hash": previous_hash,
                "collection": collection,
                "record_id": record_id,
                "operation": operation,
            }
            if operation == "put":
                if record is None:
                    raise StoreError("put requires a record")
                event["record"] = dict(record)
            elif operation != "delete":
                raise StoreError(f"unsupported event operation: {operation!r}")
            payload_hash = digest_bytes(canonical_bytes(event))
            path = self.events_dir / f"{sequence:020d}-{payload_hash}.json"
            _write_immutable(path, event)
            self._compact_if_due_locked()
            return event

    def _compaction_due(self, latest_sequence: int, snapshot: Mapping[str, Any] | None) -> bool:
        snapshot_sequence = int(snapshot.get("sequence", 0)) if snapshot else 0
        if latest_sequence - snapshot_sequence >= self.compact_every:
            return True
        if latest_sequence <= snapshot_sequence:
            return False
        if snapshot is None:
            return self.compact_interval_seconds == 0
        age = (self.clock() - _parse_timestamp(str(snapshot["created_at"]))).total_seconds()
        return age >= self.compact_interval_seconds

    def _compact_if_due_locked(self, *, force: bool = False) -> Path | None:
        files = self._files(self.events_dir, EVENT_RE)
        if not files:
            return None
        latest_sequence = files[-1][0]
        latest_event = self._read_verified(files[-1][2], files[-1][1])
        _, snapshot = self._latest_snapshot()
        if not force and not self._compaction_due(latest_sequence, snapshot):
            return None
        state = self.read()
        value = {
            "schema_version": STORE_SCHEMA_VERSION,
            "sequence": latest_sequence,
            "created_at": latest_event["recorded_at"],
            "state": state,
        }
        payload_hash = digest_bytes(canonical_bytes(value))
        path = self.snapshots_dir / f"{latest_sequence:020d}-{payload_hash}.json"
        _write_immutable(path, value)
        _replace_pointer(self.current_path, {"schema_version": STORE_SCHEMA_VERSION, "sequence": latest_sequence, "snapshot": path.name, "sha256": payload_hash})
        return path

    def compact_if_due(self, *, force: bool = False) -> Path | None:
        with self._locked():
            return self._compact_if_due_locked(force=force)
