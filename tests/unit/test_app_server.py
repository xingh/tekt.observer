import json
from pathlib import Path

import pytest

from app_server import create_digest, create_export, ingest_run_artifacts, patch_item, patch_watcher, seed_store, workspace_payload
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
    assert len(list((tmp_path / "state" / "events").iterdir())) == 7


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
    assert payload["sources"][0]["name"] == "one"
    assert payload["exports"][0]["filename"].endswith(".json")


def test_live_artifacts_replace_samples_and_preserve_curation_on_retry(tmp_path: Path):
    store = ImmutableJsonStore(tmp_path / "state")
    seed_store(store, _specs(tmp_path / "specs"))
    scratch = tmp_path / "scratch"
    organized = scratch / "artifacts" / "organized" / "topic_watch"
    digests = scratch / "artifacts" / "digests" / "topic_watch"
    organized.mkdir(parents=True)
    digests.mkdir(parents=True)
    artifact = {"track": "topic_watch", "date": "2026-08-19", "generated_at": "2026-08-19T12:00:00Z", "items": [{"item_key": "live-one", "source_id": "one", "title": "Live item", "url": "https://example.com/live", "topic": "AI", "confidence": 0.6, "rationale": "matched AI"}]}
    (organized / "2026-08-19.json").write_text(json.dumps(artifact))
    (digests / "2026-08-19.json").write_text(json.dumps({"runs": [{"top_matches": [{"job_key": "live-one", "fit_score": 9}]}]}))
    enrichment = scratch / "artifacts" / "enrichment" / "topic_watch"
    enrichment.mkdir(parents=True)
    (enrichment / "urls.json").write_text(json.dumps({"https://example.com/live": {"og_image": "https://example.com/image.jpg", "og_description": "OpenGraph summary", "og_site_name": "Example"}}))
    result = ingest_run_artifacts(store, scratch)
    payload = workspace_payload(store)
    assert result["itemCount"] == 1
    assert [item["title"] for item in payload["items"]] == ["Live item"]
    assert payload["items"][0]["score"] == 90
    assert payload["items"][0]["image"] == "https://example.com/image.jpg"
    assert payload["items"][0]["description"] == "OpenGraph summary"
    patch_item(store, "topic_watch:live-one", {"status": "saved"})
    ingest_run_artifacts(store, scratch)
    assert workspace_payload(store)["items"][0]["status"] == "saved"
