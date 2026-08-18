import json
import shutil

from generate_watchers import check_outputs, discover_specs, rendered_outputs, write_outputs


def test_committed_watcher_outputs_are_generated_from_specs(repo_root):
    specs = discover_specs(repo_root)
    assert {spec.slug for spec in specs} == {"topic_watch", "job_watch", "market_watch"}
    assert check_outputs(repo_root, rendered_outputs(repo_root, specs))
    assert all(spec.metadata["id"] == spec.slug for spec in specs)


def test_generator_check_detects_drift(repo_root, tmp_path):
    shutil.copytree(repo_root / ".arkitype", tmp_path / ".arkitype")
    outputs = rendered_outputs(tmp_path, discover_specs(tmp_path))
    write_outputs(outputs)
    assert check_outputs(tmp_path, outputs)
    stale = tmp_path / "tracks" / "topic_watch" / "track.json"
    stale.write_text("{}\n")
    assert not check_outputs(tmp_path, outputs)


def test_new_watcher_is_discovered_without_python_registration(repo_root, tmp_path):
    source = repo_root / ".arkitype" / "watchers" / "topic_watch"
    target = tmp_path / ".arkitype" / "watchers" / "research_watch"
    shutil.copytree(source, target)
    metadata_path = target / "watcher.json"
    metadata = json.loads(metadata_path.read_text())
    metadata.update({"slug": "research_watch", "id": "research_watch", "display_name": "Research Watch"})
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    specs = discover_specs(tmp_path)
    assert [spec.slug for spec in specs] == ["research_watch"]
    outputs = rendered_outputs(tmp_path, specs)
    assert tmp_path / "tracks" / "research_watch" / "track.json" in outputs
