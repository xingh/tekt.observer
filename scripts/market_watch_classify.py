"""Deterministic classifier for the market_watch track.

Reads a discovery artifact and classifies each candidate by:
- asset_class (public_equities / private_equity / fixed_income_macro) via keyword hits
- event_type (best-matching from the asset class's event catalogue)
- watchlist_matches (tickers + private companies + macro anchors present in title)
- is_portfolio_alert (any watchlist match found)

Ships a compiled-in default watchlist matching profile/personas/investor.md;
override via --watchlist path/to/watchlist.json.

Writes artifacts/organized/market_watch/<date>.json using the same schema
shape as ai_topics organized items (topic + content_type + audiences +
categories + confidence + rationale) plus market-specific extras
(watchlist_matches, is_portfolio_alert, asset_class, event_type). The
existing viewer + trends + report code works unchanged: asset_class is
mirrored into `topic` for grouping and event_type into `content_type` for
the badge.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_common import (  # noqa: E402
    item_key,
    iso_utc_now,
    substring_match,
    word_boundary_match,
)


DEFAULT_TAXONOMY = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "market_watch_taxonomy.json"

# Default watchlist mirroring profile/personas/investor.md. Users can
# override with --watchlist watchlist.json.
DEFAULT_WATCHLIST: dict = {
    "public_equities": {
        "tickers": [
            "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN",
            "AVGO", "TSM", "ASML", "BRK.B", "JPM", "GS",
            "CAT", "DE", "GE", "SIE.DE",
            "SPY", "QQQ", "IWM", "XLE", "XLI",
        ],
        # Non-ASCII tickers (Tokyo etc.)
        "ticker_regex": [r"\b7203\.T\b", r"\b8306\.T\b", r"\bASML\.AS\b"],
    },
    "private_equity": {
        "companies": [
            "Ravena Robotics", "Northwind Health", "Kessel Data",
            "Harborlight Bio", "Two Bridges Energy",
        ],
        "funds": ["Meridian Growth III", "Cardinal Ventures II"],
    },
    "fixed_income_macro": {
        "anchors": [
            "Fed", "FOMC", "ECB", "Bank of England", "BoE", "BoJ",
            "CPI", "PCE", "payrolls", "Treasury", "yield curve",
            "credit spread", "2s10s", "3m10y",
        ],
    },
}


# Re-exported for readability at call sites.
_match_word_boundary = word_boundary_match
_match_substring = substring_match


def _watchlist_hits(title: str, watchlist: dict) -> tuple[list[str], list[str]]:
    """Return (matched entities, matched asset classes)."""
    hits: list[str] = []
    classes: set[str] = set()
    pub = watchlist.get("public_equities", {}) or {}
    for tkr in pub.get("tickers", []) or []:
        if _match_word_boundary(title, tkr):
            hits.append(tkr)
            classes.add("public_equities")
    for pat in pub.get("ticker_regex", []) or []:
        if re.search(pat, title, re.IGNORECASE):
            hits.append(pat.strip(r"\b"))
            classes.add("public_equities")
    priv = watchlist.get("private_equity", {}) or {}
    for co in priv.get("companies", []) or []:
        if _match_substring(title, co):
            hits.append(co)
            classes.add("private_equity")
    for fund in priv.get("funds", []) or []:
        if _match_substring(title, fund):
            hits.append(fund)
            classes.add("private_equity")
    macro = watchlist.get("fixed_income_macro", {}) or {}
    for anchor in macro.get("anchors", []) or []:
        # Match anchors as whole words when they are short (Fed, BoE)
        if len(anchor) <= 4:
            if _match_word_boundary(title, anchor):
                hits.append(anchor)
                classes.add("fixed_income_macro")
        else:
            if _match_substring(title, anchor):
                hits.append(anchor)
                classes.add("fixed_income_macro")
    # dedupe preserving order
    seen = set()
    dedup: list[str] = []
    for h in hits:
        if h not in seen:
            dedup.append(h)
            seen.add(h)
    return dedup, sorted(classes)


def _classify_asset_class(title: str, taxonomy: dict, topic_hints: list[str]) -> tuple[str, list[str]]:
    """Best asset_class by keyword hits. Falls back to first topic_hint or public_equities."""
    scores: dict[str, list[str]] = {}
    for ac in taxonomy["asset_classes"]:
        hits = [kw for kw in ac["keywords"] if _match_substring(title, kw)]
        if hits:
            scores[ac["id"]] = hits
    if scores:
        best = max(scores.items(), key=lambda kv: len(kv[1]))
        return best[0], best[1]
    if topic_hints:
        return topic_hints[0], []
    return "public_equities", []


def _classify_event_type(title: str, asset_class_id: str, taxonomy: dict) -> str:
    ac = next((a for a in taxonomy["asset_classes"] if a["id"] == asset_class_id), None)
    if not ac:
        return "news"
    # Map keyword hits to plausible event types
    event_map = {
        "earnings": "earnings_release",
        "guidance": "guidance_change",
        "beat estimates": "earnings_release",
        "profit warning": "guidance_change",
        "downgrade": "rating_action",
        "upgrade": "rating_action",
        "rating": "rating_action",
        "sec charges": "regulatory_action",
        "settlement": "regulatory_action",
        "acquires": "m_and_a",
        "acquisition": "m_and_a",
        "merger": "m_and_a",
        "ceo": "exec_change",
        "cfo": "exec_change",
        "resigns": "exec_change",
        "activist": "activist_filing",
        "insider selling": "insider_transaction",
        "buyback": "product_launch_with_material_impact",
        "funding round": "funding_round",
        "series a": "funding_round",
        "series b": "funding_round",
        "series c": "funding_round",
        "series d": "funding_round",
        "seed round": "funding_round",
        "raises": "funding_round",
        "ipo": "exit_or_acquisition",
        "acquired by": "exit_or_acquisition",
        "down round": "down_round_signal",
        "fed": "central_bank_policy",
        "fomc": "central_bank_policy",
        "ecb": "central_bank_policy",
        "rate decision": "rate_decision",
        "rate cut": "rate_decision",
        "rate hike": "rate_decision",
        "cpi": "cpi_pce_print",
        "pce": "cpi_pce_print",
        "inflation": "cpi_pce_print",
        "payrolls": "payrolls_print",
        "yield curve": "yield_curve_shift",
        "credit spread": "credit_spread_shift",
        "quantitative": "qt_qe_change",
    }
    for kw, evt in event_map.items():
        if _match_substring(title, kw) and evt in ac.get("event_types", []):
            return evt
    # Fallback to first event_type of the class
    return (ac.get("event_types") or ["news"])[0]


def classify_candidates(discovery: dict, taxonomy: dict, watchlist: dict, date: str) -> dict:
    items: list[dict] = []
    for source in discovery.get("sources", []):
        source_id = source.get("source_id", "")
        topic_hints = source.get("search_terms_tried") or source.get("topic_hints") or []
        for cand in source.get("candidates", []):
            url = cand.get("url", "") or ""
            title = cand.get("title", "") or ""
            asset_class, ac_hits = _classify_asset_class(title, taxonomy, topic_hints)
            event_type = _classify_event_type(title, asset_class, taxonomy)
            wl_hits, wl_classes = _watchlist_hits(title, watchlist)
            # If watchlist implies a different class, prefer that
            if wl_classes and asset_class not in wl_classes:
                asset_class = wl_classes[0]
                event_type = _classify_event_type(title, asset_class, taxonomy)
            is_alert = bool(wl_hits)
            confidence = min(1.0, 0.4 + 0.15 * len(ac_hits) + 0.2 * min(len(wl_hits), 3))
            audiences = ["investors"]
            if asset_class == "private_equity":
                audiences.append("gps")
            if asset_class == "fixed_income_macro":
                audiences.append("allocators")
            items.append({
                "item_key": item_key("mw", url, title),
                "source_id": source_id,
                "url": url,
                "title": title,
                # Mirror asset_class into `topic` and event_type into
                # `content_type` so the shared viewer (ai_topics-shaped)
                # renders without changes.
                "topic": asset_class,
                "content_type": event_type,
                "categories": [asset_class],
                "audiences": audiences,
                "confidence": round(confidence, 2),
                "rationale": (
                    f"class_hits={ac_hits}; watchlist_hits={wl_hits}; "
                    f"event_type={event_type}"
                ),
                "asset_class": asset_class,
                "event_type": event_type,
                "watchlist_matches": wl_hits,
                "is_portfolio_alert": is_alert,
            })
    return {
        "schema_version": 1,
        "track": "market_watch",
        "date": date,
        "generated_at": iso_utc_now(),
        "items": items,
    }


def _load_watchlist(path: Path | None) -> dict:
    if path and path.is_file():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return DEFAULT_WATCHLIST


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", default="market_watch")
    ap.add_argument("--date", required=True)
    ap.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    ap.add_argument("--watchlist", default="", help="Optional watchlist.json override")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    disc_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    if not disc_path.is_file():
        sys.exit(f"missing discovery artifact: {disc_path}")
    taxonomy = json.loads(Path(args.taxonomy).read_text())
    watchlist = _load_watchlist(Path(args.watchlist) if args.watchlist else None)
    discovery = json.loads(disc_path.read_text())
    organized = classify_candidates(discovery, taxonomy, watchlist, args.date)
    out = root / "artifacts" / "organized" / args.track / f"{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(organized, indent=2) + "\n")
    alerts = sum(1 for i in organized["items"] if i["is_portfolio_alert"])
    print(f"wrote {out} ({len(organized['items'])} items; {alerts} portfolio alert(s))")


if __name__ == "__main__":
    main()
