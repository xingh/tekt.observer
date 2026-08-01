# Agent Capability Record

```yaml
extracting_agent:
  identity: GitHub Copilot Coding Agent
  model: not-exposed-by-runtime
  host_tool: copilot-coding-agent-runtime
  extraction_date_utc: 2026-08-01

capabilities_used:
  filesystem_listing:
    used: true
    produced:
      - repository tree inventory
      - script/template/test location mapping
  code_search:
    used: true
    produced:
      - environment-variable inventory
      - discovery mode inventory
      - integration/eval behavior anchors
  file_reads:
    used: true
    produced:
      - source-of-record schema contracts from scripts + templates + shared schema docs
      - command-interface and pipeline behavior details
  shell_execution:
    used: true
    produced:
      - dynamic list of registered discovery modes via discover.registry
      - env-variable extraction via grep
  package_installation:
    used: false
  network_access:
    used: false
  dev_server_execution:
    used: false
  database_execution:
    used: false
  screenshot_capture:
    used: false

capabilities_missing:
  - capability: live web UI rendering and screenshot observation
    compensation_strategy: "Represented interface from static analysis of CLI entrypoints and markdown renderers; marked interface verification as static-analysis."
    affected_sections:
      - .arkitype/04-interface.md assets + verification markers
    confidence: medium_high
  - capability: live external endpoint verification (SMTP/Telegram/career sources)
    compensation_strategy: "Documented integrations from code contracts, environment variables, and defaults without probing real endpoints."
    affected_sections:
      - .arkitype/01-infrastructure.md hosted endpoints + env vars
      - .arkitype/03-software.md third_party_integrations
    confidence: medium
  - capability: relational DB introspection
    compensation_strategy: "Confirmed no RDBMS/ORM usage in repo; documented JSON file schemas as canonical datastore."
    affected_sections:
      - .arkitype/02-database.md
    confidence: high

build_toolchain:
  language_runtime: python3 + bash
  environment_bootstrap:
    - scripts/bootstrap_machine.sh
    - scripts/setup_machine.sh
    - scripts/bootstrap_venv.sh
  testing:
    - scripts/test.sh
    - pytest
  generated_docs:
    - scripts/render_discovery_modes_md.py
    - scripts/render_sources_md.py
  agent_provenance:
    provider_clis: [codex, claude, gemini]
    orchestration_points:
      - scripts/run_track.sh
      - scripts/source_integration.py

regeneration_requirements:
  minimum_capabilities:
    - can read/write repository files
    - can run bash + python commands
    - can create and use local Python virtualenv
    - can execute provider CLI selected in JOB_AGENT_PROVIDER
  recommended_capabilities:
    - network access for source discovery and delivery endpoints
    - ability to run scheduler backend (cron or launchd)
  graceful_fallbacks:
    - missing_network: "Regenerate config and rendering logic, skip live discovery/delivery verification."
    - missing_provider_cli: "Use deterministic scripts and static artifact fixtures to validate schema/render paths."
    - missing_scheduler_permissions: "Run manual track workflow via scripts/run_track.sh."

verification_status:
  observed_running:
    - command-level introspection for discovery mode registration (python invocation)
    - repository/static contract consistency checks via code and test fixture inspection
  static_analysis_only:
    - run_track end-to-end execution
    - external endpoint behavior
    - rendered digest screenshots
  overall_fidelity_expectation: high_for_schema_and_pipeline_contracts_medium_for_live_endpoint_runtime_details

readme_deviations:
  - deviation: "Repository is a CLI automation system rather than a browser site; interface extraction modeled as command surfaces + generated markdown documents."
    reason: "Issue template is web-centric; direct adaptation required to avoid fabricating route/component web UI."
  - deviation: "No .arkitype/assets screenshots were captured."
    reason: "No first-party web app runtime exists to render canonical pages; fidelity preserved through source-derived interface specification."
  - deviation: "Database section modeled as file-backed JSON contracts instead of SQL tables."
    reason: "Codebase uses validated JSON artifacts and track state files as durable datastore; no DB engine/migrations present."
```
