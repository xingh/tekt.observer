# Multi-Agent CLI Platform with Command Phases

Status: planned
Owner: copilot; agent_id: unknown
Last updated: 2026-08-01 23:30 UTC

## Goal

Evolve tekt.observer from a single-domain observation tool into a generalized platform where:
- Multiple agent CLIs (gh copilot, pi, codex, claude, gemini) each contribute to the phases where they excel
- Adding new sources is as simple as editing a file or using a web-based interface
- Code for source connectors ("sensors") is auto-generated from exploration results
- The entire pipeline is idempotent — re-running any phase produces consistent, additive results

## Current State

### Existing agent provider model (`scripts/agent_provider.py`)
- Supports: codex, claude, gemini as primary providers
- Pattern: binary resolution → command building → subprocess invocation
- Roles: `reviewer`, `coder`, `scheduled`
- No concept of "auxiliary" tools or phase-specific provider selection

### Existing pipeline (`scripts/run_track.sh`)
- Linear: discover → agent (find + rank) → post-process → deliver
- Phase boundaries are implicit (script calls) rather than explicit (protocol)
- Each phase's inputs/outputs are coupled to the track-run context

### Gaps
- No way to run a single phase independently with arbitrary inputs
- No auxiliary CLI integration (only primary provider used)
- No auto-generation of sensor/provider code from exploration results
- Source addition requires manual config editing + code authoring
- No web interface for source management

## Implementation Plan

### Layer 1 — Command-phase abstraction

- [ ] Define `Phase` protocol in `scripts/phases/__init__.py`
  ```python
  class Phase(Protocol):
      name: str
      inputs: dict[str, type]
      outputs: dict[str, type]
      def run(self, context: PhaseContext) -> PhaseResult: ...
  ```
- [ ] Implement `scripts/phases/explore.py` — wraps crawl4ai probing + URL validation
- [ ] Implement `scripts/phases/seek.py` — directed retrieval via sensor config
- [ ] Implement `scripts/phases/gather.py` — refactor from `discover_jobs.py` dispatcher
- [ ] Implement `scripts/phases/organize.py` — schema mapping (from digest_json patterns)
- [ ] Implement `scripts/phases/understand.py` — agent orchestration (from rank-jobs pattern)
- [ ] Implement `scripts/phases/generate.py` — output rendering + delivery
- [ ] Add CLI entry point: `scripts/tekt.py <phase> [args]`
- [ ] Verify `run_track.sh` can be expressed as gather→organize→understand→generate chain

### Layer 2 — Auxiliary CLI integration

- [ ] Create `scripts/auxiliary_cli.py` with:
  - `invoke_copilot_suggest(prompt: str) -> str | None` — calls `gh copilot suggest` if available
  - `invoke_pi_reason(prompt: str) -> str | None` — calls Pi CLI if available
  - Graceful degradation: returns None when CLI unavailable
- [ ] Add `TEKT_AUX_PROVIDERS` env var (comma-separated: `copilot,pi`)
- [ ] Wire into `/explore` phase: suggest scraping commands for discovered API endpoints
- [ ] Wire into `/understand` phase: supplementary reasoning pass for ambiguous items

### Layer 3 — Sensor auto-generation

- [ ] Define sensor definition schema (YAML/JSON):
  ```yaml
  sensor:
    name: company_jobs
    url: https://example.com/careers
    strategy: css  # or api, rss, browser
    selectors:
      container: "div.job-listing"
      title: "h3.title"
      url: "a.apply-link@href"
      location: "span.location"
    pagination:
      type: next_button  # or infinite_scroll, offset_param, cursor
      selector: "a.next-page"
    output_schema: candidate  # maps to Candidate dataclass
  ```
- [ ] Implement `scripts/phases/explore.py` → sensor generation:
  - crawl4ai `JsonCssExtractionStrategy` identifies page structure
  - Generates draft sensor definition
  - Validates against live content
- [ ] Implement `scripts/generate_sensor.py`:
  - Takes sensor definition → produces Python provider stub
  - Registers in `discover/registry.py`
  - Runs canary validation
- [ ] Wire into `source_integration.py` loop:
  - Before full coder invocation, attempt auto-generation
  - If auto-generated sensor passes validation, skip coder phase

### Layer 4 — Source management interface

- [ ] Extend `sources.json` schema or add `sources.yaml` with:
  - Human-readable format with comments
  - Schema validation on save
  - Optional sensor definition inline
- [ ] Add `scripts/tekt.py sources` subcommand:
  - `tekt sources list` — show configured sources with status
  - `tekt sources add <url>` — auto-detect and generate sensor
  - `tekt sources edit <name>` — open in $EDITOR
  - `tekt sources validate` — schema + canary check all sources
- [ ] Future: web-based UI (Notion-like)
  - Read/write the same `sources.json` backing file
  - Backed by MCP server (RM-017 Phase 2) or standalone web app
  - Display columns: name, URL, status, last_checked, cadence, mode, health

## Progress Log

- 2026-08-01 23:30 — Plan created. Knowledge entries for GitHub Copilot CLI and Pi CLI added to `.manage/6.knowledge.md`. Project entries added to `.manage/2.projects.md`. Process definitions for all six phases added to `.manage/3.processes.md`. Roadmap item RM-018 added.

## Handoff Notes

This plan depends on:
- **RM-016** (crawl4ai integration) for Layer 3 sensor generation
- **RM-017** (MCP server) for Layer 4 web interface backend

The phase abstraction (Layer 1) can proceed independently. Start there.

Key architectural decisions:
- Auxiliary CLIs are helpers, not providers — they don't replace the codex/claude/gemini model
- Phases are composable — any phase can be run alone or chained
- Sensor definitions are declarative — the system generates code from them, not vice versa
- Source management is file-first — the web UI reads/writes the same JSON/YAML files

## Verification

- [ ] `scripts/phases/__init__.py` defines Phase protocol with type hints
- [ ] Each phase module can be imported and run independently with test fixtures
- [ ] `tekt explore <url>` produces an exploration artifact for a known working URL
- [ ] `tekt sources add <url>` generates a sensor definition for a simple career page
- [ ] `bash scripts/test.sh` passes after all changes

## Caveats

- Pi CLI has no official stable API; community wrappers may break. Integration should be behind a feature flag.
- GitHub Copilot CLI requires `gh` authentication; not available in CI environments without special setup.
- Sensor auto-generation will not work for all page structures — complex JS-heavy SPAs will still need manual providers.
- Web UI is a longer-term goal; file-based management is the minimum viable interface.
- The phase abstraction must not break the existing `run_track.sh` pipeline — it wraps rather than replaces.
