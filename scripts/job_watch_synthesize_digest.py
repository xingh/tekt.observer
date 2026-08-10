"""Deterministic digest synthesizer for the job_watch track.

Reads artifacts/organized/job_watch/<date>.json and produces the structured
digest with top_matches ranked by confidence (best AI-enabled fits at top)
and other_new_roles for the remainder, grouped conceptually by role_type.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_common import iso_utc_now, source_notes_block  # noqa: E402


def _summary(items: list[dict], remote_count: int) -> str:
    if not items:
        return "No AI-enabled postings surfaced today."
    from collections import Counter
    per_role = Counter(i["role_type"] for i in items)
    top_role = per_role.most_common(1)[0]
    return (
        f"{len(items)} postings surfaced; {remote_count} remote-friendly. "
        f"Most common role_type today: {top_role[0]} ({top_role[1]})."
    )


def _to_top_match(item: dict) -> dict:
    conf = float(item.get("confidence", 0.5))
    remote_str = "remote" if item.get("is_remote_friendly") else "location unspecified"
    return {
        "job_key": item.get("item_key"),
        "company": item.get("company", item.get("source_id", "unknown")),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "location": remote_str,
        "team_or_domain": item.get("role_type", ""),
        "source": item.get("source_id", ""),
        "source_url": item.get("url", ""),
        "fit_score": round(conf * 10, 1),
        "recommendation": "apply_now" if conf >= 0.7 else "watch",
        "why_match": [
            f"role_type: {item.get('role_type', '')}",
            f"seniority: {item.get('seniority', '')}",
            f"is_remote_friendly: {item.get('is_remote_friendly')}",
            item.get("rationale", ""),
        ],
        "concerns": [] if conf >= 0.6 else ["low classifier confidence"],
    }


def _to_other(item: dict) -> dict:
    conf = float(item.get("confidence", 0.5))
    return {
        "job_key": item.get("item_key"),
        "company": item.get("company", item.get("source_id", "unknown")),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "source": item.get("source_id", ""),
        "fit_score": round(conf * 10, 1),
        "recommendation": "watch",
        "short_note": f"{item.get('role_type', '')} · {item.get('seniority', '')}",
    }


_source_notes = source_notes_block


def synthesize(organized: dict, discovery: dict, date: str, max_top: int, disc_relpath: str) -> dict:
    items = organized.get("items", [])
    items.sort(key=lambda i: (-float(i.get("confidence", 0.0)), i.get("title", "")))
    remote = sum(1 for i in items if i.get("is_remote_friendly"))
    top = items[:max_top]
    rest = items[max_top:]
    run = {
        "kind": "initial",
        "generated_at": iso_utc_now(),
        "executive_summary": _summary(items, remote),
        "recommended_actions": [
            f"Review the top {len(top)} AI-enabled posting(s) surfaced today.",
            "Per-audience (seniority) variants live under artifacts/digests/job_watch/<audience>/.",
        ],
        "top_matches": [_to_top_match(i) for i in top],
        "other_new_roles": [_to_other(i) for i in rest],
        "filtered_roles": [],
        "source_notes": _source_notes(discovery),
        "notes_for_next_run": [
            "Classifier is deterministic keyword-based (I1 scaffold).",
            "Integrating ATS-specific providers (Greenhouse/Lever/Ashby) is a later iteration.",
        ],
        "discovery_artifacts": [disc_relpath] if disc_relpath else [],
    }
    return {
        "schema_version": 1,
        "track": "job_watch",
        "date": date,
        "runs": [run],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", default="job_watch")
    ap.add_argument("--date", required=True)
    ap.add_argument("--max-top", type=int, default=8)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    org_path = root / "artifacts" / "organized" / args.track / f"{args.date}.json"
    disc_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    if not org_path.is_file():
        sys.exit(f"missing organized artifact: {org_path}")
    if not disc_path.is_file():
        sys.exit(f"missing discovery artifact: {disc_path}")
    organized = json.loads(org_path.read_text())
    discovery = json.loads(disc_path.read_text())
    digest = synthesize(organized, discovery, args.date, args.max_top, str(disc_path.relative_to(root)))
    out = root / "artifacts" / "digests" / args.track / f"{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(digest, indent=2) + "\n")
    (out.parent / "latest.json").write_text(json.dumps(digest, indent=2) + "\n")
    r = digest["runs"][0]
    print(f"wrote {out} (top={len(r['top_matches'])}, other={len(r['other_new_roles'])})")


if __name__ == "__main__":
    main()
