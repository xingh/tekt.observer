#!/usr/bin/env python3
"""Validated local portfolio state and cross-track item projection."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

from source_config import file_lock, write_json_atomic

ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
TRACK_STATUSES = {"draft", "active", "archived"}


class PortfolioStateError(ValueError):
    pass


def _id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise PortfolioStateError(f"{field} must match {ID_RE.pattern}")
    return value


def _text(value: Any, field: str, *, optional: bool = False) -> str:
    if optional and value is None:
        return ""
    if not isinstance(value, str) or (not optional and not value.strip()):
        raise PortfolioStateError(f"{field} must be a non-empty string")
    return value.strip()


def _ids(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise PortfolioStateError(f"{field} must be a list")
    result = [_id(v, f"{field}[{i}]") for i, v in enumerate(value)]
    if len(result) != len(set(result)):
        raise PortfolioStateError(f"{field} must not contain duplicates")
    return result


def _read(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise PortfolioStateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PortfolioStateError(f"{path} must contain an object")
    return value


def validate_interests(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1 or not isinstance(payload.get("interests"), list):
        raise PortfolioStateError("interests requires schema_version 1 and an interests list")
    out, seen = [], set()
    for n, raw in enumerate(payload["interests"]):
        if not isinstance(raw, dict):
            raise PortfolioStateError(f"interests[{n}] must be an object")
        iid = _id(raw.get("id"), f"interests[{n}].id")
        if iid in seen:
            raise PortfolioStateError(f"duplicate interest id: {iid}")
        seen.add(iid)
        keywords = raw.get("keywords", [])
        if not isinstance(keywords, list): raise PortfolioStateError("keywords must be a list")
        out.append({"id": iid, "label": _text(raw.get("label"), "label"),
                    "description": _text(raw.get("description"), "description", optional=True),
                    "keywords": [_text(x, "keyword") for x in keywords]})
    return {"schema_version": 1, "interests": out}


def validate_portfolios(payload: dict[str, Any], interest_ids: set[str], track_ids: set[str]) -> dict[str, Any]:
    if payload.get("schema_version") != 1 or not isinstance(payload.get("portfolios"), list):
        raise PortfolioStateError("portfolios requires schema_version 1 and a portfolios list")
    default_id = _id(payload.get("default_portfolio_id"), "default_portfolio_id")
    out, seen = [], set()
    for n, raw in enumerate(payload["portfolios"]):
        if not isinstance(raw, dict):
            raise PortfolioStateError(f"portfolios[{n}] must be an object")
        pid = _id(raw.get("id"), f"portfolios[{n}].id")
        if pid in seen:
            raise PortfolioStateError(f"duplicate portfolio id: {pid}")
        seen.add(pid)
        tracks = _ids(raw.get("track_ids", []), "track_ids")
        interests = _ids(raw.get("interest_ids", []), "interest_ids")
        missing_t, missing_i = set(tracks) - track_ids, set(interests) - interest_ids
        if missing_t or missing_i:
            raise PortfolioStateError(f"dangling references: tracks={sorted(missing_t)}, interests={sorted(missing_i)}")
        out.append({"id": pid, "name": _text(raw.get("name"), "name"), "track_ids": tracks,
                    "interest_ids": interests, "archived": bool(raw.get("archived", False))})
    if default_id not in seen:
        raise PortfolioStateError("default_portfolio_id must reference a portfolio")
    return {"schema_version": 1, "default_portfolio_id": default_id, "portfolios": out}


def validate_track(payload: dict[str, Any], slug: str, interest_ids: set[str]) -> dict[str, Any]:
    if payload.get("schema_version") != 1 or payload.get("id") != slug:
        raise PortfolioStateError(f"track metadata must have schema_version 1 and id {slug!r}")
    status = payload.get("status", "active")
    if status not in TRACK_STATUSES:
        raise PortfolioStateError(f"status must be one of {sorted(TRACK_STATUSES)}")
    selected = _ids(payload.get("interest_ids", []), "interest_ids")
    if set(selected) - interest_ids:
        raise PortfolioStateError("track references unknown interests")
    mappings = payload.get("interest_topic_mappings", {})
    if not isinstance(mappings, dict) or set(mappings) - interest_ids:
        raise PortfolioStateError("interest_topic_mappings references unknown interests")
    clean_mappings = {_id(k, "mapping interest"): _ids(v, f"mapping {k}") for k, v in mappings.items()}
    return {"schema_version": 1, "id": slug,
            "display_name": _text(payload.get("display_name", slug.replace("_", " ").title()), "display_name"),
            "description": _text(payload.get("description"), "description", optional=True),
            "status": status, "interest_ids": selected,
            "default_audience": _text(payload.get("default_audience"), "default_audience", optional=True),
            "interest_topic_mappings": clean_mappings}


def validate_taxonomy(payload: dict[str, Any], slug: str) -> dict[str, Any]:
    if payload.get("schema_version") != 1 or payload.get("track") != slug:
        raise PortfolioStateError(f"taxonomy must have schema_version 1 and track {slug!r}")
    def entries(name: str) -> list[dict[str, str]]:
        raw = payload.get(name, [])
        if not isinstance(raw, list):
            raise PortfolioStateError(f"{name} must be a list")
        out, seen = [], set()
        for n, item in enumerate(raw):
            if not isinstance(item, dict):
                raise PortfolioStateError(f"{name}[{n}] must be an object")
            eid = _id(item.get("id"), f"{name}[{n}].id")
            if eid in seen:
                raise PortfolioStateError(f"duplicate {name} id: {eid}")
            seen.add(eid)
            out.append({"id": eid, "label": _text(item.get("label", eid.replace("_", " ").title()), "label"),
                        "description": _text(item.get("description"), "description", optional=True)})
        return out
    return {"schema_version": 1, "track": slug, "topics": entries("topics"), "audiences": entries("audiences")}


class PortfolioStore:
    def __init__(self, root: Path): self.root = Path(root)
    @property
    def interests_path(self): return self.root / "profile" / "interests.json"
    @property
    def portfolios_path(self): return self.root / "profile" / "portfolios.json"
    def track_ids(self) -> set[str]:
        base = self.root / "tracks"
        return {p.name for p in base.iterdir() if p.is_dir() and ID_RE.fullmatch(p.name)} if base.exists() else set()
    def interests(self): return validate_interests(_read(self.interests_path, {"schema_version": 1, "interests": []}))
    def track(self, slug: str):
        _id(slug, "track")
        path = self.root / "tracks" / slug / "track.json"
        if not path.exists():
            return {"schema_version": 1, "id": slug, "display_name": slug.replace("_", " ").title(),
                    "description": "", "status": "active", "interest_ids": [], "default_audience": "",
                    "interest_topic_mappings": {}, "implicit": True}
        return validate_track(_read(path, {}), slug, {x["id"] for x in self.interests()["interests"]})
    def portfolios(self):
        if not self.portfolios_path.exists():
            return {"schema_version": 1, "default_portfolio_id": "all_tracks", "portfolios": [{
                "id": "all_tracks", "name": "All Tracks", "track_ids": sorted(self.track_ids()),
                "interest_ids": [], "archived": False, "implicit": True}]}
        return validate_portfolios(_read(self.portfolios_path, {}),
                                   {x["id"] for x in self.interests()["interests"]}, self.track_ids())
    def initialize(self):
        self.root.joinpath("profile").mkdir(parents=True, exist_ok=True)
        if not self.interests_path.exists(): write_json_atomic(self.interests_path, {"schema_version": 1, "interests": []})
        if not self.portfolios_path.exists():
            write_json_atomic(self.portfolios_path, {"schema_version": 1, "default_portfolio_id": "all_tracks",
                "portfolios": [{"id": "all_tracks", "name": "All Tracks", "track_ids": sorted(self.track_ids()), "interest_ids": [], "archived": False}]})
        return {"interests": self.interests(), "portfolios": self.portfolios()}
    def mutate(self, kind: str, fn: Callable[[dict[str, Any]], dict[str, Any]]):
        path = self.interests_path if kind == "interests" else self.portfolios_path
        with file_lock(path):
            current = self.interests() if kind == "interests" else self.portfolios()
            candidate = fn(current)
            valid = validate_interests(candidate) if kind == "interests" else validate_portfolios(
                candidate, {x["id"] for x in self.interests()["interests"]}, self.track_ids())
            write_json_atomic(path, valid)
        return valid
    def save_track(self, slug: str, payload: dict[str, Any]):
        if slug not in self.track_ids(): raise PortfolioStateError("unknown track")
        path = self.root / "tracks" / slug / "track.json"
        valid = validate_track(payload, slug, {x["id"] for x in self.interests()["interests"]})
        with file_lock(path): write_json_atomic(path, valid)
        return valid
    def taxonomy(self, slug: str):
        local = self.root / "tracks" / slug / "taxonomy.json"
        shipped = self.root / "shared" / "schemas" / f"{slug}_taxonomy.json"
        path = local if local.exists() else shipped
        if not path.exists(): return {"schema_version": 1, "track": slug, "topics": [], "audiences": [], "source": "empty"}
        raw = _read(path, {})
        # Shipped schemas are richer; normalize their id-bearing lists without rewriting them.
        result = {"schema_version": 1, "track": slug,
                  "topics": raw.get("topics", []), "audiences": raw.get("audiences", [])}
        valid = validate_taxonomy(result, slug)
        valid["source"] = "local" if path == local else "shipped"
        return valid
    def save_taxonomy(self, slug: str, payload: dict[str, Any]):
        if slug not in self.track_ids(): raise PortfolioStateError("unknown track")
        valid = validate_taxonomy(payload, slug)
        topic_ids = {x["id"] for x in valid["topics"]}
        mapped = {x for vals in self.track(slug)["interest_topic_mappings"].values() for x in vals}
        if mapped - topic_ids: raise PortfolioStateError(f"taxonomy would orphan mapped topics: {sorted(mapped-topic_ids)}")
        path = self.root / "tracks" / slug / "taxonomy.json"
        with file_lock(path): write_json_atomic(path, valid)
        return valid


def _item_key(item: dict[str, Any]) -> str:
    return str(item.get("item_key") or item.get("job_key") or item.get("url") or item.get("listing_url") or "")


def unified_items(root: Path, *, tracks: set[str] | None = None) -> list[dict[str, Any]]:
    """Adapt organized, ranked-audience, and digest artifacts without modifying them."""
    store, found = PortfolioStore(root), {}
    selected = tracks or store.track_ids()
    for slug in sorted(selected & store.track_ids()):
        candidates: list[tuple[str, Path]] = []
        for kind in ("organized", "ranked_audience", "digests", "discovery"):
            base = root / "artifacts" / kind / slug
            if base.exists(): candidates.extend((kind, p) for p in base.rglob("*.json"))
        for kind, path in candidates:
            try: raw = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError): continue
            audience = path.parent.name if kind == "ranked_audience" else ""
            date_value = path.stem if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem) else ""
            arrays = []
            if isinstance(raw, list): arrays = [raw]
            elif isinstance(raw, dict):
                for key in ("items", "ranked_items", "candidates", "top_matches", "other_new_roles"):
                    if isinstance(raw.get(key), list): arrays.append(raw[key])
                for run in raw.get("runs", []) if isinstance(raw.get("runs"), list) else []:
                    if isinstance(run, dict): arrays.extend(run.get(k, []) for k in ("top_matches", "other_new_roles") if isinstance(run.get(k), list))
                for source in raw.get("sources", []) if isinstance(raw.get("sources"), list) else []:
                    if isinstance(source, dict) and isinstance(source.get("candidates"), list): arrays.append(source["candidates"])
            for array in arrays:
                for item in array:
                    if not isinstance(item, dict): continue
                    key = _item_key(item)
                    if not key: continue
                    uid = f"{slug}:{key}"
                    score = item.get("audience_score")
                    score_percent = round(max(0, min(1, float(score))) * 100, 1) if isinstance(score, (int, float)) else None
                    projected = {**item, "id": uid, "track": slug, "item_key": key, "audience": audience,
                                 "date": item.get("published_at") or item.get("posted_date") or item.get("date") or date_value,
                                 "title": item.get("title") or item.get("headline") or "Untitled",
                                 "url": item.get("url") or item.get("listing_url") or "", "score_percent": score_percent,
                                 "artifact_kind": kind, "artifact_path": str(path.relative_to(root))}
                    previous = found.get(uid)
                    if previous is None or (projected["score_percent"] or -1) > (previous["score_percent"] or -1): found[uid] = projected
    return sorted(found.values(), key=lambda x: (str(x.get("date") or ""), x.get("score_percent") or -1, x["id"]), reverse=True)


def resolved_classifier_taxonomy(root: Path, slug: str) -> dict[str, Any]:
    """Overlay editable labels/descriptions on the complete shipped classifier schema."""
    shipped_path = root / "shared" / "schemas" / f"{slug}_taxonomy.json"
    base = _read(shipped_path, {"schema_version": 1})
    local_path = root / "tracks" / slug / "taxonomy.json"
    if not local_path.exists(): return base
    override = validate_taxonomy(_read(local_path, {}), slug)
    topic_key = "topics" if "topics" in base else "role_types" if "role_types" in base else "asset_classes"
    for key in (topic_key, "audiences"):
        existing = {x.get("id"): x for x in base.get(key, []) if isinstance(x, dict)}
        source = override["topics" if key == topic_key else "audiences"]
        base[key] = [{**existing.get(x["id"], {}), **x} for x in source]
    return base


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--root", default=".")
    ap.add_argument("command", choices=["init", "validate", "items"]); args = ap.parse_args()
    store = PortfolioStore(Path(args.root).resolve())
    result = store.initialize() if args.command == "init" else ({"interests": store.interests(), "portfolios": store.portfolios()} if args.command == "validate" else unified_items(store.root))
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
