"""Per-audience rerank stage (I6).

Reads artifacts/organized/<track>/<date>.json and the track taxonomy at
shared/schemas/<track>_taxonomy.json. For every audience declared in the
taxonomy, writes:

  artifacts/ranked_audience/<track>/<audience>/<date>.json

Each ranked entry is the organized item plus:
  - audience_score: 0..1
  - rank: 1-based position for this audience
  - selected: True if the audience is one of the item's declared audiences

Scoring is deterministic and cheap (audience_score = confidence * boost).
LLM-scored rerank belongs to I6+.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_taxonomy_audiences(root: Path, track: str) -> list[dict]:
    tax_path = root / "shared" / "schemas" / f"{track}_taxonomy.json"
    if not tax_path.is_file():
        return []
    try:
        data = json.loads(tax_path.read_text())
    except json.JSONDecodeError:
        return []
    return data.get("audiences") or []


def rerank_for_audience(items: list[dict], audience_id: str) -> list[dict]:
    scored: list[dict] = []
    for item in items:
        conf = float(item.get("confidence", 0.5))
        item_audiences = set(item.get("audiences") or [])
        selected = audience_id in item_audiences
        # Audience-lens boost: strong match if declared, dampened otherwise.
        boost = 1.5 if selected else 0.55
        # Cross-boost when item names watchlist / portfolio-alert flag applies
        if item.get("is_portfolio_alert") and audience_id in {"investors", "portfolio_managers", "allocators"}:
            boost += 0.25
        score = min(1.0, conf * boost)
        entry = dict(item)
        entry["audience"] = audience_id
        entry["audience_score"] = round(score, 3)
        entry["selected"] = selected
        scored.append(entry)
    scored.sort(key=lambda x: (-x["audience_score"], x.get("title", "")))
    for i, x in enumerate(scored, start=1):
        x["rank"] = i
    return scored


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", required=True)
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    org_path = root / "artifacts" / "organized" / args.track / f"{args.date}.json"
    if not org_path.is_file():
        sys.exit(f"missing organized artifact: {org_path}")
    audiences = _load_taxonomy_audiences(root, args.track)
    if not audiences:
        # Fallback: infer audiences from organized items' audiences field.
        org = json.loads(org_path.read_text())
        seen: set[str] = set()
        for it in org.get("items", []):
            for a in it.get("audiences") or []:
                seen.add(a)
        audiences = [{"id": a, "label": a.replace("_", " ").title()} for a in sorted(seen)]
    if not audiences:
        sys.exit("no audiences in taxonomy or organized items")

    organized = json.loads(org_path.read_text())
    items = organized.get("items", [])
    written = 0
    for aud in audiences:
        aud_id = aud["id"]
        ranked = rerank_for_audience(items, aud_id)
        out = root / "artifacts" / "ranked_audience" / args.track / aud_id / f"{args.date}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "track": args.track,
            "audience": aud_id,
            "date": args.date,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_items": len(ranked),
            "selected_items": sum(1 for r in ranked if r["selected"]),
            "ranked": ranked,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n")
        written += 1
    print(f"wrote {written} audience rerank file(s) for {args.track}/{args.date}")


if __name__ == "__main__":
    main()
