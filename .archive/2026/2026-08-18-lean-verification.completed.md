# Lean verification harness

Status: complete
Owner: Codex; agent_id: unknown
Last updated: 2026-08-18 America/New_York

## Goal

Reduce verification code and maintenance without reducing behavioral coverage.

## Plan

- [x] Inventory the harness, collected tests, omitted modules, and exact duplicate test bodies.
- [x] Replace repeated Python compilation commands with one whole-tree pass.
- [x] Replace the pytest file allowlist with automatic discovery of `tests/`.
- [x] Verify collection covers the previously omitted suites and run the full harness.
- [x] Record the result and archive this completed plan.

## Evidence so far

- The current allowlist collects 671 outcomes in the full run but omits twelve unit/integration modules from its explicit paths.
- Whole-tree discovery collects 731 tests before skip evaluation.
- An AST-normalized audit found no exact duplicate test bodies, so deleting behavioral tests solely to lower the count would reduce signal rather than remove redundancy.
- The expanded harness exposed an import-time root binding defect in `update_seen_jobs.py`; runtime root resolution now makes the script isolated and testable.
- Final verification: 703 passed, 28 skipped in 177.90 seconds.
