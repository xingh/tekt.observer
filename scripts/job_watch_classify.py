"""Deterministic classifier for the job_watch track.

Reads a discovery artifact and classifies each candidate job posting by:
- role_type (ai_engineer / prompt_engineer / ml_engineer / ai_researcher /
  ai_instructor / ai_devrel / ai_pm / ai_augmented_generalist)
- seniority audience (individual_contributor / senior_ic / tech_lead /
  manager / instructor) via seniority_keywords
- is_remote_friendly (bool)

Emits organized items in the ai_topics schema shape with job-specific
extras: role_type, seniority, is_remote_friendly, company. Mirrors
role_type into `topic` and hard-sets content_type="posting" so the
shared viewer renders unchanged.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_common import item_key, iso_utc_now, substring_match  # noqa: E402

DEFAULT_TAXONOMY = Path(__file__).resolve().parents[1] / "shared" / "schemas" / "job_watch_taxonomy.json"


COMPANY_HINT_RE = re.compile(r"^(?P<co>[A-Z][\w &.-]{1,40}?)\s*(?:\||:| is |,)")


_matches = substring_match


def _role_type(title: str, description: str, taxonomy: dict) -> tuple[str, list[str]]:
    hay = f"{title} {description}"
    scores: dict[str, list[str]] = {}
    for rt in taxonomy["role_types"]:
        hits = [k for k in rt["keywords"] if _matches(hay, k)]
        if hits:
            scores[rt["id"]] = hits
    if scores:
        best = max(scores.items(), key=lambda kv: len(kv[1]))
        return best[0], best[1]
    return "ai_augmented_generalist", []


def _seniority(title: str, description: str, taxonomy: dict) -> tuple[str, list[str]]:
    hay = f"{title} {description}".lower()
    for aud_id, kws in taxonomy.get("seniority_keywords", {}).items():
        hits = [k for k in kws if k in hay]
        if hits:
            return aud_id, hits
    return "senior_ic", []  # default assumption


def _is_remote(title: str, description: str, taxonomy: dict) -> bool:
    hay = f"{title} {description}".lower()
    return any(k in hay for k in taxonomy.get("remote_keywords", []))


def _company(title: str, source_id: str) -> str:
    """Best-effort company parse. HN 'Who is hiring' titles often start
    with '<Company> (YC S21) is hiring ...'; ai-jobs.net has '@ Company' style."""
    m = COMPANY_HINT_RE.match(title.strip())
    if m:
        return m.group("co").strip()
    if " at " in title:
        return title.split(" at ", 1)[1].strip().split("(")[0].strip()
    if " @ " in title:
        return title.split(" @ ", 1)[1].strip()
    return source_id or "unknown"


def classify_candidates(discovery: dict, taxonomy: dict, date: str) -> dict:
    items: list[dict] = []
    for source in discovery.get("sources", []):
        source_id = source.get("source_id", "")
        for cand in source.get("candidates", []):
            url = cand.get("url", "") or ""
            title = cand.get("title", "") or ""
            desc = cand.get("description", "") or ""
            role_type, role_hits = _role_type(title, desc, taxonomy)
            seniority, sen_hits = _seniority(title, desc, taxonomy)
            remote = _is_remote(title, desc, taxonomy)
            company = _company(title, source.get("source", source_id))
            audiences = [seniority]
            if role_type == "ai_instructor":
                audiences.append("instructor")
            confidence = min(1.0, 0.4 + 0.15 * len(role_hits) + 0.1 * len(sen_hits) + (0.1 if remote else 0))
            items.append({
                "item_key": item_key("jw", url, title),
                "source_id": source_id,
                "url": url,
                "title": title,
                "company": company,
                # Mirror role_type into `topic`, hard-set content_type so
                # the shared viewer renders without changes.
                "topic": role_type,
                "content_type": "posting",
                "categories": [role_type],
                "audiences": audiences,
                "confidence": round(confidence, 2),
                "rationale": (
                    f"role_hits={role_hits}; seniority_hits={sen_hits}; "
                    f"remote={remote}"
                ),
                "role_type": role_type,
                "seniority": seniority,
                "is_remote_friendly": remote,
            })
    return {
        "schema_version": 1,
        "track": "job_watch",
        "date": date,
        "generated_at": iso_utc_now(),
        "items": items,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--track", default="job_watch")
    ap.add_argument("--date", required=True)
    ap.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    disc_path = root / "artifacts" / "discovery" / args.track / f"{args.date}.json"
    if not disc_path.is_file():
        sys.exit(f"missing discovery artifact: {disc_path}")
    taxonomy = (json.loads(Path(args.taxonomy).read_text()) if args.taxonomy != str(DEFAULT_TAXONOMY)
                else resolved_classifier_taxonomy(root, args.track))
    discovery = json.loads(disc_path.read_text())
    organized = classify_candidates(discovery, taxonomy, args.date)
    out = root / "artifacts" / "organized" / args.track / f"{args.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(organized, indent=2) + "\n")
    remote = sum(1 for i in organized["items"] if i["is_remote_friendly"])
    print(f"wrote {out} ({len(organized['items'])} postings; {remote} remote-friendly)")


if __name__ == "__main__":
    main()
from portfolio_state import resolved_classifier_taxonomy
