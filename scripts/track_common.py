"""Small helpers shared across track pipeline scripts.

Kept intentionally minimal: only things used by two or more of
topic_watch_/market_watch_/career_watch_ classifiers and synthesizers, plus
synthesize_audience_digests.py. Anything track-specific stays in the
per-track module.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone


def iso_utc_now() -> str:
    """Second-precision UTC timestamp in the format the artifacts use."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def item_key(prefix: str, url: str, title: str) -> str:
    """Stable per-item key. `<prefix>-<12 hex chars of sha1(url|title)>`."""
    h = hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{h}"


def substring_match(text: str, needle: str) -> bool:
    """Case-insensitive substring test used by every classifier."""
    if not needle:
        return False
    return needle.lower() in (text or "").lower()


def word_boundary_match(text: str, needle: str) -> bool:
    """Case-insensitive word-boundary match. Used for tickers and short
    tokens where substring match would collide (e.g. `GS` vs `GSK`)."""
    if not text or not needle:
        return False
    return bool(re.search(r"\b" + re.escape(needle) + r"\b", text, re.IGNORECASE))


def source_notes_block(discovery: dict | None) -> list[dict]:
    """Convert a discovery artifact's per-source rows into digest source_notes."""
    if not discovery:
        return []
    out: list[dict] = []
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
            "note": (
                f"Enumerated {s.get('enumerated_jobs', 0)}; "
                f"matched {s.get('matched_jobs', 0)}."
            ),
        })
    return out
