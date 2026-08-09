"""Deterministic digest synthesizer for the ai_topics track (I7 preview).

Reads:
- artifacts/organized/ai_topics/<date>.json  (from ai_topics_classify.py)
- artifacts/discovery/ai_topics/<date>.json  (for source_notes)

Writes:
- artifacts/digests/ai_topics/<date>.json    (structured digest per shared/digest_schema.md)

Splits organized items into top_matches (items whose audiences include the
--audience flag, ranked by confidence) and other_new_roles (the rest). No LLM;
this is the deterministic scaffold that later iterations replace.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _summary(items: list[dict], audience: str) -> str:
    if not items:
        return "No items surfaced today."
    topics = sorted({i["topic"] for i in items})
    matches = sum(1 for i in items if audience in i.get("audiences", []))
    return (
        f"{len(items)} items surfaced across {len(topics)} topics; "
        f"{matches} match the {audience} audience lens."
    )


def _to_top_match(item: dict, index: int) -> dict:
    conf = float(item.get("confidence", 0.5))
    return {
        "job_key": item.get("item_key"),
        "company": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "location": "content",
        "team_or_domain": item.get("topic", ""),
        "source": item.get("source_id", ""),
        "source_url": item.get("url", ""),
        "fit_score": round(conf * 10, 1),
        "recommendation": "watch" if conf < 0.7 else "apply_now",
        "why_match": [
            f"topic={item.get('topic', '')}",
            f"audiences={','.join(item.get('audiences') or [])}",
            item.get("rationale", ""),
        ],
        "concerns": [] if conf >= 0.6 else ["low classifier confidence"],
    }


def _to_other(item: dict) -> dict:
    conf = float(item.get("confidence", 0.5))
    return {
        "job_key": item.get("item_key"),
        "company": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "source": item.get("source_id", ""),
        "fit_score": round(conf * 10, 1),
        "recommendation": "watch",
        "short_note": (
            f"{item.get('content_type', '')} in {item.get('topic', '')} "
            f"for {'/'.join(item.get('audiences') or [])}"
        ),
    }


def _source_notes(discovery: dict) -> list[dict]:
    out = []
    for s in discovery.get("sources", []):
        out.append({
            "source": s.get("source", ""),
            "discovery_mode": s.get("discovery_mode", ""),
            "status": s.get("status", ""),
            "listing_pages_scanned": s.get("listing_pages_scanned", ""),
            "search_terms_tried": s.get("search_terms_tried") or [],
            "result_pages_summary": s.get("result_pages_scanned", ""),
            "direct_job_pages_opened": s.get("direct_job_pages_opened", 0),
            "limitations": s.get("limitations") or [],
            "note": f"Enumerated {s.get('enumerated_jobs', 0)} candidates; matched {s.get('matched_jobs', 0)}.",
        })
    return out


def synthesize(
    organized: dict,
    discovery: dict,
    date: str,
    audience: str,
    max_top: int,
    discovery_artifact_relpath: str,
) -> dict:
    items = organized.get("items", [])
    matched = [i for i in items if audience in i.get("audiences", [])]
    unmatched = [i for i in items if audience not in i.get("audiences", [])]
    matched.sort(key=lambda i: (-float(i.get("confidence", 0.0)), i.get("title", "")))
    unmatched.sort(key=lambda i: (-float(i.get("confidence", 0.0)), i.get("title", "")))
    top = [_to_top_match(m, idx) for idx, m in enumerate(matched[:max_top])]
    other = [_to_other(m) for m in matched[max_top:] + unmatched]
    run = {
        "kind": "initial",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "executive_summary": _summary(items, audience),
        "recommended_actions": [
            f"Review the top {len(top)} match(es) for the {audience} lens.",
            "Skim the other items list for future reference; nothing time-sensitive.",
            "See artifacts/organized/ for the full classifier output.",
        ],
        "top_matches": top,
        "other_new_roles": other,
        "filtered_roles": [],
        "source_notes": _source_notes(discovery),
        "notes_for_next_run": [
            "Classifier is deterministic keyword-based (I1 scaffold); replace with LLM at I5.",
            "No filtering applied yet; category-level filters arrive with I5.",
        ],
        "discovery_artifacts": [discovery_artifact_relpath],
    }
    return {
        "schema_version": 1,
        "track": "ai_topics",
        "date": date,
        "runs": [run],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--track", default="ai_topics")
    ap.add_argument("--audience", default="architects", help="Audience id to prioritise in top_matches")
    ap.add_argument("--max-top", type=int, default=8)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    organized_path = root / "artifacts" / "organized" / args.track / f"{args.date}.json"
    discovery_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    if not organized_path.is_file():
        sys.exit(f"missing organized artifact: {organized_path}")
    if not discovery_path.is_file():
        sys.exit(f"missing discovery artifact: {discovery_path}")
    organized = json.loads(organized_path.read_text())
    discovery = json.loads(discovery_path.read_text())
    disc_relpath = str(discovery_path.relative_to(root))
    digest = synthesize(organized, discovery, args.date, args.audience, args.max_top, disc_relpath)
    out_path = root / "artifacts" / "digests" / args.track / f"{args.date}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(digest, indent=2) + "\n")
    latest = out_path.parent / "latest.json"
    latest.write_text(json.dumps(digest, indent=2) + "\n")
    print(f"wrote {out_path} (top={len(digest['runs'][0]['top_matches'])}, other={len(digest['runs'][0]['other_new_roles'])})")


if __name__ == "__main__":
    main()
