import threading

import feed_gather


def test_gather_all_fetches_concurrently_but_preserves_registry_order(monkeypatch):
    lock = threading.Lock()
    release = threading.Event()
    active = 0
    peak = 0

    def fake_gather(source, window=None):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            if active >= 2:
                release.set()
        assert release.wait(1), "sources were fetched serially"
        with lock:
            active -= 1
        return [{"title": source["name"], "url": source["url"]}], [], "complete"

    monkeypatch.setattr(feed_gather, "_gather_source", fake_gather)
    sources = [
        {"id": f"source_{index}", "name": f"Source {index}", "kind": "rss", "url": f"https://example.com/{index}"}
        for index in range(4)
    ]
    result = feed_gather.gather_all({"sources": sources}, workers=3)
    assert peak >= 2
    assert [row["source_id"] for row in result] == [source["id"] for source in sources]
