"""Deterministic classifier for the ai_topics track (I5 preview).

Reads a discovery artifact at artifacts/discovery/ai_topics/<date>.json and
emits artifacts/organized/ai_topics/<date>.json using keyword-based matching
against the taxonomy in shared/schemas/ai_topics_taxonomy.json.

This is a deterministic scaffold, not the eventual LLM-driven classifier.
Purpose: prove the pipeline shape and give the HTML viewer something to render.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_topics_taxonomy import Taxonomy, taxonomy_from_dict  # noqa: E402
from portfolio_state import resolved_classifier_taxonomy  # noqa: E402
from track_common import item_key, iso_utc_now, substring_match  # noqa: E402


TOPIC_KEYWORDS: dict[str, list[str]] = {
    "ai_knowledge_memory": [
        "knowledge graph", "context graph", "agent memory",
        "vector store", "retrieval augmented", "rag", "hnsw",
        "episodic memory", "knowledge storage", "entity resolution",
        "chunking",
    ],
    "ai_capabilities": [
        "vision", "document vision", "document formulate",
        "agent fleet", "fleet management",
    ],
    "open_source_ai": [
        "open source", "open-source", "oss", "harness",
    ],
    "models_intelligence_inference": [
        "inference", "local inference", "cloud inference",
        "quantized", "quantization", "gpu",
    ],
    "models_inference_strategy": [
        "fusion inference", "edge inference", "hybrid inference",
        "routing tokens", "routing", "cross-model",
    ],
    "models_family": [
        "foundation model", "frontier model", "open weights",
    ],
    "news_ai": [
        "regulator", "adoption", "roundup", "quarterly report",
        "policy", "transparency rule",
    ],
}

AUDIENCE_KEYWORDS: dict[str, list[str]] = {
    "architects": [
        "tradeoff", "invariant", "design", "architecture", "pattern",
        "hierarchy", "provenance", "schema",
    ],
    "builders": [
        "build", "building", "prototype", "code", "coding agent",
        "implementation", "tuning", "benchmark",
    ],
    "operators": [
        "cost", "latency", "reliability", "throughput", "observability",
        "cache", "caching", "production", "repair",
    ],
    "managers": [
        "team", "roadmap", "hiring", "adoption", "playbook",
    ],
    "leaders": [
        "strategy", "portfolio", "policy", "regulator",
        "annual", "compliance",
    ],
}

CONTENT_TYPE_HINTS: list[tuple[str, str]] = [
    ("/podcast", "podcast"),
    ("podcast", "podcast"),
    ("/video", "video"),
    ("video:", "video"),
    (".pdf", "paper"),
    ("paper:", "paper"),
    ("/book", "book"),
    ("book:", "book"),
    ("resource:", "resource"),
    ("catalog", "resource"),
    ("catalogue", "resource"),
]


def _classify_content_type(title: str, url: str) -> str:
    hay = f"{url.lower()} {title.lower()}"
    for needle, ctype in CONTENT_TYPE_HINTS:
        if needle in hay:
            return ctype
    return "post"


def _matches(title: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if substring_match(title, k)]


def _classify_topic(title: str) -> tuple[str, list[str]]:
    best_topic = "news_ai"
    best_hits: list[str] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        hits = _matches(title, keywords)
        if len(hits) > len(best_hits):
            best_topic = topic
            best_hits = hits
    return best_topic, best_hits


def _classify_audiences(title: str) -> tuple[list[str], list[str]]:
    hits_per: dict[str, list[str]] = {}
    for aud, keywords in AUDIENCE_KEYWORDS.items():
        m = _matches(title, keywords)
        if m:
            hits_per[aud] = m
    if not hits_per:
        return ["architects", "builders"], []  # sensible default
    return list(hits_per.keys()), sorted({m for ms in hits_per.values() for m in ms})


def classify_candidates(discovery: dict, taxonomy: Taxonomy, date: str) -> dict:
    items: list[dict] = []
    for source in discovery.get("sources", []):
        source_id = source.get("source_id", "")
        for cand in source.get("candidates", []):
            url = cand.get("url", "")
            title = cand.get("title", "")
            topic, topic_hits = _classify_topic(title)
            ctype = _classify_content_type(title, url)
            audiences, aud_hits = _classify_audiences(title)
            # categories: topic-derived only for I1 scope
            categories = [topic]
            confidence = min(1.0, 0.4 + 0.2 * len(topic_hits) + 0.1 * len(aud_hits))
            item = {
                "item_key": item_key("ai", url, title),
                "source_id": source_id,
                "url": url,
                "title": title,
                "topic": topic,
                "content_type": ctype,
                "categories": categories,
                "audiences": audiences,
                "confidence": round(confidence, 2),
                "rationale": (
                    f"topic_hits={topic_hits}; audience_hits={aud_hits}; "
                    f"content_type_inferred={ctype}"
                ),
            }
            items.append(item)
    return {
        "schema_version": 1,
        "track": "ai_topics",
        "date": date,
        "generated_at": iso_utc_now(),
        "items": items,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (discovery date)")
    ap.add_argument("--track", default="ai_topics")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    discovery_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    if not discovery_path.is_file():
        sys.exit(f"missing discovery artifact: {discovery_path}")
    discovery = json.loads(discovery_path.read_text())
    taxonomy = taxonomy_from_dict(resolved_classifier_taxonomy(root, args.track))
    organized = classify_candidates(discovery, taxonomy, args.date)
    out_path = root / "artifacts" / "organized" / args.track / f"{args.date}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(organized, indent=2) + "\n")
    print(f"wrote {out_path} ({len(organized['items'])} items)")


if __name__ == "__main__":
    main()
