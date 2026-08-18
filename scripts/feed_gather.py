"""Feed-based discovery step, shared across topic-watch-style tracks.

Reads a source registry JSON (defaults to topic_watch; override with --registry),
fetches each source according to its `kind` (rss/atom/hn_algolia), normalises
entries into the discovery artifact schema, and writes
artifacts/discovery/<track>/<date>.json.

Used by topic_watch, market_watch, and any future feed-driven track. Stdlib
only. Degrades per-source: if a source fails, its entry lands with status
"failed" and empty candidates rather than crashing the whole run.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen

USER_AGENT = "tekt.observer/feed-gather (github.com/xingh/tekt.observer)"
DEFAULT_TIMEOUT = 15
MAX_PER_SOURCE = 20

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


def _date_window(for_date: str | None) -> tuple[int, int] | None:
    """Return (start_epoch, end_epoch) inclusive UTC window for a YYYY-MM-DD date."""
    if not for_date:
        return None
    try:
        d = datetime.strptime(for_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    start = int(d.timestamp())
    end = start + 86399
    return start, end


def _parse_published_epoch(published: str | None) -> int | None:
    """Best-effort parse of RSS pubDate / Atom published to epoch seconds."""
    if not published:
        return None
    published = published.strip()
    try:
        dt = parsedate_to_datetime(published)
        if dt is None:
            raise ValueError("empty")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(published, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    return None


def _rewrite_hn_url_for_window(url: str, window: tuple[int, int]) -> str:
    """Append numericFilters=created_at_i>=start,created_at_i<=end to a HN Algolia URL."""
    start, end = window
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["numericFilters"] = f"created_at_i>={start},created_at_i<={end}"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def _filter_by_window(items: list[dict], window: tuple[int, int] | None) -> list[dict]:
    if not window:
        return items
    start, end = window
    out = []
    for it in items:
        ep = _parse_published_epoch(it.get("published_at"))
        if ep is None:
            continue
        if start <= ep <= end:
            out.append(it)
    return out


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fmt_iso(dt: str | None) -> str | None:
    if not dt:
        return None
    return dt.strip()


def _parse_rss(body: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(body)
    channel = root.find("channel")
    container = channel if channel is not None else root
    items = []
    for item in container.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = _strip_html(item.findtext("description") or "")
        pub = _fmt_iso(item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date"))
        author = (item.findtext("{http://purl.org/dc/elements/1.1/}creator") or item.findtext("author") or "").strip()
        if title and link:
            items.append({"title": title, "url": link, "description": desc[:400], "published_at": pub, "author": author})
    return items[:MAX_PER_SOURCE]


def _parse_atom(body: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(body)
    items = []
    for entry in root.findall("atom:entry", _NS):
        title = (entry.findtext("atom:title", default="", namespaces=_NS) or "").strip()
        link_el = entry.find("atom:link", _NS)
        link = ""
        if link_el is not None:
            link = link_el.attrib.get("href", "").strip()
        if not link:
            for l in entry.findall("atom:link", _NS):
                href = l.attrib.get("href", "")
                if href:
                    link = href.strip()
                    break
        summary = _strip_html(entry.findtext("atom:summary", default="", namespaces=_NS) or "")
        if not summary:
            content_el = entry.find("atom:content", _NS)
            if content_el is not None:
                summary = _strip_html(content_el.text or "")
        published = _fmt_iso(entry.findtext("atom:published", default="", namespaces=_NS)
                             or entry.findtext("atom:updated", default="", namespaces=_NS))
        author = ""
        author_el = entry.find("atom:author/atom:name", _NS)
        if author_el is not None:
            author = (author_el.text or "").strip()
        if title and link:
            items.append({"title": title, "url": link, "description": summary[:400], "published_at": published, "author": author})
    return items[:MAX_PER_SOURCE]


def _parse_hn_algolia(body: bytes, source: dict) -> list[dict]:
    data = json.loads(body)
    items = []
    for hit in data.get("hits", []):
        title = (hit.get("title") or hit.get("story_title") or "").strip()
        link = (hit.get("url") or hit.get("story_url") or "").strip()
        if not link and hit.get("objectID"):
            link = f"https://news.ycombinator.com/item?id={hit['objectID']}"
        author = hit.get("author") or ""
        pub = hit.get("created_at") or None
        if title and link:
            items.append({"title": title, "url": link, "description": "", "published_at": pub, "author": author})
    return items[:MAX_PER_SOURCE]


def _gather_source(source: dict, window: tuple[int, int] | None = None) -> tuple[list[dict], list[str], str]:
    kind = source.get("kind")
    url = source["url"]
    # HN Algolia can filter server-side by created_at_i window.
    if kind == "hn_algolia" and window:
        url = _rewrite_hn_url_for_window(url, window)
    try:
        body = _fetch(url)
    except (URLError, HTTPError, socket.timeout, TimeoutError) as exc:
        return [], [f"fetch_error:{exc}"], "failed"
    try:
        if kind == "rss":
            items = _parse_rss(body, source)
        elif kind == "atom":
            items = _parse_atom(body, source)
        elif kind == "hn_algolia":
            items = _parse_hn_algolia(body, source)
        else:
            return [], [f"unknown_kind:{kind}"], "failed"
    except (ET.ParseError, json.JSONDecodeError, ValueError) as exc:
        return [], [f"parse_error:{exc}"], "failed"
    limitations: list[str] = []
    if window and kind in {"rss", "atom"}:
        before = len(items)
        items = _filter_by_window(items, window)
        if before and not items:
            limitations.append(f"window_filtered_out:{before}")
    status = "complete" if items else "partial"
    return items, limitations, status


def _to_candidates(items: list[dict], source: dict) -> list[dict]:
    hints = source.get("topic_hints", []) or []
    out = []
    for it in items:
        out.append({
            "employer": source.get("name", ""),
            "title": it["title"],
            "url": it["url"],
            "source_url": source["url"],
            "alternate_url": "",
            "location": "content",
            "remote": "unknown",
            "matched_terms": hints,
            "notes": f"kind={source['kind']}",
            "description": it.get("description", ""),
            "description_truncated": False,
            "published_at": it.get("published_at"),
            "author": it.get("author", ""),
            "topic_hints": hints,
        })
    return out


def gather_all(registry: dict, window: tuple[int, int] | None = None) -> list[dict]:
    per_source = []
    for source in registry.get("sources", []):
        items, limitations, status = _gather_source(source, window=window)
        cands = _to_candidates(items, source)
        per_source.append({
            "source": source["name"],
            "source_url": source["url"],
            "discovery_mode": source["kind"],
            "cadence_group": "every_run",
            "last_checked": None,
            "due_today": True,
            "status": status,
            "listing_pages_scanned": 1,
            "search_terms_tried": source.get("topic_hints", []),
            "result_pages_scanned": "feed=1",
            "direct_job_pages_opened": 0,
            "enumerated_jobs": len(items),
            "matched_jobs": len(cands),
            "limitations": limitations,
            "candidates": cands,
            "source_id": source["id"],
            "filters": {},
        })
        # progress line to stderr so live runs surface where the time went
        print(f"[gather] {source['id']}: {status} ({len(cands)} items)", file=sys.stderr)
    return per_source


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root")
    ap.add_argument("--track", default="topic_watch")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    default_registry = str(Path(__file__).resolve().parents[1] / "shared" / "schemas" / "topic_watch_source_registry.json")
    ap.add_argument("--registry", default=default_registry)
    ap.add_argument("--for-date", default="",
                    help="Fetch only entries whose pubDate falls in this UTC day (YYYY-MM-DD). "
                         "For hn_algolia sources the window is applied server-side; for rss/atom "
                         "the parsed entries are filtered client-side.")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    registry_path = Path(args.registry).resolve()
    registry = json.loads(registry_path.read_text())
    window = _date_window(args.for_date) if args.for_date else None
    per_source = gather_all(registry, window=window)
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
    (out_path.parent / "latest.json").write_text(json.dumps(artifact, indent=2) + "\n")
    total = sum(s["matched_jobs"] for s in per_source)
    ok = sum(1 for s in per_source if s["status"] == "complete")
    print(f"wrote {out_path} ({total} items across {ok}/{len(per_source)} sources)")


if __name__ == "__main__":
    main()
