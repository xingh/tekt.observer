# tekt.observer PocketBase Rebuild

Status: in_progress
Owner: Codex; agent_id: 01a017a7-56d7-70d2-b10b-a806a3aeac3c
Last updated: 2026-08-18 America/New_York

## Goal

Incrementally rebuild tekt.observer around an immutable JSON durable record, pinned unmodified PocketBase as the operational projection/API layer, a React/TypeScript document interface, existing Python observation workers, and deterministic JSON handoff bundles published with immutable rclone copies.

## Dependencies

- Crawl4AI integration supplies repeatable browser extraction.
- browser-use integration supplies reconnaissance and repair for interactive sources.
- multi-agent CLI platform supplies setup, interpretation, ranking, synthesis, and repair boundaries.
- The delivered local portfolio establishes behavior to preserve until PocketBase parity.

## Milestones

- [x] Rewrite Arkitype intent and archive the superseded local-portfolio implementation plan.
- [x] Pin PocketBase 0.39.11 and commit initial workspace-scoped collection migration.
- [x] Add standard-REST Python client, deterministic bundles, hash/secret/stale-revision validation, unified CLI, local compose topology, and focused tests.
- [x] Add a hash-chained immutable JSON event journal with fsynced writes, deterministic replay, count/time-based immutable snapshot compaction, atomic cache pointer, CLI controls, and tamper tests.
- [ ] Validate migration and API rules against the pinned executable, including owner/editor/viewer/worker and cross-workspace cases.
- [ ] Import current portfolio state, starter watcher specs, sources, feedback, operations, and artifacts with stable IDs and idempotent retries.
- [ ] Add operation claim leases, cancellation, crash recovery, revision mutation discipline, and realtime progress.
- [x] Build the responsive React/Vite/Tailwind application shell, starter inbox, watcher health, signal detail/provenance, operations view, keyboard search, themes, and durable Save/Dismiss workflow.
- [x] Add local-owner visibility, watcher pause/enable, persisted digest generation, deterministic export/download history, and concrete storage/theme settings.
- [ ] Complete hosted member management, bundle import/fork controls, live watcher execution, and full browser-level workflow coverage.
- [ ] Cut workers over to PocketBase, then retire the legacy viewer and redundant shell entrypoints after parity.
- [ ] Complete hosted deployment, backup/restore, immutable rclone round-trip, and local/hosted acceptance.

## Verification

- Focused bundle/client/store tests: 8 passed.
- Python compile check and `git diff --check`: passed.
- Full `scripts/test.sh`: 715 passed, 28 skipped, including frontend build and component tests.

## Six-iteration product pass

- [x] Iteration 1: first-class Active, New, Saved, and Dismissed inbox views with reversible curation.
- [ ] Iteration 2: source inventory and watcher health detail.
- [ ] Iteration 3: validated immutable bundle import/fork.
- [ ] Iteration 4: journaled local run operations.
- [ ] Iteration 5: digest reading and highlighted-item navigation.
- [ ] Iteration 6: onboarding, accessibility, keyboard, and acceptance polish.

## Next Step

Run the committed migration with the pinned executable and add executable API-rule integration tests before treating the authorization model as complete.

## Risks

- PocketBase is pre-1.0; upgrades require migration and API-rule regression testing.
- The compose image is a packaging convenience, not the source of truth; production must verify the binary checksum and preserve data volumes.
- The immutable store is implemented, but every PocketBase mutation path still needs to be routed through journal-first projection before the cutover is complete.
