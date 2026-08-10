"""Iteration I8: feedback loop primitives.

Feedback events are stored as append-only JSON lines at
artifacts/feedback/<track>/<audience>/events.jsonl. Any writer (the
serve_html.py POST endpoint, a CLI, an external process) can append; readers
never mutate.

Event shape (v1):
  {
    "ts":       "2026-08-10T15:22:11Z",
    "track":    "ai_topics",
    "audience": "architects",
    "item_key": "ai-6c…",
    "url":      "https://…",
    "action":   "save" | "hide" | "click" | "note",
    "note":     "optional freeform"
  }

Consumers:
- scripts/track_rerank.py --with-feedback re-runs rerank with per-item
  boosts/penalties derived from these events.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_common import iso_utc_now  # noqa: E402

VALID_ACTIONS = {"save", "hide", "click", "note"}

# Applied by track_rerank when reading events.
BOOST_PER_ACTION = {
    "save": 0.20,
    "click": 0.05,
    "note": 0.10,
    "hide": -0.35,
}


def events_path(root: Path, track: str, audience: str) -> Path:
    return root / "artifacts" / "feedback" / track / audience / "events.jsonl"


def append_event(root: Path, event: dict) -> Path:
    for req in ("track", "audience", "item_key", "action"):
        if not event.get(req):
            raise ValueError(f"missing required field: {req}")
    if event["action"] not in VALID_ACTIONS:
        raise ValueError(f"unknown action: {event['action']} (allowed: {sorted(VALID_ACTIONS)})")
    event.setdefault("ts", iso_utc_now())
    path = events_path(root, event["track"], event["audience"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def load_events(root: Path, track: str, audience: str) -> list[dict]:
    path = events_path(root, track, audience)
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def per_item_boosts(events: list[dict]) -> dict[str, float]:
    """Aggregate boosts per item_key. Later events for the same item override
    earlier ones only when the more recent action is stronger (larger absolute
    value) — so a hide after a save counts as hide, but a click after a save
    stays as save."""
    latest: dict[str, tuple[str, str]] = {}  # item_key -> (action, ts)
    for e in events:
        key = e.get("item_key")
        action = e.get("action")
        ts = e.get("ts", "")
        if not key or action not in BOOST_PER_ACTION:
            continue
        prev = latest.get(key)
        if prev is None:
            latest[key] = (action, ts)
            continue
        prev_action, prev_ts = prev
        # More recent event wins if it is a stronger signal.
        if ts > prev_ts and abs(BOOST_PER_ACTION[action]) >= abs(BOOST_PER_ACTION[prev_action]):
            latest[key] = (action, ts)
    boosts: dict[str, float] = defaultdict(float)
    for key, (action, _) in latest.items():
        boosts[key] = BOOST_PER_ACTION[action]
    return dict(boosts)


def _cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="Append one feedback event")
    a.add_argument("--track", required=True)
    a.add_argument("--audience", required=True)
    a.add_argument("--item-key", required=True)
    a.add_argument("--action", required=True, choices=sorted(VALID_ACTIONS))
    a.add_argument("--url", default="")
    a.add_argument("--note", default="")

    r = sub.add_parser("summary", help="Show aggregated per-item boosts")
    r.add_argument("--track", required=True)
    r.add_argument("--audience", required=True)

    args = ap.parse_args()
    root = Path(args.root).resolve()
    if args.cmd == "append":
        event = {
            "track": args.track,
            "audience": args.audience,
            "item_key": args.item_key,
            "action": args.action,
            "url": args.url,
            "note": args.note,
        }
        path = append_event(root, event)
        print(f"appended to {path}")
    else:
        events = load_events(root, args.track, args.audience)
        boosts = per_item_boosts(events)
        print(json.dumps({
            "track": args.track,
            "audience": args.audience,
            "events": len(events),
            "unique_items": len(boosts),
            "boosts": boosts,
        }, indent=2))


if __name__ == "__main__":
    _cli()
