import threading

import feed_enrich


def test_enrichment_fetches_concurrently_and_preserves_candidate_mapping(monkeypatch):
    lock = threading.Lock()
    release = threading.Event()
    active = 0
    peak = 0

    def fake_enrich(url):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            if active >= 2:
                release.set()
        assert release.wait(1), "metadata was fetched serially"
        with lock:
            active -= 1
        return {"og_title": url.rsplit("/", 1)[-1]}

    monkeypatch.setattr(feed_enrich, "enrich_url", fake_enrich)
    discovery = {"sources": [{"candidates": [{"url": f"https://example.com/{index}"} for index in range(4)]}]}
    cache = {}
    assert feed_enrich.enrich_discovery(discovery, cache, max_urls=3, workers=3) == 3
    assert peak >= 2
    candidates = discovery["sources"][0]["candidates"]
    assert candidates[0]["enrichment"]["og_title"] == "0"
    assert candidates[3]["enrichment"] == {"error": "budget_exhausted"}
