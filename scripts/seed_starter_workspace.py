#!/usr/bin/env python3
"""Create a deterministic, viewable workspace for the three starter workflows."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path


SAMPLE_ITEMS = {
    "ai_topics": [
        {
            "item_key": "sample-context-memory",
            "title": "Designing durable context and memory for agent workflows",
            "url": "https://example.com/tekt-observer/ai-context-memory",
            "description": "A starter signal about context graphs, retrieval, and durable agent memory.",
            "topic": "ai_knowledge_memory",
            "topic_ids": ["ai_knowledge_memory"],
            "content_type": "post",
            "audiences": ["builders", "architects"],
            "sample": True,
        },
        {
            "item_key": "sample-open-agent-tools",
            "title": "Open agent tooling moves from demos to operating patterns",
            "url": "https://example.com/tekt-observer/open-agent-tools",
            "description": "A starter signal about open-source harnesses, tools, and fleet operations.",
            "topic": "open_source_ai",
            "topic_ids": ["open_source_ai", "ai_capabilities"],
            "content_type": "resource",
            "audiences": ["builders", "operators", "leaders"],
            "sample": True,
        },
    ],
    "market_watch": [
        {
            "item_key": "sample-central-bank",
            "title": "Central-bank guidance shifts the near-term rate outlook",
            "url": "https://example.com/tekt-observer/central-bank-guidance",
            "description": "A starter macro signal showing how policy news appears in the portfolio inbox.",
            "topic": "fixed_income_macro",
            "topic_ids": ["fixed_income_macro"],
            "content_type": "central_bank_policy",
            "audiences": ["investors", "portfolio_managers", "allocators"],
            "sample": True,
        },
        {
            "item_key": "sample-acquisition",
            "title": "Strategic acquisition changes a software market's competitive map",
            "url": "https://example.com/tekt-observer/strategic-acquisition",
            "description": "A starter company signal illustrating acquisition and portfolio-alert classification.",
            "topic": "public_equities",
            "topic_ids": ["public_equities"],
            "content_type": "m_and_a",
            "audiences": ["investors", "gps", "lps"],
            "sample": True,
        },
    ],
    "job_watch": [
        {
            "item_key": "sample-ai-platform-engineer",
            "title": "Senior AI Platform Engineer",
            "url": "https://example.com/tekt-observer/ai-platform-engineer",
            "description": "A starter role focused on production LLM systems, retrieval, and platform reliability.",
            "topic": "ai_engineer",
            "topic_ids": ["ai_engineer"],
            "content_type": "posting",
            "audiences": ["senior_ic", "tech_lead"],
            "sample": True,
        },
        {
            "item_key": "sample-ai-instructor",
            "title": "Applied AI Instructor",
            "url": "https://example.com/tekt-observer/applied-ai-instructor",
            "description": "A starter role for hands-on AI curriculum design and live technical teaching.",
            "topic": "ai_instructor",
            "topic_ids": ["ai_instructor"],
            "content_type": "posting",
            "audiences": ["instructor", "individual_contributor"],
            "sample": True,
        },
    ],
}


def seed(repo_root: Path, output_root: Path, run_date: str) -> Path:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    if output_root in {repo_root, Path(output_root.anchor)}:
        raise ValueError("starter workspace output must not be the repository or filesystem root")
    if output_root.exists():
        shutil.rmtree(output_root)
    for track, items in SAMPLE_ITEMS.items():
        source = repo_root / "tracks" / track
        target = output_root / "tracks" / track
        target.mkdir(parents=True, exist_ok=True)
        for name in ("track.json", "prefs.md"):
            shutil.copy2(source / name, target / name)
        artifact = {
            "schema_version": 1,
            "track": track,
            "date": run_date,
            "generated_at": f"{run_date}T09:00:00Z",
            "mode": "starter_sample",
            "items": [{**item, "published_at": f"{run_date}T08:00:00Z"} for item in items],
        }
        path = output_root / "artifacts" / "organized" / track / f"{run_date}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact, indent=2) + "\n")
    return output_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--out", default="tests/tmp/starter-workflows", help="Workspace to replace")
    parser.add_argument("--date", default=date.today().isoformat(), help="Sample date")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.out)
    if not output.is_absolute():
        output = root / output
    print(f"seeded starter workspace at {seed(root, output, args.date)}")


if __name__ == "__main__":
    main()
