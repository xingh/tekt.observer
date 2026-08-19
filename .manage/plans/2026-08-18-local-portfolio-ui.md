# Local Portfolio Management UI — I9–I14

Status: in_progress
Owner: Codex; agent_id: 01a01690-6d24-75d0-862f-ae12bd979073
Last updated: 2026-08-18 America/New_York

## Goal
Add a local-first portfolio dashboard and management API while preserving file-backed tracks, deterministic pipelines, static output, and CLI compatibility.

## Current State
The live viewer is a loopback `http.server` with read-only HTML routes and one unprotected feedback POST. Track artifacts have three distinct shapes and private configuration is gitignored.

## Implementation Plan
- [x] I9: specifications, validated private state, initialization, legacy projection
- [x] I10–I12: unified items/dashboard, feedback, portfolio/interest/track/taxonomy APIs
- [ ] I13–I14: bounded background operations and operational APIs (run/validation/schedule forms and polling landed; guided browser setup remains agent-routed)
- [x] Fresh-checkout experience: track three starter workflows, add offline sample and combined live launchers, and update the user-facing documentation
- [x] Documentation for the behavior landed in this slice

## Progress Log
- 2026-08-18 - Inspected viewer, render model, persistence conventions, feedback, roadmap, and architecture specifications.
- 2026-08-18 - Implemented state, dashboard/API, feedback integration, taxonomy precedence, and bounded operation manager.
- 2026-08-18 - Focused suite: 6 passed, 2 sandbox-skipped. Full suite: 621 passed, 28 skipped, 2 pre-existing multiprocessing tests blocked by sandbox AF_UNIX permissions.
- 2026-08-18 - Began the fresh-checkout iteration after confirming only `test_workflow` was tracked despite the three documented starter tracks.
- 2026-08-18 - The combined-launcher smoke test exposed misplaced imports in the two newest classifier integrations; moved them before `main()` so the documented default-taxonomy path runs.
- 2026-08-18 - Added six explicit sample signals so a fresh/offline user sees content immediately; `--live` replaces that workspace with current feed results.
- 2026-08-18 - Verified the sample dashboard (3 workflows, 6 signals), combined live pipeline control flow, focused portfolio tests (8 passed, 2 sandbox-skipped), and full suite (623 passed, 28 skipped).
- 2026-08-18 - Added `/manage` for live runs, source validation, schedules, and polling; fixed cross-request cancellation and terminal-state races. Focused suite: 11 passed, 2 sandbox-skipped.
- 2026-08-18 - Refocused the three starters on AI-enabled professions, AI public companies/regulation, and AI business use; expanded their taxonomies, live query registries, briefs, and offline samples.
- 2026-08-18 - Verified 9 seeded items across the three starters, focused behavior (14 passed, 2 sandbox-skipped), and the full suite (623 passed, 28 skipped).

## Handoff Notes
The safe foundation, read/curation APIs, fresh-checkout starter workspace, and operational management page are implemented. Next: decide whether browser setup should remain a handoff to interactive agents or become a resumable wizard protocol, then add browser-level coverage. Files added in this effort include `scripts/run_starter_workflows.sh`, `scripts/seed_starter_workspace.py`, `.knowledge/local-portfolio.md`, and tracked metadata for the three starter workflows.

## Verification
- [x] focused state and HTTP tests
- [x] starter workspace/dashboard smoke test
- [x] `bash scripts/test.sh` (623 passed, 28 skipped)

## Caveats
Playwright is not currently a project dependency; HTTP/HTML smoke tests cover the browser surface. Loopback socket tests are skipped in this execution sandbox. External feeds were unreachable during the live smoke test, but all three pipelines completed with their designed empty-feed degradation; the default sample path remains fully offline.
