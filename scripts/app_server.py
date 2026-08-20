#!/usr/bin/env python3
"""Loopback application server backed by the immutable JSON journal."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import threading
from typing import Any
from urllib.parse import unquote, urlparse

from exchange_bundle import BundleError, build_bundle, validate_bundle, write_bundle
from immutable_json_store import ImmutableJsonStore, StoreError

ROOT = Path(__file__).resolve().parents[1]
ITEM_PATH = re.compile(r"^/api/v1/items/([^/]+)$")
WATCHER_PATH = re.compile(r"^/api/v1/watchers/([^/]+)$")
EXPORT_PATH = re.compile(r"^/api/v1/exports/([A-Za-z0-9._-]+)$")
MAX_BODY = 64 * 1024
MAX_IMPORT_BODY = 20 * 1024 * 1024
RUN_LOCK = threading.Lock()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _readable_context(track: str, row: dict[str, Any]) -> str:
    topic = str(row.get("topic") or "general").replace("_", " ")
    if track == "career_watch":
        role = str(row.get("role_type") or topic).replace("_", " ")
        seniority = str(row.get("seniority") or "unspecified seniority").replace("_", " ")
        location = "Remote-friendly" if row.get("is_remote_friendly") else "Location flexibility was not confirmed"
        return f"{seniority.title()} opportunity in {role}. {location}."
    if track == "market_watch":
        event = str(row.get("event_type") or row.get("content_type") or "market development").replace("_", " ")
        watchlist = row.get("watchlist_matches") or []
        relevance = f" Watchlist match: {', '.join(watchlist)}." if watchlist else ""
        return f"{event.title()} with potential relevance to {topic}.{relevance}"
    audience = ", ".join(str(value).replace("_", " ") for value in row.get("audiences", []))
    suffix = f" for {audience}" if audience else ""
    return f"A {str(row.get('content_type') or 'report').replace('_', ' ')} about {topic}{suffix}."


def _useful_description(value: Any) -> str:
    text = str(value or "").strip()
    machine_markers = ("_hits=", "content_type_inferred=", "watchlist_hits=", "remote=")
    return "" if any(marker in text for marker in machine_markers) else text


def seed_store(store: ImmutableJsonStore, specs_root: Path = ROOT / ".arkitype" / "watchers") -> None:
    state = store.read()
    changed = False
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    if not state["workspaces"]:
        store.append("workspaces", "local", "put", {"id": "local", "name": "My observation workspace", "revision": 1})
        changed = True
    for watcher_dir in sorted(specs_root.iterdir()):
        if not watcher_dir.is_dir() or not (watcher_dir / "watcher.json").exists():
            continue
        definition = _read_json(watcher_dir / "watcher.json")
        sources = _read_json(watcher_dir / "sources.json")
        source_rows = sources.get("sources", sources) if isinstance(sources, dict) else sources
        watcher = {
            "id": definition["id"], "slug": definition["slug"],
            "name": definition.get("display_name", definition["slug"]).split(" · ")[-1],
            "description": definition.get("description", ""), "enabled": definition.get("status") == "active",
            "status": "healthy", "sourceCount": len(source_rows),
        }
        existing_watcher = state["watchers"].get(watcher["id"])
        if existing_watcher:
            enabled = existing_watcher.get("enabled", watcher["enabled"])
            watcher = {**watcher, "enabled": enabled, "status": "healthy" if enabled else "paused"}
        if existing_watcher != watcher:
            store.append("watchers", watcher["id"], "put", watcher)
            changed = True
        for source in source_rows:
            source_id = f"{definition['slug']}:{source['id']}"
            if source_id not in state["sources"]:
                store.append("sources", source_id, "put", {
                    "id": source_id, "watcher": definition["slug"], "name": source.get("name", source["id"]),
                    "url": source.get("url", ""), "discoveryMode": source.get("discovery_mode", "unknown"),
                    "cadence": source.get("cadence_group", "every_run"), "status": "ready",
                })
                changed = True
        configured_source_ids = {f"{definition['slug']}:{source['id']}" for source in source_rows}
        for source_id, existing_source in state["sources"].items():
            if existing_source.get("watcher") == definition["slug"] and source_id not in configured_source_ids:
                store.append("sources", source_id, "delete")
                changed = True
        has_live_items = any(row.get("watcher") == definition["slug"] and not row.get("sample", False) for row in state["items"].values())
        for index, sample in enumerate(_read_json(watcher_dir / "samples.json")):
            item_id = f"{definition['slug']}:{sample['item_key']}"
            if item_id in state["items"] or has_live_items:
                continue
            item = {
                "id": item_id, "watcher": definition["slug"], "title": sample["title"],
                "description": sample.get("description", ""), "url": sample.get("url", ""),
                "topic": sample.get("topic", "general"), "score": max(72, 94 - index * 5),
                "status": "new", "observedAt": now,
                "provenance": ["Starter watcher specification", "Normalized by tekt.observer", "Sample content — replace with a live run"],
                "sample": True,
            }
            store.append("items", item_id, "put", item)
            changed = True
    if "starter-run" not in state["operations"]:
        store.append("operations", "starter-run", "put", {"id": "starter-run", "label": "Starter watchers initialized", "status": "complete", "progress": 100, "updatedAt": now})
        changed = True
    if changed:
        store.compact_if_due(force=True)


def ingest_run_artifacts(store: ImmutableJsonStore, scratch: Path, date: str | None = None) -> dict[str, Any]:
    organized_root = scratch / "artifacts" / "organized"
    if not organized_root.is_dir():
        raise StoreError(f"organized artifacts not found: {organized_root}")
    state = store.read()
    imported = 0
    tracks: dict[str, int] = {}
    resolved_date = date
    for track_dir in sorted(organized_root.iterdir()):
        if not track_dir.is_dir():
            continue
        candidates = sorted(track_dir.glob("*.json"))
        if date:
            candidates = [track_dir / f"{date}.json"] if (track_dir / f"{date}.json").exists() else []
        if not candidates:
            continue
        artifact = _read_json(candidates[-1])
        track = artifact.get("track", track_dir.name)
        resolved_date = artifact.get("date", resolved_date)
        enrichment_path = scratch / "artifacts" / "enrichment" / track / "urls.json"
        enrichment = _read_json(enrichment_path) if enrichment_path.exists() else {}
        score_by_id: dict[str, float] = {}
        digest_summary = ""
        digest_item_ids: list[str] = []
        digest_path = scratch / "artifacts" / "digests" / track / f"{artifact.get('date')}.json"
        if digest_path.exists():
            digest = _read_json(digest_path)
            for run in digest.get("runs", []):
                digest_summary = run.get("executive_summary") or digest_summary
                for row in run.get("top_matches", []):
                    if row.get("job_key"):
                        score_by_id[row["job_key"]] = min(100, float(row.get("fit_score") or 0) * 10)
                        digest_item_ids.append(f"{track}:{row['job_key']}")
        track_count = 0
        for row in artifact.get("items", []):
            item_key = row.get("item_key")
            if not item_key:
                continue
            item_id = f"{track}:{item_key}"
            existing = state["items"].get(item_id, {})
            rationale = row.get("rationale") or "Classified by the deterministic observation pipeline."
            metadata = enrichment.get(row.get("url", ""), {})
            item = {
                "id": item_id, "watcher": track, "title": row.get("title", "Untitled signal"),
                "description": _useful_description(metadata.get("og_description")) or _useful_description(row.get("description")) or _readable_context(track, row), "url": row.get("url", ""),
                "image": metadata.get("og_image", ""), "siteName": metadata.get("og_site_name") or row.get("source_id", ""),
                "author": metadata.get("author", ""),
                "topic": row.get("topic") or row.get("role_type") or row.get("asset_class") or "general",
                "score": round(score_by_id.get(item_key, max(40, float(row.get("confidence") or 0.5) * 100))),
                "status": existing.get("status", "new"), "observedAt": artifact.get("generated_at") or f"{artifact.get('date')}T00:00:00Z",
                "provenance": [f"Live run · {artifact.get('date')}", f"Source · {row.get('source_id', 'unknown')}", rationale],
                "sample": False,
            }
            store.append("items", item_id, "put", item)
            imported += 1
            track_count += 1
        tracks[track] = track_count
        run_id = f"{track}:{artifact.get('date')}"
        store.append("runs", run_id, "put", {"id": run_id, "watcher": track, "date": artifact.get("date"), "status": "complete", "itemCount": track_count, "artifact": str(candidates[-1])})
        if digest_summary or digest_item_ids:
            digest_id = f"pipeline:{track}:{artifact.get('date')}"
            store.append("digests", digest_id, "put", {"id": digest_id, "watcher": track, "title": f"{track.replace('_', ' ').title()} · {artifact.get('date')}", "createdAt": artifact.get("generated_at") or f"{artifact.get('date')}T00:00:00Z", "summary": digest_summary or f"{track_count} signals imported.", "itemIds": digest_item_ids, "status": "ready"})
    if not tracks:
        raise StoreError("no organized track artifacts found")
    for item_id, row in state["items"].items():
        if row.get("sample"):
            store.append("items", item_id, "delete")
    workspace = state["workspaces"].get("local")
    if workspace:
        store.append("workspaces", "local", "put", {**workspace, "revision": int(workspace.get("revision", 0)) + 1})
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    operation_id = f"live-import:{resolved_date or now[:10]}"
    operation = {"id": operation_id, "label": f"Imported live tracks for {resolved_date}", "status": "complete", "progress": 100, "updatedAt": now, "itemCount": imported}
    store.append("operations", operation_id, "put", operation)
    store.compact_if_due(force=True)
    return {"date": resolved_date, "tracks": tracks, "itemCount": imported, "operation": operation}


def workspace_payload(store: ImmutableJsonStore) -> dict[str, Any]:
    state = store.read()
    workspace = state["workspaces"].get("local") or next(iter(state["workspaces"].values()), {"id": "local", "name": "Workspace", "revision": 0})
    return {
        "workspace": workspace,
        "watchers": sorted(state["watchers"].values(), key=lambda row: row["slug"]),
        "sources": sorted(state["sources"].values(), key=lambda row: (row.get("watcher", ""), row.get("name", ""))),
        "items": sorted(state["items"].values(), key=lambda row: row.get("observedAt", ""), reverse=True),
        "operations": sorted(state["operations"].values(), key=lambda row: row.get("updatedAt", ""), reverse=True),
        "digests": sorted(state["digests"].values(), key=lambda row: row.get("createdAt", ""), reverse=True),
        "exports": sorted(state["exports"].values(), key=lambda row: row.get("createdAt", ""), reverse=True),
    }


def patch_item(store: ImmutableJsonStore, item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"status"} or payload["status"] not in {"new", "saved", "dismissed"}:
        raise StoreError("status must be one of new, saved, or dismissed")
    state = store.read()
    existing = state["items"].get(item_id)
    if existing is None:
        raise KeyError(item_id)
    updated = {**existing, "status": payload["status"]}
    store.append("items", item_id, "put", updated)
    workspace = state["workspaces"].get("local")
    if workspace:
        store.append("workspaces", "local", "put", {**workspace, "revision": int(workspace.get("revision", 0)) + 1})
    return updated


def patch_watcher(store: ImmutableJsonStore, watcher_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) != {"enabled"} or not isinstance(payload["enabled"], bool):
        raise StoreError("enabled must be a boolean")
    state = store.read()
    existing = state["watchers"].get(watcher_id)
    if existing is None:
        raise KeyError(watcher_id)
    updated = {**existing, "enabled": payload["enabled"], "status": "healthy" if payload["enabled"] else "paused"}
    store.append("watchers", watcher_id, "put", updated)
    return updated


def create_digest(store: ImmutableJsonStore) -> dict[str, Any]:
    state = store.read()
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    digest_id = f"digest-{len(state['digests']) + 1:04d}"
    visible = [row for row in state["items"].values() if row.get("status") != "dismissed"]
    top = sorted(visible, key=lambda row: (-int(row.get("score", 0)), row.get("title", "")))[:5]
    digest = {
        "id": digest_id, "title": f"Observation brief · {now[:10]}", "createdAt": now,
        "summary": f"{len(visible)} active signals across {len(state['watchers'])} watchers, with {len(top)} highlighted below.",
        "itemIds": [row["id"] for row in top], "status": "ready",
    }
    store.append("digests", digest_id, "put", digest)
    return digest


def create_export(store: ImmutableJsonStore) -> tuple[dict[str, Any], Path]:
    state = store.read()
    workspace = state["workspaces"].get("local") or next(iter(state["workspaces"].values()))
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    data = {
        "workspace": workspace,
        "watchers": list(state["watchers"].values()), "sources": list(state["sources"].values()),
        "runs": list(state["runs"].values()), "items": list(state["items"].values()),
        "feedback": list(state["feedback"].values()), "digests": list(state["digests"].values()), "provenance": [],
    }
    bundle = build_bundle(workspace_id=workspace["id"], workspace_revision=int(workspace.get("revision", 0)), producer="tekt.observer.local", created_at=now, data=data)
    filename = f"{bundle['manifest']['bundle_id']}.tekt-observer.json"
    path = store.root / "exports" / filename
    write_bundle(path, bundle)
    record = {"id": bundle["manifest"]["bundle_id"], "filename": filename, "createdAt": now, "workspaceRevision": workspace.get("revision", 0), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    store.append("exports", record["id"], "put", record)
    return record, path


def validate_import_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    validate_bundle(bundle)
    manifest = bundle["manifest"]
    data = bundle["data"]
    return {
        "valid": True,
        "bundleId": manifest["bundle_id"],
        "workspaceId": manifest["workspace_id"],
        "workspaceRevision": manifest["workspace_revision"],
        "schemaVersion": manifest["schema_version"],
        "counts": {name: len(value) if isinstance(value, list) else 1 for name, value in data.items()},
    }


def start_live_run(store: ImmutableJsonStore, scratch: Path = ROOT / "tests" / "tmp" / "starter-workflows") -> dict[str, Any]:
    state = store.read()
    if any(row.get("status") in {"queued", "running"} and row.get("kind") == "live_tracks" for row in state["operations"].values()):
        raise StoreError("a live track run is already active")
    now = dt.datetime.now(dt.timezone.utc)
    operation_id = f"live-run:{now.strftime('%Y%m%dT%H%M%S')}"
    operation = {"id": operation_id, "kind": "live_tracks", "label": "Run all live watchers", "status": "queued", "progress": 0, "updatedAt": now.isoformat().replace("+00:00", "Z")}
    store.append("operations", operation_id, "put", operation)

    def run() -> None:
        with RUN_LOCK:
            running = {**operation, "status": "running", "progress": 10, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")}
            store.append("operations", operation_id, "put", running)
            log_path = store.root / "run-logs" / f"{operation_id.replace(':', '-')}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with log_path.open("wb") as log:
                    subprocess.run(["bash", str(ROOT / "scripts" / "run_starter_workflows.sh"), "--live", "--scratch", str(scratch)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                result = ingest_run_artifacts(store, scratch)
                complete = {**running, "status": "complete", "progress": 100, "itemCount": result["itemCount"], "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"), "log": str(log_path)}
                store.append("operations", operation_id, "put", complete)
            except Exception as exc:
                failed = {**running, "status": "failed", "progress": 100, "error": str(exc), "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"), "log": str(log_path)}
                store.append("operations", operation_id, "put", failed)

    threading.Thread(target=run, name=operation_id, daemon=True).start()
    return operation


class AppHandler(SimpleHTTPRequestHandler):
    server_version = "tekt.observer"

    def __init__(self, *args: Any, directory: str, store: ImmutableJsonStore, **kwargs: Any) -> None:
        self.store = store
        super().__init__(*args, directory=directory, **kwargs)

    def _json(self, status: HTTPStatus, value: Any) -> None:
        body = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/v1/workspace":
            try:
                self._json(HTTPStatus.OK, workspace_payload(self.store))
            except StoreError as exc:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return
        export_match = EXPORT_PATH.match(urlparse(self.path).path)
        if export_match:
            path = self.store.root / "exports" / export_match.group(1)
            if not path.is_file():
                self._json(HTTPStatus.NOT_FOUND, {"error": "export not found"})
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        path = urlparse(self.path).path
        if path != "/" and not (Path(self.directory) / path.lstrip("/")).exists():
            self.path = "/index.html"
        super().do_GET()

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        item_match = ITEM_PATH.match(path)
        watcher_match = WATCHER_PATH.match(path)
        if not item_match and not watcher_match:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise StoreError("invalid request size")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise StoreError("request body must be an object")
            updated = patch_item(self.store, unquote(item_match.group(1)), payload) if item_match else patch_watcher(self.store, unquote(watcher_match.group(1)), payload)
            self._json(HTTPStatus.OK, updated)
        except KeyError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "item not found"})
        except (StoreError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/v1/digests":
                self._json(HTTPStatus.CREATED, create_digest(self.store))
            elif path == "/api/v1/exports":
                record, _ = create_export(self.store)
                self._json(HTTPStatus.CREATED, {**record, "downloadUrl": f"/api/v1/exports/{record['filename']}"})
            elif path == "/api/v1/runs/ingest":
                result = ingest_run_artifacts(self.store, ROOT / "tests" / "tmp" / "starter-workflows")
                self._json(HTTPStatus.CREATED, result)
            elif path == "/api/v1/runs":
                self._json(HTTPStatus.ACCEPTED, start_live_run(self.store))
            elif path == "/api/v1/imports/validate":
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_IMPORT_BODY:
                    raise StoreError("invalid import size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise StoreError("bundle must be an object")
                self._json(HTTPStatus.OK, validate_import_bundle(payload))
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except (BundleError, StoreError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, format_: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format_ % args}")


def serve(host: str, port: int, store_path: Path, static_path: Path) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("the local app server only binds to loopback")
    if not (static_path / "index.html").exists():
        raise FileNotFoundError(f"frontend build missing at {static_path}; run: cd frontend && npm run build")
    store = ImmutableJsonStore(store_path)
    seed_store(store)
    handler = lambda *args, **kwargs: AppHandler(*args, directory=str(static_path), store=store, **kwargs)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"tekt.observer is ready at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\ntekt.observer stopped")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--store", type=Path, default=ROOT / "state")
    parser.add_argument("--static", type=Path, default=ROOT / "frontend" / "dist")
    args = parser.parse_args()
    serve(args.host, args.port, args.store, args.static)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
