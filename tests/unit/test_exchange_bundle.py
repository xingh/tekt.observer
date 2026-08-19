import copy
import json
from pathlib import Path

import pytest

from exchange_bundle import BundleError, assert_publishable, build_bundle, read_bundle, write_bundle


def sample_data():
    return {
        "workspace": {"id": "workspace00001", "slug": "demo", "revision": 4},
        "watchers": [{"id": "watcher0000001", "workspace": "workspace00001", "slug": "topic_watch"}],
        "sources": [], "runs": [], "items": [], "feedback": [], "digests": [], "provenance": [],
    }


def test_bundle_is_byte_stable_and_hash_verified(tmp_path: Path):
    first = build_bundle(workspace_id="workspace00001", workspace_revision=4, producer="test", created_at="2026-08-18T12:00:00Z", data=sample_data())
    second = build_bundle(workspace_id="workspace00001", workspace_revision=4, producer="test", created_at="2026-08-18T12:00:00Z", data=sample_data())
    one, two = tmp_path / "one.json", tmp_path / "two.json"
    write_bundle(one, first)
    write_bundle(two, second)
    assert one.read_bytes() == two.read_bytes()
    assert read_bundle(one) == first


def test_bundle_rejects_corruption_unsupported_schema_and_secrets(tmp_path: Path):
    bundle = build_bundle(workspace_id="workspace00001", workspace_revision=4, producer="test", created_at="2026-08-18T12:00:00Z", data=sample_data())
    corrupt = copy.deepcopy(bundle)
    corrupt["data"]["workspace"]["slug"] = "changed"
    path = tmp_path / "corrupt.json"
    path.write_text(json.dumps(corrupt))
    with pytest.raises(BundleError, match="hash mismatch"):
        read_bundle(path)
    unsupported = copy.deepcopy(bundle)
    unsupported["manifest"]["schema_version"] = 99
    path.write_text(json.dumps(unsupported))
    with pytest.raises(BundleError, match="unsupported"):
        read_bundle(path)
    secret_data = sample_data()
    secret_data["workspace"]["api_token"] = "nope"
    with pytest.raises(BundleError, match="secret-bearing"):
        build_bundle(workspace_id="workspace00001", workspace_revision=4, producer="test", created_at="now", data=secret_data)


def test_stale_bundle_is_not_publishable():
    bundle = build_bundle(workspace_id="workspace00001", workspace_revision=4, producer="test", created_at="2026-08-18T12:00:00Z", data=sample_data())
    assert_publishable(bundle, 4)
    with pytest.raises(BundleError, match="stale export"):
        assert_publishable(bundle, 5)
