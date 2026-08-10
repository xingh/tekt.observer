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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_common import iso_utc_now  # noqa: E402
from track_feedback import load_events, per_item_boosts  # noqa: E402


def _load_taxonomy_audiences(root: Path, track: str) -> list[dict]:
    tax_path = root / "shared" / "schemas" / f"{track}_taxonomy.json"
    if not tax_path.is_file():
        return []
    try:
        data = json.loads(tax_path.read_text())
    except json.JSONDecodeError:
        return []
    return data.get("audiences") or []


def rerank_for_audience(
    items: list[dict],
    audience_id: str,
    feedback_boosts: dict[str, float] | None = None,
) -> list[dict]:
    boosts = feedback_boosts or {}
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
        feedback_delta = boosts.get(item.get("item_key", ""), 0.0)
        score = max(0.0, min(1.0, conf * boost + feedback_delta))
        entry = dict(item)
        entry["audience"] = audience_id
        entry["audience_score"] = round(score, 3)
        entry["selected"] = selected
        if feedback_delta:
            entry["feedback_delta"] = round(feedback_delta, 3)
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
    ap.add_argument("--with-feedback", action="store_true",
                    help="Apply per-item boosts/penalties from artifacts/feedback/<track>/<audience>/events.jsonl")
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
    total_feedback_items = 0
    for aud in audiences:
        aud_id = aud["id"]
        events = load_events(root, args.track, aud_id) if args.with_feedback else []
        boosts = per_item_boosts(events) if events else {}
        total_feedback_items += len(boosts)
        ranked = rerank_for_audience(items, aud_id, feedback_boosts=boosts)
        out = root / "artifacts" / "ranked_audience" / args.track / aud_id / f"{args.date}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "track": args.track,
            "audience": aud_id,
            "date": args.date,
            "generated_at": iso_utc_now(),
            "total_items": len(ranked),
            "selected_items": sum(1 for r in ranked if r["selected"]),
            "feedback_applied_items": len(boosts),
            "ranked": ranked,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n")
        written += 1
    print(
        f"wrote {written} audience rerank file(s) for {args.track}/{args.date}"
        + (f"; feedback applied to {total_feedback_items} item(s)" if args.with_feedback else "")
    )


if __name__ == "__main__":
    main()
