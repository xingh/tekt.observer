#!/usr/bin/env python3
"""Create a deterministic, viewable workspace from canonical watcher specs."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

from generate_watchers import discover_specs


def seed(repo_root: Path, output_root: Path, run_date: str) -> Path:
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    if output_root in {repo_root, Path(output_root.anchor)}:
        raise ValueError("starter workspace output must not be the repository or filesystem root")
    if output_root.exists():
        shutil.rmtree(output_root)
    for spec in discover_specs(repo_root):
        track, items = spec.slug, spec.samples
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
