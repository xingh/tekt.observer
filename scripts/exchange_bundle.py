#!/usr/bin/env python3
"""Deterministic, portable tekt.observer JSON exchange bundles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

BUNDLE_SCHEMA_VERSION = 1
COLLECTION_ORDER = ("workspace", "watchers", "sources", "runs", "items", "feedback", "digests", "provenance")
FORBIDDEN_KEYS = {"token", "password", "passwordConfirm", "credentials", "environment", "claim_token"}


class BundleError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reject_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS or key.lower().endswith(("_secret", "_password", "_token")):
                raise BundleError(f"secret-bearing field is not exportable: {path}.{key}")
            _reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secrets(child, f"{path}[{index}]")


def build_bundle(*, workspace_id: str, workspace_revision: int, producer: str, created_at: str, data: Mapping[str, Any], bundle_id: str | None = None) -> dict[str, Any]:
    normalized = {name: data.get(name, [] if name != "workspace" else {}) for name in COLLECTION_ORDER}
    _reject_secrets(normalized)
    hashes = {name: sha256(normalized[name]) for name in COLLECTION_ORDER}
    stable_identity = {"workspace_id": workspace_id, "workspace_revision": workspace_revision, "schema_version": BUNDLE_SCHEMA_VERSION, "hashes": hashes}
    resolved_id = bundle_id or hashlib.sha256(canonical_bytes(stable_identity)).hexdigest()[:32]
    return {
        "manifest": {
            "bundle_id": resolved_id,
            "workspace_id": workspace_id,
            "workspace_revision": workspace_revision,
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "producer": producer,
            "created_at": created_at,
            "hashes": hashes,
        },
        "data": normalized,
    }


def validate_bundle(bundle: Mapping[str, Any]) -> None:
    manifest = bundle.get("manifest")
    data = bundle.get("data")
    if not isinstance(manifest, dict) or not isinstance(data, dict):
        raise BundleError("bundle must contain manifest and data objects")
    if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise BundleError(f"unsupported bundle schema version: {manifest.get('schema_version')!r}")
    if set(data) != set(COLLECTION_ORDER):
        raise BundleError("bundle data collections are incomplete or unknown")
    expected = manifest.get("hashes")
    if not isinstance(expected, dict):
        raise BundleError("manifest hashes must be an object")
    _reject_secrets(data)
    for name in COLLECTION_ORDER:
        actual = sha256(data[name])
        if expected.get(name) != actual:
            raise BundleError(f"hash mismatch for {name}")


def write_bundle(path: Path, bundle: Mapping[str, Any]) -> None:
    validate_bundle(bundle)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(bundle)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def read_bundle(path: Path) -> dict[str, Any]:
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleError(f"cannot read bundle {path}: {exc}") from exc
    validate_bundle(bundle)
    return bundle


def assert_publishable(bundle: Mapping[str, Any], current_revision: int) -> None:
    validate_bundle(bundle)
    revision = bundle["manifest"]["workspace_revision"]
    if revision != current_revision:
        raise BundleError(f"stale export revision {revision}; workspace is at revision {current_revision}")
