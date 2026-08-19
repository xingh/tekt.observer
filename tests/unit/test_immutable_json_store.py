import datetime as dt
import json
from pathlib import Path

import pytest

from immutable_json_store import ImmutableJsonStore, StoreError


UTC = dt.timezone.utc


class Clock:
    def __init__(self):
        self.value = dt.datetime(2026, 8, 18, 12, tzinfo=UTC)

    def __call__(self):
        return self.value


def test_events_are_immutable_hash_chained_and_reduced(tmp_path: Path):
    clock = Clock()
    store = ImmutableJsonStore(tmp_path, compact_every=10, clock=clock)
    store.append("items", "one", "put", {"title": "First"})
    first_path = next((tmp_path / "events").iterdir())
    first_bytes = first_path.read_bytes()
    clock.value += dt.timedelta(seconds=1)
    store.append("items", "two", "put", {"title": "Second"})
    store.append("items", "one", "delete")
    assert first_path.read_bytes() == first_bytes
    assert store.read()["items"] == {"two": {"title": "Second"}}
    events = sorted((tmp_path / "events").iterdir())
    assert json.loads(events[1].read_text())["previous_hash"] in events[0].name


def test_count_threshold_compacts_and_keeps_old_files(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path, compact_every=2)
    store.append("watchers", "topic_watch", "put", {"enabled": True})
    assert not (tmp_path / "CURRENT.json").exists()
    store.append("watchers", "job_watch", "put", {"enabled": True})
    snapshots = list((tmp_path / "snapshots").iterdir())
    assert len(snapshots) == 1
    assert len(list((tmp_path / "events").iterdir())) == 2
    pointer = json.loads((tmp_path / "CURRENT.json").read_text())
    assert pointer["sequence"] == 2
    assert store.read()["watchers"]["topic_watch"]["enabled"] is True


def test_time_threshold_and_forced_flush(tmp_path: Path):
    clock = Clock()
    store = ImmutableJsonStore(tmp_path, compact_every=100, compact_interval_seconds=60, clock=clock)
    store.append("runs", "a", "put", {"status": "queued"})
    first = store.compact_if_due(force=True)
    clock.value += dt.timedelta(seconds=61)
    store.append("runs", "b", "put", {"status": "complete"})
    assert first is not None
    assert len(list((tmp_path / "snapshots").iterdir())) == 2


def test_tampering_is_detected(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path)
    store.append("items", "one", "put", {"title": "First"})
    event = next((tmp_path / "events").iterdir())
    event.write_text(event.read_text().replace("First", "Changed"))
    with pytest.raises(StoreError, match="hash mismatch"):
        store.read()
