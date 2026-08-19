# Integrate browser-use as a Discovery Driver for crawl4ai

Status: planned
Owner: claude; agent_id: cse_0163bn5gx9zi4faGbsaEL9ZT
Last updated: 2026-08-03 00:23 UTC

## Goal

Use browser-use (https://github.com/browser-use/browser-use) as a *reconnaissance* driver that discovers how to navigate and extract from a career page, then feeds that structure (CSS selectors, pagination mechanism, cookie-consent pattern) into crawl4ai's deterministic extraction. Longer term, package tekt.observer's data-gathering capabilities as browser-use custom tools so the combination forms a complete open-source-signals plugin (issue #11).

Division of labor:
- **browser-use** discovers page structure and handles interactive flows (LLM-driven, non-deterministic, costs per action)
- **crawl4ai** extracts at scale using the discovered CSS selectors (deterministic, zero LLM cost)
- **tekt.observer** orchestrates: track management, source registry, dedup, ranking, digests

## Current State

- Research findings recorded in `.manage/6.knowledge.md` ("browser-use — research findings"); summary plan in `.manage/1.plans.md`.
- Roadmap item: RM-019 (`.knowledge/roadmap.md`). Depends on RM-016 (crawl4ai integration) Phase 1; complements RM-018's `/explore` phase.
- `filters` values in `sources.json` are flat string arrays; registry dispatch is sync (wrap async with `asyncio.run`).
- Playwright is already a dev dependency (`==1.58.0`); browser-use requires Python >= 3.11 and would be an *optional* dependency.
- The browser-use agent needs an LLM API key at runtime; it must flow through the existing `scripts/runtime_env.py` secret boundary.

## Implementation Plan

### Phase 1 — Source-structure discovery driver (near-term; blocked on RM-016 Phase 1)

- [ ] Add `scripts/probe_with_browser_use.py`: given a careers URL, run a browser-use agent that reports job-card/title/location/link CSS selectors, pagination mechanism, and cookie-consent pattern
- [ ] Emit output in the shape `sources.json` expects for the `crawl4ai_browser` discovery mode (flat string arrays in `filters`)
- [ ] Document the probe step in `.knowledge/contributing/adding-sources.md` and reference it from the `explore-start` skill
- [ ] Add browser-use as an optional dependency (documented, not in `requirements-dev.txt`); degrade gracefully when absent

### Phase 2 — Optional `browser_use` discovery mode (medium-term)

- [ ] Register a `browser_use` discovery mode in the provider registry, gated behind `requires = ("browser-use",)`
- [ ] Agent task template receives employer-specific parameters from `filters` in `sources.json`; returns structured job data
- [ ] Route LLM API key through `scripts/runtime_env.py`
- [ ] Restrict use to sources that genuinely need interactive multi-step navigation (cost control)

### Phase 3 — tekt.observer as browser-use custom tools (medium-term)

- [ ] Expose `discover_jobs`, `evaluate_source`, `rank_jobs`, and `probe_source` as browser-use custom tools
- [ ] Coordinate with RM-017 Phase 2 (MCP server) — same tool surface, two frontends

## Progress Log

- 2026-08-02 - Research completed and recorded in `.manage/6.knowledge.md`; plan summarized in `.manage/1.plans.md`; roadmap item added (PR #12)
- 2026-08-03 00:23 - Renumbered roadmap item RM-018 → RM-019 (RM-018 was claimed on master by the multi-agent CLI platform); merged master; promoted this plan doc to a tracked file

## Handoff Notes

No implementation has started. Phase 1 is blocked on RM-016 (crawl4ai `crawl4ai_browser` mode) landing first, since the probe output targets that mode's config shape. The `browser-use skill install` step is a user-local machine action, not a repo change — if adopted, document it in `.knowledge/machine_setup.md`.

## Verification

- [ ] Phase 1: probe a known-good source (e.g. an existing Greenhouse/Ashby page) and confirm emitted selectors work in the `crawl4ai_browser` mode
- [ ] Phase 2: one interactive source runs end-to-end via `browser_use` mode in a dry run
- [ ] `bash scripts/test.sh`, when code lands (plan-only change for now)

## Caveats

- **LLM cost**: every agent run costs per action; keep browser-use to discovery/setup, not routine extraction.
- **Non-determinism**: agent output must be validated and frozen into deterministic config (CSS selectors in `sources.json`) before production use.
- **Version floor**: browser-use requires Python >= 3.11; keep it optional so the core workflow stays dependency-light.
- The issue text also asks to install browser-use and connect it to a live browser; that is a user-local machine-setup action outside this repo-level plan.
