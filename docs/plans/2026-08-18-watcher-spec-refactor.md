# Canonical Watcher Specs and Slugs

Status: complete
Owner: Codex; agent_id: 01a016a7-0c85-7723-a26e-a225e490496d
Last updated: 2026-08-18 America/New_York

## Goal
Make `topic_watch`, `job_watch`, and `market_watch` the canonical built-in watcher tracks, and generate their runtime metadata, taxonomy, registries, and starter briefs from machine-readable specs under `.arkitype/` so future watcher types follow one extension path.

## Current State
`job_watch` and `market_watch` already used the desired slugs, while the topic watcher used a different historical slug across scripts, schemas, fixtures, docs, and its track directory. Runtime JSON and starter metadata were hand-maintained separately from Markdown arkitype specs. PyYAML is not a project dependency.

## Implementation Plan
- [x] Define a dependency-free watcher spec contract under `.arkitype/watchers/`; verify all three specs parse and validate.
- [x] Add a deterministic generator with `--check`; verify generated runtime files are byte-stable and include all three canonical slugs.
- [x] Rename the topic watcher runtime surface from the legacy slug to `topic_watch`; verify pipeline dispatch, artifacts, starter workspace, and tests.
- [x] Update docs and extension guidance; verify no unintended legacy topic slug references remain.
- [x] Run focused tests and `bash scripts/test.sh`.
- [x] Harden generated-file provenance and orphan detection; verify stale generated outputs fail `--check`.

## Progress Log
- 2026-08-18 - Began repository-wide inventory and spec-generation design; preserved existing dirty work from the prior starter-workflow iteration.
- 2026-08-18 - Added modular watcher specs (`watcher.json`, `brief.md`, `taxonomy.json`, `sources.json`, `samples.json`) and deterministic runtime generation with drift checking.
- 2026-08-18 - Renamed the topic runtime surface, scripts, schemas, track, fixtures, screenshots, commands, and docs to canonical `topic_watch`; canonical pipeline smoke completed with empty-feed degradation in the restricted network sandbox.
- 2026-08-18 - Made starter seeding and combined live runs discover watcher specs dynamically, so an additional watcher does not require registration in Python or shell.
- 2026-08-18 - Full verification passed: generated watcher check clean; 642 tests passed and 28 skipped.
- 2026-08-18 - Continued with generator hardening so runtime outputs identify their source spec and removed specs cannot leave silent orphan files.
- 2026-08-18 - Added provenance stamps and orphan detection, documented explicit cleanup, and completed full verification with 643 tests passed and 28 skipped.

## Handoff Notes
The canonical refactor and generator hardening passed in full. Future watcher types should begin as a new `.arkitype/watchers/<slug>/` directory and use the generator rather than editing runtime files directly.

## Verification
- [x] watcher spec generator check
- [x] focused watcher/pipeline tests
- [x] `bash scripts/test.sh` (643 passed, 28 skipped)

## Caveats
The slug change intentionally provides no permanent runtime alias. Existing ignored legacy artifact directories remain ordinary local track data, but new built-in runs only emit `topic_watch`.
