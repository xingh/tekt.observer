import json
import threading
from pathlib import Path

import pytest

from portfolio_state import PortfolioStateError, PortfolioStore, unified_items
from seed_starter_workspace import seed


def _track(root: Path, slug="alpha"):
    (root / "tracks" / slug).mkdir(parents=True)


def test_legacy_tracks_project_into_implicit_portfolio(tmp_path):
    _track(tmp_path)
    state = PortfolioStore(tmp_path)
    assert state.track("alpha")["implicit"] is True
    assert state.portfolios()["portfolios"][0]["track_ids"] == ["alpha"]
    assert not (tmp_path / "profile").exists()


def test_initialize_and_reject_dangling_references(tmp_path):
    _track(tmp_path)
    store = PortfolioStore(tmp_path); store.initialize()
    with pytest.raises(PortfolioStateError, match="dangling"):
        store.mutate("portfolios", lambda p: {**p, "portfolios": [{**p["portfolios"][0], "interest_ids": ["missing"]}]})


def test_concurrent_mutations_do_not_lose_updates(tmp_path):
    store = PortfolioStore(tmp_path); store.initialize()
    errors = []
    def add(i):
        try:
            store.mutate("interests", lambda p: {**p, "interests": p["interests"] + [{"id": f"interest_{i}", "label": str(i), "description": "", "keywords": []}]})
        except Exception as exc: errors.append(exc)
    threads = [threading.Thread(target=add, args=(i,)) for i in range(8)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert not errors
    assert len(store.interests()["interests"]) == 8


def test_unified_items_deduplicates_and_normalizes_score(tmp_path):
    _track(tmp_path)
    base = tmp_path / "artifacts" / "ranked_audience" / "alpha" / "builders"; base.mkdir(parents=True)
    (base / "2026-08-18.json").write_text(json.dumps({"items": [{"item_key": "one", "title": "One", "audience_score": 1.5}]}))
    organized = tmp_path / "artifacts" / "organized" / "alpha"; organized.mkdir(parents=True)
    (organized / "2026-08-18.json").write_text(json.dumps({"items": [{"item_key": "one", "title": "Old"}]}))
    items = unified_items(tmp_path)
    assert len(items) == 1
    assert items[0]["id"] == "alpha:one"
    assert items[0]["score_percent"] == 100


def test_taxonomy_override_blocks_orphaned_mapping(tmp_path):
    _track(tmp_path)
    store = PortfolioStore(tmp_path); store.initialize()
    store.mutate("interests", lambda p: {**p, "interests": [{"id": "ai", "label": "AI", "description": "", "keywords": []}]})
    store.save_track("alpha", {"schema_version": 1, "id": "alpha", "display_name": "Alpha", "status": "active", "interest_ids": ["ai"], "default_audience": "builders", "interest_topic_mappings": {"ai": ["agents"]}})
    with pytest.raises(PortfolioStateError, match="orphan"):
        store.save_taxonomy("alpha", {"schema_version": 1, "track": "alpha", "topics": [], "audiences": []})


def test_shipped_starter_workflows_have_valid_metadata(repo_root):
    store = PortfolioStore(repo_root)
    expected = {
        "topic_watch": ("Topicwatch · AI in Business", "managers"),
        "market_watch": ("Marketwatch · AI Markets & Regulation", "investors"),
        "career_watch": ("Careerwatch · Career opportunities & intelligence", "senior_ic"),
    }
    assert expected.keys() <= store.track_ids()
    for slug, (name, audience) in expected.items():
        metadata = store.track(slug)
        assert metadata["display_name"] == name
        assert metadata["default_audience"] == audience
        assert metadata.get("implicit") is not True


def test_seed_starter_workspace_populates_each_workflow(repo_root, tmp_path):
    seed(repo_root, tmp_path, "2026-08-18")
    items = unified_items(tmp_path)
    assert {item["track"] for item in items} == {"topic_watch", "market_watch", "career_watch"}
    assert len(items) == 9
    assert all(item["sample"] is True for item in items)


def test_seed_starter_workspace_refuses_repository_root(repo_root):
    with pytest.raises(ValueError, match="must not be"):
        seed(repo_root, repo_root, "2026-08-18")
