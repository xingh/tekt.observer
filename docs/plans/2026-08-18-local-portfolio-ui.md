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
- [ ] I13–I14: bounded background operations and operational APIs (run/validation and polling landed; setup wizard, schedule/source forms remain)
- [x] Documentation for the behavior landed in this slice

## Progress Log
- 2026-08-18 - Inspected viewer, render model, persistence conventions, feedback, roadmap, and architecture specifications.
- 2026-08-18 - Implemented state, dashboard/API, feedback integration, taxonomy precedence, and bounded operation manager.
- 2026-08-18 - Focused suite: 6 passed, 2 sandbox-skipped. Full suite: 621 passed, 28 skipped, 2 pre-existing multiprocessing tests blocked by sandbox AF_UNIX permissions.

## Handoff Notes
The safe foundation and read/curation APIs are implemented. Next: build the setup wizard and source/schedule management forms on the operation API, then add Playwright coverage.

## Verification
- [x] focused state and HTTP tests
- [ ] `bash scripts/test.sh` (621 passed; two existing sandbox-incompatible multiprocessing tests failed)

## Caveats
Playwright is not currently a project dependency; HTTP/HTML smoke tests cover the browser surface. Loopback sockets and multiprocessing forkserver sockets are prohibited in this execution sandbox.
