#!/usr/bin/env python3
"""Generate built-in watcher runtime files from canonical .arkitype specs."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SOURCE_KINDS = {"rss", "atom", "hn_algolia"}
PRIMARY_DIMENSIONS = ("topics", "role_types", "asset_classes")
SPEC_ROOT = ".arkitype/watchers"
PREFS_MARKER_RE = re.compile(r"^<!-- Generated from (\.arkitype/watchers/[^;]+); do not edit directly\. -->$")


class WatcherSpecError(ValueError):
    pass


@dataclass(frozen=True)
class WatcherSpec:
    slug: str
    directory: Path
    metadata: dict[str, Any]
    taxonomy: dict[str, Any]
    registry: dict[str, Any]
    brief: str
    samples: list[dict[str, Any]]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise WatcherSpecError(f"missing watcher spec file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WatcherSpecError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WatcherSpecError(f"{path} must contain an object")
    return value


def _ids(rows: Any, field: str) -> set[str]:
    if not isinstance(rows, list): raise WatcherSpecError(f"{field} must be a list")
    values = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not SLUG_RE.fullmatch(row["id"]):
            raise WatcherSpecError(f"{field}[{index}].id must be a file-safe identifier")
        values.append(row["id"])
    if len(values) != len(set(values)): raise WatcherSpecError(f"{field} contains duplicate ids")
    return set(values)


def load_spec(directory: Path) -> WatcherSpec:
    metadata = _load_json(directory / "watcher.json")
    taxonomy = _load_json(directory / "taxonomy.json")
    registry = _load_json(directory / "sources.json")
    try: samples = json.loads((directory / "samples.json").read_text())
    except FileNotFoundError as exc: raise WatcherSpecError(f"missing watcher spec file: {directory / 'samples.json'}") from exc
    except json.JSONDecodeError as exc: raise WatcherSpecError(f"invalid JSON in {directory / 'samples.json'}: {exc}") from exc
    try: brief = (directory / "brief.md").read_text()
    except FileNotFoundError as exc: raise WatcherSpecError(f"missing watcher spec file: {directory / 'brief.md'}") from exc
    slug = metadata.get("slug")
    if metadata.get("schema_version") != 1 or metadata.get("kind") != "watcher":
        raise WatcherSpecError(f"{directory}/watcher.json requires schema_version 1 and kind watcher")
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug) or slug != directory.name:
        raise WatcherSpecError(f"watcher slug must be file-safe and match directory {directory.name!r}")
    if metadata.get("id") != slug: raise WatcherSpecError(f"{slug}: id must match slug")
    if not isinstance(metadata.get("order"), int): raise WatcherSpecError(f"{slug}: order must be an integer")
    audiences = _ids(taxonomy.get("audiences"), f"{slug}.taxonomy.audiences")
    if metadata.get("default_audience") not in audiences:
        raise WatcherSpecError(f"{slug}: default_audience must exist in taxonomy audiences")
    dimensions = [name for name in PRIMARY_DIMENSIONS if name in taxonomy]
    if len(dimensions) != 1: raise WatcherSpecError(f"{slug}: taxonomy needs exactly one primary dimension")
    topic_ids = _ids(taxonomy[dimensions[0]], f"{slug}.taxonomy.{dimensions[0]}")
    sources = registry.get("sources")
    source_ids = _ids(sources, f"{slug}.sources")
    if not source_ids: raise WatcherSpecError(f"{slug}: at least one source is required")
    for source in sources:
        if source.get("kind") not in SOURCE_KINDS: raise WatcherSpecError(f"{slug}: invalid source kind")
        if not isinstance(source.get("url"), str) or not source["url"].startswith(("http://", "https://")):
            raise WatcherSpecError(f"{slug}: source URLs must be HTTP(S)")
        hints = source.get("topic_hints", [])
        if not isinstance(hints, list) or set(hints) - topic_ids:
            raise WatcherSpecError(f"{slug}: source topic_hints must reference the primary taxonomy dimension")
    if not isinstance(samples, list) or not samples: raise WatcherSpecError(f"{slug}: samples must be a non-empty list")
    sample_ids = set()
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict) or not isinstance(sample.get("item_key"), str):
            raise WatcherSpecError(f"{slug}.samples[{index}] must have an item_key")
        if sample["item_key"] in sample_ids: raise WatcherSpecError(f"{slug}: duplicate sample item_key")
        sample_ids.add(sample["item_key"])
        if set(sample.get("topic_ids", [])) - topic_ids: raise WatcherSpecError(f"{slug}: sample topics must exist in taxonomy")
        if set(sample.get("audiences", [])) - audiences: raise WatcherSpecError(f"{slug}: sample audiences must exist in taxonomy")
    if not brief.endswith("\n"): brief += "\n"
    return WatcherSpec(slug, directory, metadata, taxonomy, registry, brief, samples)


def discover_specs(root: Path) -> list[WatcherSpec]:
    base = root / ".arkitype" / "watchers"
    specs = [load_spec(path) for path in sorted(base.iterdir()) if path.is_dir()]
    slugs = [spec.slug for spec in specs]
    if not specs: raise WatcherSpecError("no watcher specs found")
    if len(slugs) != len(set(slugs)): raise WatcherSpecError("duplicate watcher slugs")
    return sorted(specs, key=lambda spec: (spec.metadata["order"], spec.slug))


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def rendered_outputs(root: Path, specs: list[WatcherSpec]) -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    for spec in specs:
        source_root = f"{SPEC_ROOT}/{spec.slug}"
        track = {key: value for key, value in spec.metadata.items() if key not in {"kind", "slug", "order"}}
        track["generated_from"] = f"{source_root}/watcher.json"
        taxonomy = {**spec.taxonomy, "generated_from": f"{source_root}/taxonomy.json"}
        registry = {**spec.registry, "generated_from": f"{source_root}/sources.json"}
        prefs = f"<!-- Generated from {source_root}/brief.md; do not edit directly. -->\n\n{spec.brief}"
        outputs[root / "tracks" / spec.slug / "track.json"] = _json_text(track)
        outputs[root / "tracks" / spec.slug / "prefs.md"] = prefs
        outputs[root / "shared" / "schemas" / f"{spec.slug}_taxonomy.json"] = _json_text(taxonomy)
        outputs[root / "shared" / "schemas" / f"{spec.slug}_source_registry.json"] = _json_text(registry)
    return outputs


def write_outputs(outputs: dict[Path, str]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def check_outputs(root: Path, outputs: dict[Path, str]) -> bool:
    clean = True
    for path, expected in outputs.items():
        actual = path.read_text() if path.exists() else ""
        if actual == expected: continue
        clean = False
        label = str(path.relative_to(root))
        sys.stderr.writelines(difflib.unified_diff(actual.splitlines(True), expected.splitlines(True),
                                                   fromfile=label, tofile=f"{label} (generated)"))
    expected_paths = set(outputs)
    candidates = list((root / "tracks").glob("*/track.json"))
    candidates.extend((root / "tracks").glob("*/prefs.md"))
    candidates.extend((root / "shared" / "schemas").glob("*_taxonomy.json"))
    candidates.extend((root / "shared" / "schemas").glob("*_source_registry.json"))
    for path in sorted(set(candidates) - expected_paths):
        try:
            if path.suffix == ".md":
                first_line = path.read_text().splitlines()[0]
                generated = PREFS_MARKER_RE.fullmatch(first_line) is not None
            else:
                value = json.loads(path.read_text())
                source = value.get("generated_from") if isinstance(value, dict) else None
                generated = isinstance(source, str) and source.startswith(f"{SPEC_ROOT}/")
        except (IndexError, OSError, json.JSONDecodeError):
            generated = False
        if generated:
            clean = False
            print(f"orphaned generated watcher output: {path.relative_to(root)}", file=sys.stderr)
    return clean


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--check", action="store_true", help="Fail if generated outputs are stale")
    parser.add_argument("--list", action="store_true", help="Print canonical watcher slugs")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        specs = discover_specs(root)
        outputs = rendered_outputs(root, specs)
    except WatcherSpecError as exc:
        print(f"generate_watchers.py: {exc}", file=sys.stderr)
        return 2
    if args.list:
        print("\n".join(spec.slug for spec in specs))
    elif args.check:
        if not check_outputs(root, outputs): return 1
        print("Watcher runtime files are up to date.")
    else:
        write_outputs(outputs)
        print(f"Generated {len(outputs)} watcher runtime files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
