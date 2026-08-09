"""Load and validate the ai_topics taxonomy.

The taxonomy is authored in .arkitype/00-topic-tracker.md (human) and mirrored
in shared/schemas/ai_topics_taxonomy.json (machine-readable). Classifier and
tests read the JSON to avoid a YAML/markdown parse step.

An "item" is a content record with topic + content_type + categories + audiences.
Validation returns a list of reasons; empty list means the item is valid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAXONOMY_PATH = ROOT / "shared" / "schemas" / "ai_topics_taxonomy.json"


@dataclass(frozen=True)
class Taxonomy:
    topic_ids: frozenset[str]
    content_type_ids: frozenset[str]
    audience_ids: frozenset[str]
    category_group_map: dict[str, frozenset[str]]
    content_type_to_groups: dict[str, tuple[str, ...]]

    def categories_for_type(self, content_type: str) -> frozenset[str]:
        groups = self.content_type_to_groups.get(content_type, ())
        out: set[str] = set()
        for g in groups:
            out |= self.category_group_map.get(g, frozenset())
        return frozenset(out)


def load_taxonomy(path: Path = DEFAULT_TAXONOMY_PATH) -> Taxonomy:
    data = json.loads(path.read_text())
    topic_ids = frozenset(t["id"] for t in data["topics"])
    content_types = data["content_types"]
    audience_ids = frozenset(a["id"] for a in data["audiences"])
    category_group_map: dict[str, frozenset[str]] = {}
    category_group_map["topics"] = topic_ids
    for name, spec in data["category_groups"].items():
        base: set[str] = set()
        if spec.get("derived_from_topics"):
            base |= set(topic_ids)
        base |= set(spec.get("extra", []))
        category_group_map[name] = frozenset(base)
    content_type_to_groups = {
        ct["id"]: tuple(ct["category_groups"]) for ct in content_types
    }
    return Taxonomy(
        topic_ids=topic_ids,
        content_type_ids=frozenset(ct["id"] for ct in content_types),
        audience_ids=audience_ids,
        category_group_map=category_group_map,
        content_type_to_groups=content_type_to_groups,
    )


def validate_item(item: dict[str, Any], taxonomy: Taxonomy) -> list[str]:
    reasons: list[str] = []
    for required in ("item_key", "topic", "content_type", "audiences"):
        if required not in item or item[required] in (None, "", []):
            reasons.append(f"missing_required:{required}")
    topic = item.get("topic")
    if topic and topic not in taxonomy.topic_ids:
        reasons.append(f"unknown_topic:{topic}")
    ctype = item.get("content_type")
    if ctype and ctype not in taxonomy.content_type_ids:
        reasons.append(f"unknown_content_type:{ctype}")
    audiences = item.get("audiences") or []
    if not isinstance(audiences, list):
        reasons.append("audiences_not_list")
    else:
        for a in audiences:
            if a not in taxonomy.audience_ids:
                reasons.append(f"unknown_audience:{a}")
    categories = item.get("categories") or []
    if categories and ctype in taxonomy.content_type_ids:
        allowed = taxonomy.categories_for_type(ctype)
        for c in categories:
            if c not in allowed:
                reasons.append(f"unknown_category_for_type:{c}")
    return reasons


def validate_items(items: Iterable[dict[str, Any]], taxonomy: Taxonomy) -> tuple[int, int, dict[str, int]]:
    """Return (accepted, rejected, reason_counts)."""
    accepted = 0
    rejected = 0
    counts: dict[str, int] = {}
    for item in items:
        reasons = validate_item(item, taxonomy)
        if reasons:
            rejected += 1
            for r in reasons:
                key = r.split(":", 1)[0]
                counts[key] = counts.get(key, 0) + 1
        else:
            accepted += 1
    return accepted, rejected, counts


def _cli() -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--items", required=True, help="Path to items.json (list or {items:[...]})")
    ap.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY_PATH))
    args = ap.parse_args()
    taxonomy = load_taxonomy(Path(args.taxonomy))
    payload = json.loads(Path(args.items).read_text())
    items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    accepted, rejected, counts = validate_items(items, taxonomy)
    print(json.dumps({
        "total": accepted + rejected,
        "accepted": accepted,
        "rejected": rejected,
        "rejection_reasons": counts,
    }, indent=2))
    raise SystemExit(1 if rejected else 0)


if __name__ == "__main__":
    _cli()
