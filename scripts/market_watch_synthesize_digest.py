"""Deterministic digest synthesizer for the market_watch track.

Reads the market_watch organized artifact (from market_watch_classify.py)
and produces the structured digest per shared/digest_schema.md, with two
prioritised buckets:

- Portfolio alerts (is_portfolio_alert=True) -> top_matches, sorted by
  confidence. Each carries watchlist_matches + event_type in the why bullets.
- Everything else -> other_new_roles, providing situational awareness.

The report page renders these as "Top matches" and "All items by topic"
respectively, with cards, OG images, and topic grouping.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_common import iso_utc_now, source_notes_block  # noqa: E402


def _summary(items: list[dict], alerts: int, alert_urls: int) -> str:
    if not items:
        return "No items surfaced today."
    return (
        f"{len(items)} items surfaced; {alerts} named a watchlist entity "
        f"(portfolio alert), {alert_urls} unique alert URLs. Remaining items "
        f"are for situational awareness."
    )


def _to_top_match(item: dict) -> dict:
    conf = float(item.get("confidence", 0.5))
    matches = item.get("watchlist_matches") or []
    event = item.get("event_type") or ""
    ac = item.get("asset_class") or item.get("topic") or ""
    return {
        "job_key": item.get("item_key"),
        "company": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "location": "market_news",
        "team_or_domain": ac,
        "source": item.get("source_id", ""),
        "source_url": item.get("url", ""),
        "fit_score": round(conf * 10, 1),
        "recommendation": "apply_now" if conf >= 0.7 else "watch",
        "why_match": [
            f"watchlist: {', '.join(matches)}" if matches else "no direct watchlist hit",
            f"asset_class: {ac}",
            f"event_type: {event}",
        ],
        "concerns": [] if conf >= 0.6 else ["low classifier confidence"],
    }


def _to_other(item: dict) -> dict:
    conf = float(item.get("confidence", 0.5))
    ac = item.get("asset_class") or item.get("topic") or ""
    event = item.get("event_type") or ""
    return {
        "job_key": item.get("item_key"),
        "company": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "source": item.get("source_id", ""),
        "fit_score": round(conf * 10, 1),
        "recommendation": "watch",
        "short_note": f"{event or 'news'} · {ac}",
    }


_source_notes = source_notes_block


def synthesize(organized: dict, discovery: dict, date: str, disc_relpath: str) -> dict:
    items = organized.get("items", [])
    alerts = [i for i in items if i.get("is_portfolio_alert")]
    others = [i for i in items if not i.get("is_portfolio_alert")]
    alerts.sort(key=lambda i: (-float(i.get("confidence", 0.0)), i.get("title", "")))
    others.sort(key=lambda i: (-float(i.get("confidence", 0.0)), i.get("title", "")))
    unique_alert_urls = len({i.get("url") for i in alerts})
    run = {
        "kind": "initial",
        "generated_at": iso_utc_now(),
        "executive_summary": _summary(items, len(alerts), unique_alert_urls),
        "recommended_actions": [
            f"Review the {len(alerts)} portfolio alert(s) before market open.",
            "Skim situational awareness for macro / policy drift.",
            "Update watchlist in profile/personas/investor.md as positions change.",
        ],
        "top_matches": [_to_top_match(i) for i in alerts],
        "other_new_roles": [_to_other(i) for i in others],
        "filtered_roles": [],
        "source_notes": _source_notes(discovery),
        "notes_for_next_run": [
            "Classifier is deterministic keyword + watchlist matching (I5 scaffold).",
            "Cross-source URL detection lives in artifacts/trends/market_watch/<date>.json.",
        ],
        "discovery_artifacts": [disc_relpath],
    }
    return {
        "schema_version": 1,
        "track": "market_watch",
        "date": date,
        "runs": [run],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", default="market_watch")
    ap.add_argument("--date", required=True)
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
    digest = synthesize(organized, discovery, args.date, str(disc_path.relative_to(root)))
    out = root / "artifacts" / "digests" / args.track / f"{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(digest, indent=2) + "\n")
    (out.parent / "latest.json").write_text(json.dumps(digest, indent=2) + "\n")
    r = digest["runs"][0]
    print(f"wrote {out} (portfolio_alerts={len(r['top_matches'])}, situational={len(r['other_new_roles'])})")


if __name__ == "__main__":
    main()
