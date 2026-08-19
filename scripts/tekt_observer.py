#!/usr/bin/env python3
"""Unified tekt.observer command surface."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

from exchange_bundle import BundleError, assert_publishable, build_bundle, read_bundle, write_bundle
from pocketbase_client import PocketBaseClient, PocketBaseError

ROOT = Path(__file__).resolve().parents[1]
EXPORT_COLLECTIONS = ("watchers", "sources", "runs", "items", "feedback")


def client_from_env() -> PocketBaseClient:
    url = os.environ.get("TEKT_OBSERVER_POCKETBASE_URL", "http://127.0.0.1:8090")
    token = os.environ.get("TEKT_OBSERVER_TOKEN")
    return PocketBaseClient(url, token=token)


def _record_payload(record: dict[str, Any]) -> dict[str, Any]:
    transient = {"collectionId", "collectionName", "expand", "created", "updated"}
    return {key: value for key, value in record.items() if key not in transient}


def export_workspace(client: PocketBaseClient, workspace_id: str, output: Path, created_at: str | None = None) -> dict[str, Any]:
    workspace_rows = client.list_records("workspaces", filter_=f'id="{workspace_id}"')
    if len(workspace_rows) != 1:
        raise BundleError(f"workspace not found: {workspace_id}")
    workspace = _record_payload(workspace_rows[0])
    data: dict[str, Any] = {"workspace": workspace, "digests": [], "provenance": []}
    for collection in EXPORT_COLLECTIONS:
        data[collection] = [_record_payload(row) for row in client.list_records(collection, filter_=f'workspace="{workspace_id}"')]
    instant = created_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    bundle = build_bundle(
        workspace_id=workspace_id,
        workspace_revision=int(workspace.get("revision", 0)),
        producer="tekt.observer",
        created_at=instant,
        data=data,
    )
    write_bundle(output, bundle)
    return bundle


def import_bundle(client: PocketBaseClient, bundle_path: Path, *, fork_slug: str | None = None) -> str:
    bundle = read_bundle(bundle_path)
    source_workspace = dict(bundle["data"]["workspace"])
    old_workspace_id = source_workspace.pop("id", bundle["manifest"]["workspace_id"])
    source_workspace["slug"] = fork_slug or f"{source_workspace.get('slug', 'workspace')}-import"
    collisions = client.list_records("workspaces", filter_=f'slug="{source_workspace["slug"]}"')
    if collisions:
        raise BundleError(f"workspace slug already exists: {source_workspace['slug']}")
    created_workspace = client.create_record("workspaces", source_workspace)
    workspace_id = created_workspace["id"]
    id_maps: dict[str, dict[str, str]] = {}
    for collection in EXPORT_COLLECTIONS:
        id_maps[collection] = {}
        for raw in bundle["data"][collection]:
            record = dict(raw)
            old_id = record.pop("id", None)
            record["workspace"] = workspace_id
            for relation, target in (("watcher", "watchers"), ("run", "runs"), ("item", "items")):
                if record.get(relation) in id_maps.get(target, {}):
                    record[relation] = id_maps[target][record[relation]]
            created = client.create_record(collection, record)
            if old_id:
                id_maps[collection][old_id] = created["id"]
    return workspace_id


def current_revision(client: PocketBaseClient, workspace_id: str) -> int:
    rows = client.list_records("workspaces", filter_=f'id="{workspace_id}"')
    if len(rows) != 1:
        raise BundleError(f"workspace not found: {workspace_id}")
    return int(rows[0].get("revision", 0))


def publish_bundle(client: PocketBaseClient, bundle_path: Path, workspace_id: str, remote: str) -> None:
    bundle = read_bundle(bundle_path)
    if bundle["manifest"]["workspace_id"] != workspace_id:
        raise BundleError("bundle workspace does not match --workspace")
    assert_publishable(bundle, current_revision(client, workspace_id))
    if not shutil.which("rclone"):
        raise BundleError("rclone is required for publication")
    subprocess.run(["rclone", "copy", "--immutable", str(bundle_path), remote], check=True)


def seed_local(client: PocketBaseClient) -> str:
    """Create the implicit local owner workspace and canonical starter watchers."""
    rows = client.list_records("workspaces", filter_='slug="local"')
    if rows:
        workspace = rows[0]
    else:
        workspace = client.create_record("workspaces", {"name": "Local workspace", "slug": "local", "revision": 1, "definition": {"mode": "local"}})
    existing = {row["slug"] for row in client.list_records("watchers", filter_=f'workspace="{workspace["id"]}"')}
    for slug in ("topic_watch", "job_watch", "market_watch"):
        if slug not in existing:
            definition = json.loads((ROOT / ".arkitype" / "watchers" / slug / "watcher.json").read_text())
            client.create_record("watchers", {"workspace": workspace["id"], "slug": slug, "name": definition.get("name", slug.replace("_", " ").title()), "enabled": True, "definition": definition})
    return workspace["id"]


def worker_loop(client: PocketBaseClient, poll_seconds: float, once: bool) -> None:
    while True:
        queued = client.list_records("operations", filter_='status="queued"', sort="created")
        if queued:
            operation = queued[0]
            client.update_record("operations", operation["id"], {"status": "running", "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "attempt": int(operation.get("attempt", 0)) + 1})
            try:
                watcher = operation.get("input", {}).get("watcher_slug")
                if operation["kind"] != "run_watcher" or not watcher:
                    raise RuntimeError(f"unsupported operation: {operation['kind']}")
                subprocess.run(["bash", str(ROOT / "scripts" / "run_track.sh"), "--track", watcher], cwd=ROOT, check=True)
                client.update_record("operations", operation["id"], {"status": "complete", "result": {"watcher_slug": watcher}})
            except Exception as exc:
                next_status = "queued" if int(operation.get("attempt", 0)) + 1 < int(operation.get("max_attempts", 1)) else "failed"
                client.update_record("operations", operation["id"], {"status": next_status, "error": str(exc)})
        if once:
            return
        time.sleep(poll_seconds)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="tekt.observer")
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("up").add_argument("--hosted", action="store_true")
    worker = sub.add_parser("worker")
    worker.add_argument("--poll-seconds", type=float, default=5)
    worker.add_argument("--once", action="store_true")
    importer = sub.add_parser("import")
    importer.add_argument("bundle", type=Path)
    importer.add_argument("--fork-slug")
    exporter = sub.add_parser("export")
    exporter.add_argument("--workspace", required=True)
    exporter.add_argument("--output", type=Path)
    publisher = sub.add_parser("publish")
    publisher.add_argument("--workspace", required=True)
    publisher.add_argument("--bundle", type=Path, required=True)
    publisher.add_argument("--remote", required=True)
    sub.add_parser("seed-local")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "up":
            command = ["docker", "compose", "-f", str(ROOT / "deploy" / "docker-compose.yml"), "up", "-d"]
            if args.hosted:
                print("Hosted mode requires a reverse proxy, TLS, and non-loopback port configuration.", file=sys.stderr)
            subprocess.run(command, cwd=ROOT, check=True)
            return 0
        client = client_from_env()
        if args.command == "worker":
            worker_loop(client, args.poll_seconds, args.once)
        elif args.command == "import":
            print(import_bundle(client, args.bundle, fork_slug=args.fork_slug))
        elif args.command == "export":
            output = args.output or ROOT / "exports" / f"{args.workspace}.tekt-observer.json"
            bundle = export_workspace(client, args.workspace, output)
            print(json.dumps({"bundle_id": bundle["manifest"]["bundle_id"], "path": str(output)}, sort_keys=True))
        elif args.command == "publish":
            publish_bundle(client, args.bundle, args.workspace, args.remote)
        elif args.command == "seed-local":
            print(seed_local(client))
        return 0
    except (BundleError, PocketBaseError, subprocess.CalledProcessError) as exc:
        print(f"tekt.observer: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
