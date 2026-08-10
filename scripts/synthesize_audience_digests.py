"""Iteration I7: per-audience digest variants.

For every audience with a ranked_audience artifact, emits:
- artifacts/digests/<track>/<audience>/<date>.json   (structured digest)
- tracks/<track>/digests/<audience>/<date>.md         (rendered markdown)

The audience-scoped digest has a section-title-agnostic shape that matches
shared/digest_schema.md, so it drops into the existing email + telegram +
Logseq delivery paths. Each audience gets its own top_matches (top-N of
the ranked list), audience-labeled recommended_actions, and shared
source_notes / discovery_artifacts.

The default (non-audience) digest produced by the track's own
<track>_synthesize_digest.py continues to live at
artifacts/digests/<track>/<date>.json and remains the persona digest.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from digest_json import render_digest_markdown  # noqa: E402


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _audiences(root: Path, track: str, date: str) -> list[str]:
    base = root / "artifacts" / "ranked_audience" / track
    if not base.is_dir():
        return []
    out: list[str] = []
    for sub in sorted(base.iterdir()):
        if sub.is_dir() and (sub / f"{date}.json").is_file():
            out.append(sub.name)
    return out


def _source_notes(discovery: dict | None) -> list[dict]:
    if not discovery:
        return []
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
            "note": f"Enumerated {s.get('enumerated_jobs', 0)}; matched {s.get('matched_jobs', 0)}.",
        })
    return out


def _to_top_match(item: dict) -> dict:
    score = float(item.get("audience_score", item.get("confidence", 0.5)))
    return {
        "job_key": item.get("item_key"),
        "company": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "location": "content",
        "team_or_domain": item.get("topic", ""),
        "source": item.get("source_id", ""),
        "source_url": item.get("url", ""),
        "fit_score": round(score * 10, 1),
        "recommendation": "apply_now" if score >= 0.7 else "watch",
        "why_match": [
            f"audience_score: {score:.2f}",
            f"rank: {item.get('rank')}",
            f"selected: {'yes' if item.get('selected') else 'no (extrapolated)'}",
            item.get("rationale", ""),
        ],
        "concerns": [] if item.get("selected") else ["audience not declared on this item"],
    }


def _to_other(item: dict) -> dict:
    score = float(item.get("audience_score", item.get("confidence", 0.5)))
    return {
        "job_key": item.get("item_key"),
        "company": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "listing_url": item.get("url", ""),
        "source": item.get("source_id", ""),
        "fit_score": round(score * 10, 1),
        "recommendation": "watch",
        "short_note": f"{item.get('content_type', '')} · {item.get('topic', '')}",
    }


def synthesize_for_audience(
    track: str,
    audience: str,
    ranked: dict,
    discovery: dict | None,
    date: str,
    max_top: int,
    disc_relpath: str,
) -> dict:
    items = ranked.get("ranked", [])
    top = items[:max_top]
    rest = items[max_top:]
    run = {
        "kind": "initial",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "executive_summary": (
            f"{len(items)} items ranked for the {audience} audience; "
            f"{ranked.get('selected_items', 0)} explicitly named this audience; "
            f"top {len(top)} shown."
        ),
        "recommended_actions": [
            f"Review the top {len(top)} match(es) tuned for {audience}.",
            "The default persona digest for this track is at "
            f"artifacts/digests/{track}/{date}.json.",
        ],
        "top_matches": [_to_top_match(i) for i in top],
        "other_new_roles": [_to_other(i) for i in rest],
        "filtered_roles": [],
        "source_notes": _source_notes(discovery),
        "notes_for_next_run": [
            "Audience scoring is deterministic (classifier confidence + audience boost).",
            "LLM audience rerank belongs to I6+.",
        ],
        "discovery_artifacts": [disc_relpath] if disc_relpath else [],
    }
    return {
        "schema_version": 1,
        "track": track,
        "date": date,
        "audience": audience,
        "runs": [run],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--max-top", type=int, default=8)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    disc_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    discovery = _load(disc_path)
    disc_relpath = str(disc_path.relative_to(root)) if disc_path.is_file() else ""
    audiences = _audiences(root, args.track, args.date)
    if not audiences:
        print(f"no ranked_audience artifacts for {args.track}/{args.date} — nothing to do")
        return
    written = 0
    for aud in audiences:
        ranked_path = root / "artifacts" / "ranked_audience" / args.track / aud / f"{args.date}.json"
        ranked = _load(ranked_path)
        if not ranked:
            continue
        digest = synthesize_for_audience(args.track, aud, ranked, discovery, args.date, args.max_top, disc_relpath)
        out_json = root / "artifacts" / "digests" / args.track / aud / f"{args.date}.json"
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(digest, indent=2) + "\n")
        latest = out_json.parent / "latest.json"
        latest.write_text(json.dumps(digest, indent=2) + "\n")
        try:
            md = render_digest_markdown(digest)
            out_md = root / "tracks" / args.track / "digests" / aud / f"{args.date}.md"
            out_md.parent.mkdir(parents=True, exist_ok=True)
            out_md.write_text(md)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] markdown render failed for {aud}: {exc}", file=sys.stderr)
        written += 1
    print(f"wrote {written} audience digest(s) under artifacts/digests/{args.track}/<audience>/")


if __name__ == "__main__":
    main()
