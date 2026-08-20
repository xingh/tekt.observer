"""Per-URL metadata enrichment for any track's discovery artifact.

For each candidate URL in artifacts/discovery/<track>/<date>.json, fetches
the page (HEAD-like GET with a Range header when possible) and extracts
OpenGraph / Twitter / canonical / description meta tags plus published_time.
Writes the enrichment map to artifacts/enrichment/<track>/urls.json so
subsequent runs skip already-fetched URLs. Also patches the discovery
artifact in place, adding an `enrichment` key to each candidate.

Used by topic_watch, market_watch, and any jobwatch-style track that wants
OG images on its listings.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
import socket
import ssl
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

USER_AGENT = "tekt.observer/feed-enrich (github.com/xingh/tekt.observer)"
FETCH_TIMEOUT = 12
MAX_BYTES = 200_000  # only need the <head>
MAX_URLS = 60


class _MetaHarvester(HTMLParser):
    """Extract meta/link/title from <head>. Stops after </head>."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.done = False
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical: str = ""

    def handle_starttag(self, tag: str, attrs):  # noqa: N802
        if self.done:
            return
        if tag == "title":
            self.in_title = True
            return
        if tag == "meta":
            a = dict(attrs)
            key = (a.get("property") or a.get("name") or "").lower()
            val = a.get("content") or ""
            if key and val:
                self.meta[key] = val
            return
        if tag == "link":
            a = dict(attrs)
            if (a.get("rel") or "").lower() == "canonical" and a.get("href"):
                self.canonical = a["href"]
            return

    def handle_endtag(self, tag: str) -> None:  # noqa: N802
        if tag == "title":
            self.in_title = False
        if tag == "head":
            self.done = True

    def handle_data(self, data: str) -> None:
        if self.in_title and not self.done:
            self.title_parts.append(data)


def _fetch_head(url: str, timeout: int = FETCH_TIMEOUT) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8", "Range": f"bytes=0-{MAX_BYTES - 1}"}
    req = Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read(MAX_BYTES)


def enrich_url(url: str) -> dict:
    try:
        body = _fetch_head(url)
    except (URLError, HTTPError, socket.timeout, TimeoutError, ValueError, ConnectionError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    # Decode leniently
    try:
        text = body.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        text = body.decode("latin-1", errors="replace")
    # Only parse <head> to keep it fast
    head_end = text.lower().find("</head>")
    if head_end > 0:
        text = text[: head_end + len("</head>")]
    parser = _MetaHarvester()
    try:
        parser.feed(text)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"parse_error: {exc}"}
    m = parser.meta
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    return {
        "og_image": m.get("og:image") or m.get("twitter:image") or "",
        "og_title": m.get("og:title") or title,
        "og_description": m.get("og:description") or m.get("description") or m.get("twitter:description") or "",
        "og_site_name": m.get("og:site_name") or "",
        "og_type": m.get("og:type") or "",
        "canonical": parser.canonical or m.get("og:url") or "",
        "published_time": m.get("article:published_time") or m.get("og:updated_time") or "",
        "author": m.get("article:author") or m.get("author") or "",
    }


def enrich_discovery(discovery: dict, cache: dict[str, dict], max_urls: int, workers: int = 6) -> int:
    candidates = [candidate for source in discovery.get("sources", []) for candidate in source.get("candidates", [])]
    pending = list(dict.fromkeys(candidate.get("url") or "" for candidate in candidates if candidate.get("url") and candidate.get("url") not in cache))[:max_urls]
    if pending:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(pending))), thread_name_prefix="enrich") as executor:
            for index, (url, enriched) in enumerate(zip(pending, executor.map(enrich_url, pending)), start=1):
                cache[url] = enriched
                print(f"[enrich] ({index}/{len(pending)}) {url}", file=sys.stderr)
    for candidate in candidates:
        url = candidate.get("url") or ""
        if url:
            candidate["enrichment"] = cache.get(url, {"error": "budget_exhausted"})
    return len(pending)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root")
    ap.add_argument("--track", default="topic_watch")
    ap.add_argument("--date", required=True)
    ap.add_argument("--max-urls", type=int, default=MAX_URLS)
    ap.add_argument("--workers", type=int, default=6, help="Maximum concurrent metadata fetches")
    ap.add_argument("--refetch", action="store_true", help="Ignore cache and re-fetch every URL")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    disc_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    if not disc_path.is_file():
        sys.exit(f"missing discovery artifact: {disc_path}")
    cache_path = root / "artifacts" / "enrichment" / args.track / "urls.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, dict] = {}
    if cache_path.is_file() and not args.refetch:
        try:
            cache = json.loads(cache_path.read_text())
        except json.JSONDecodeError:
            cache = {}
    discovery = json.loads(disc_path.read_text())
    fetched = enrich_discovery(discovery, cache, args.max_urls, workers=args.workers)
    cache_path.write_text(json.dumps(cache, indent=2) + "\n")
    disc_path.write_text(json.dumps(discovery, indent=2) + "\n")
    latest = disc_path.parent / "latest.json"
    if latest.is_file():
        latest.write_text(json.dumps(discovery, indent=2) + "\n")
    print(f"enriched {fetched} new URLs; cache now has {len(cache)} entries at {cache_path}")


if __name__ == "__main__":
    main()
