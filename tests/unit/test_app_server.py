import json
from pathlib import Path

import pytest

from app_server import create_digest, create_export, patch_item, patch_watcher, seed_store, workspace_payload
from exchange_bundle import read_bundle
from immutable_json_store import ImmutableJsonStore, StoreError


def _specs(tmp_path: Path) -> Path:
    watcher = tmp_path / "topic_watch"
    watcher.mkdir(parents=True)
    (watcher / "watcher.json").write_text(json.dumps({"id": "topic_watch", "slug": "topic_watch", "display_name": "Topicwatch · Topics", "description": "Things to know", "status": "active"}))
    (watcher / "sources.json").write_text(json.dumps({"sources": [{"id": "one"}]}))
    (watcher / "samples.json").write_text(json.dumps([{"item_key": "sample", "title": "Useful signal", "description": "Details", "topic": "AI", "url": "https://example.com"}]))
    return tmp_path


def test_seed_is_idempotent_and_workspace_is_immediately_useful(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path / "state", compact_every=100)
    specs = _specs(tmp_path / "specs")
    seed_store(store, specs)
    event_count = len(list((tmp_path / "state" / "events").iterdir()))
    seed_store(store, specs)
    payload = workspace_payload(store)
    assert len(list((tmp_path / "state" / "events").iterdir())) == event_count
    assert payload["watchers"][0]["sourceCount"] == 1
    assert payload["items"][0]["title"] == "Useful signal"
    assert (tmp_path / "state" / "CURRENT.json").exists()


def test_item_curation_is_journaled_and_increments_revision(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path / "state")
    seed_store(store, _specs(tmp_path / "specs"))
    item_id = workspace_payload(store)["items"][0]["id"]
    updated = patch_item(store, item_id, {"status": "saved"})
    assert updated["status"] == "saved"
    assert workspace_payload(store)["workspace"]["revision"] == 2
    assert len(list((tmp_path / "state" / "events").iterdir())) == 6


def test_item_curation_rejects_unknown_status_and_item(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path / "state")
    seed_store(store, _specs(tmp_path / "specs"))
    with pytest.raises(StoreError):
        patch_item(store, "missing", {"status": "favorite"})
    with pytest.raises(KeyError):
        patch_item(store, "missing", {"status": "saved"})


def test_watcher_toggle_digest_and_export_are_durable(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path / "state")
    seed_store(store, _specs(tmp_path / "specs"))
    watcher = patch_watcher(store, "topic_watch", {"enabled": False})
    digest = create_digest(store)
    export, path = create_export(store)
    assert watcher["status"] == "paused"
    assert digest["itemIds"]
    assert export["workspaceRevision"] == 1
    assert read_bundle(path)["data"]["digests"][0]["id"] == digest["id"]
    payload = workspace_payload(store)
    assert payload["watchers"][0]["enabled"] is False
    assert payload["exports"][0]["filename"].endswith(".json")
