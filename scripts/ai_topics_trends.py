"""Trend aggregation for the ai_topics track.

Reads today's organized artifact and (if present) yesterday's, computes:
- items_per_topic today
- items_per_source today
- topic_velocity (delta vs previous run)
- cross_source_urls (same URL/canonical appearing across multiple sources)
- keyword_counts (frequent significant tokens in titles)

Writes artifacts/trends/ai_topics/<date>.json for the viewer to render.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path


STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "of", "in", "to", "on", "with", "by",
    "is", "are", "as", "at", "be", "from", "how", "why", "we", "you", "your",
    "our", "it", "its", "this", "that", "these", "those", "not", "no", "up",
    "into", "out", "over", "under", "than", "then", "so", "if", "but",
    "who", "what", "when", "where", "which", "vs", "using", "use", "one",
    "new", "will", "can", "should", "could", "would", "may", "get", "gets",
    "got", "make", "makes", "made", "way", "ways", "day", "days", "week",
    "year", "years", "just", "much", "many", "very", "more", "less",
    "part", "parts", "post", "posts", "video", "podcast", "book",
    "s", "t", "d", "re", "ll", "ve", "am", "pm",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


def _load_organized(root: Path, track: str, day: str) -> dict | None:
    p = root / "artifacts" / "organized" / track / f"{day}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def _tokens(title: str) -> list[str]:
    return [t for t in (m.group(0).lower() for m in TOKEN_RE.finditer(title or "")) if t not in STOPWORDS]


def compute_trends(today: dict, prev: dict | None) -> dict:
    items = today.get("items", [])
    per_topic: Counter = Counter(i["topic"] for i in items)
    per_source: Counter = Counter(i.get("source_id", "") for i in items)
    per_type: Counter = Counter(i.get("content_type", "") for i in items)
    per_audience: Counter = Counter()
    for i in items:
        for a in i.get("audiences") or []:
            per_audience[a] += 1

    velocity: dict[str, int] = {}
    if prev:
        prev_per_topic = Counter(i["topic"] for i in prev.get("items", []))
        all_topics = set(per_topic) | set(prev_per_topic)
        for t in all_topics:
            velocity[t] = per_topic.get(t, 0) - prev_per_topic.get(t, 0)

    # Cross-source: same URL host+path (rough canonical) across multiple source_ids
    url_to_sources: dict[str, set[str]] = defaultdict(set)
    for i in items:
        url = (i.get("url") or "").split("?")[0].rstrip("/")
        if url:
            url_to_sources[url].add(i.get("source_id", ""))
    cross = [
        {"url": u, "sources": sorted(s)} for u, s in url_to_sources.items() if len(s) > 1
    ]

    # Top keywords
    counter: Counter = Counter()
    for i in items:
        for tok in _tokens(i.get("title", "")):
            counter[tok] += 1
    top_keywords = [{"token": k, "count": v} for k, v in counter.most_common(25)]

    return {
        "schema_version": 1,
        "track": today.get("track", "ai_topics"),
        "date": today.get("date"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_items": len(items),
        "items_per_topic": [{"topic": k, "count": v} for k, v in per_topic.most_common()],
        "items_per_source": [{"source_id": k, "count": v} for k, v in per_source.most_common()],
        "items_per_content_type": [{"content_type": k, "count": v} for k, v in per_type.most_common()],
        "items_per_audience": [{"audience": k, "count": v} for k, v in per_audience.most_common()],
        "topic_velocity_vs_previous": [{"topic": k, "delta": v} for k, v in sorted(velocity.items(), key=lambda kv: -kv[1])],
        "cross_source_urls": cross,
        "top_keywords": top_keywords,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", default="ai_topics")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    today = _load_organized(root, args.track, args.date)
    if today is None:
        raise SystemExit(f"missing organized artifact for {args.date}")
    try:
        yday = (date_cls.fromisoformat(args.date) - timedelta(days=1)).isoformat()
    except ValueError:
        yday = None
    prev = _load_organized(root, args.track, yday) if yday else None
    trends = compute_trends(today, prev)
    out = root / "artifacts" / "trends" / args.track / f"{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trends, indent=2) + "\n")
    print(f"wrote {out} (topics={len(trends['items_per_topic'])} cross_source={len(trends['cross_source_urls'])})")


if __name__ == "__main__":
    main()
