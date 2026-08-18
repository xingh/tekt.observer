"""Content-item discovery for the topic_watch track (I2 preview).

The base discover_jobs.py pipeline is tuned for job listings and filters
candidates through job-title heuristics (engineer, researcher, ...) that
reject legitimate AI content titles. This script emits the same discovery
schema shape from a plain HTML page — every <a> inside a <ul> becomes a
candidate, filtered only by track_terms substring match. Later iterations
replace this with a real crawler/RSS/API layer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_config import load_sources_config  # noqa: E402


class _AnchorHarvester(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_a = False
        self.current_href: str = ""
        self.current_text_parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs):  # noqa: N802
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            self.in_a = True
            self.current_href = href
            self.current_text_parts = []

    def handle_endtag(self, tag: str) -> None:  # noqa: N802
        if tag == "a" and self.in_a:
            text = re.sub(r"\s+", " ", "".join(self.current_text_parts)).strip()
            if text and self.current_href:
                self.anchors.append((self.current_href, text))
            self.in_a = False
            self.current_href = ""
            self.current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_a:
            self.current_text_parts.append(data)


def _fetch(url: str) -> str:
    with urlopen(url) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _match_terms(title: str, terms: list[str]) -> list[str]:
    lo = title.lower()
    return [t for t in terms if t.lower() in lo]


def discover_source(source: dict, track_terms: list[str]) -> dict:
    src_url = source["url"]
    parser = _AnchorHarvester()
    html_text = _fetch(src_url)
    parser.feed(html_text)
    terms = list(dict.fromkeys(track_terms + (source.get("search_terms", {}) or {}).get("terms", [])))
    candidates: list[dict] = []
    enumerated = 0
    for href, title in parser.anchors:
        enumerated += 1
        absolute = urljoin(src_url, href)
        matched = _match_terms(title, terms) if terms else []
        if terms and not matched:
            continue
        candidates.append({
            "employer": source.get("name", ""),
            "title": title,
            "url": absolute,
            "source_url": src_url,
            "alternate_url": "",
            "location": "content",
            "remote": "unknown",
            "matched_terms": matched,
            "notes": "topic_watch_discover: <a> inside <ul>",
            "description": "",
            "description_truncated": False,
        })
    return {
        "source": source.get("name", ""),
        "source_url": src_url,
        "discovery_mode": source.get("discovery_mode", "html"),
        "cadence_group": source.get("cadence_group", "every_run"),
        "last_checked": None,
        "due_today": True,
        "status": "complete" if candidates else "partial",
        "listing_pages_scanned": 1,
        "search_terms_tried": terms,
        "result_pages_scanned": "local_filter=1",
        "direct_job_pages_opened": 0,
        "enumerated_jobs": enumerated,
        "matched_jobs": len(candidates),
        "limitations": [] if candidates else ["no term matches"],
        "candidates": candidates,
        "source_id": source.get("id", ""),
        "filters": source.get("filters", {}) or {},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root")
    ap.add_argument("--track", default="topic_watch")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    sources_path = root / "tracks" / args.track / "sources.json"
    config = json.loads(sources_path.read_text())
    track_terms = config.get("track_terms", []) or []
    per_source = [discover_source(s, track_terms) for s in config.get("sources", [])]
    artifact = {
        "schema_version": 1,
        "track": args.track,
        "today": args.date,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "discover",
        "sources": per_source,
    }
    out_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2) + "\n")
    latest = out_path.parent / "latest.json"
    latest.write_text(json.dumps(artifact, indent=2) + "\n")
    total = sum(s["matched_jobs"] for s in per_source)
    print(f"wrote {out_path} (matched {total} across {len(per_source)} source(s))")


if __name__ == "__main__":
    # source_config is imported for validation of sources.json shape but isn't
    # required for this discovery pass; keep import so failures surface early.
    _ = load_sources_config
    main()
