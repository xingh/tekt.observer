import json

from topic_watch_classify import _classify_topic
from career_watch_classify import classify_candidates as classify_jobs
from market_watch_classify import DEFAULT_WATCHLIST, _classify_event_type, _watchlist_hits


def test_business_topic_starter_classification():
    topic, hits = _classify_topic("Enterprise AI adoption needs workflow redesign and measurable ROI")
    assert topic == "enterprise_ai_adoption"
    assert {"enterprise ai", "ai adoption", "roi"} <= set(hits)


def test_ai_enabled_profession_starter_classification(repo_root):
    taxonomy = json.loads((repo_root / "shared/schemas/career_watch_taxonomy.json").read_text())
    discovery = {"sources": [{"source_id": "starter", "candidates": [{
        "title": "AI Governance and Model Risk Lead",
        "description": "Own responsible AI compliance and model risk controls.",
        "url": "https://example.test/jobs/governance",
    }]}]}
    item = classify_jobs(discovery, taxonomy, "2026-08-18")["items"][0]
    assert item["role_type"] == "ai_governance_risk"


def test_ai_market_regulation_watchlist_and_registries(repo_root):
    hits, classes = _watchlist_hits("FTC AI Act review affects NVDA chip export controls", DEFAULT_WATCHLIST)
    assert {"FTC", "AI Act", "NVDA", "export control"} <= set(hits)
    assert {"public_equities", "ai_regulation"} <= set(classes)
    taxonomy = json.loads((repo_root / "shared/schemas/market_watch_taxonomy.json").read_text())
    assert _classify_event_type("New chip export control for AI accelerators", "ai_regulation", taxonomy) == "export_control"

    expected = {"topic_watch": 8, "market_watch": 10, "career_watch": 5}
    for track, count in expected.items():
        registry = json.loads((repo_root / f"shared/schemas/{track}_source_registry.json").read_text())
        assert len(registry["sources"]) == count
        assert sum(source["kind"] == "hn_algolia" for source in registry["sources"]) <= 2
