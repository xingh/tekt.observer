# Interface

## I9–I14 browser and JSON interfaces

The live `/` route is a responsive named-portfolio dashboard with track health and a unified signal inbox. Filters cover portfolio, track, audience, topic, date/text; items expose source provenance and normalized 0–100 scores. Existing report/feed/trend/source/raw routes remain. `/api/v1` exposes portfolio and interest CRUD, track metadata/taxonomy, item queries, feedback, and pollable operations. Guided setup shares the operation state model and activates a track only after validation and a viewable first artifact.

```yaml
INTERFACE:
  interface_type: cli_first_with_generated_markdown_outputs
  routes_and_views:
    - id: cli.bootstrap_machine
      entrypoint: scripts/bootstrap_machine.sh
      purpose: first-time machine bootstrap and optional launch of guided setup
      verified: static-analysis
    - id: cli.setup_machine
      entrypoint: scripts/setup_machine.sh
      purpose: generate/refresh machine-local runtime config and profile placeholders
      verified: static-analysis
    - id: cli.start_setup_agent
      entrypoint: scripts/start_setup_agent.sh
      purpose: launch provider-specific guided setup contract for creating/curating tracks
      verified: static-analysis
    - id: cli.run_track
      entrypoint: scripts/run_track.sh
      purpose: execute one track run and optional delivery
      verified: static-analysis
    - id: cli.run_scheduled_jobs
      entrypoint: scripts/run_scheduled_jobs.sh
      purpose: execute due schedule entries and prevent duplicate same-day runs
      verified: static-analysis
    - id: cli.discover_jobs
      entrypoint: scripts/discover_jobs.py
      purpose: deterministic source discovery and candidate extraction
      verified: static-analysis
    - id: cli.integrate_next_source
      entrypoint: scripts/integrate_next_source.py
      purpose: process one queued source integration task
      verified: static-analysis
    - id: cli.start_source_integration
      entrypoint: scripts/start_source_integration.py
      purpose: spawn background source integration workers
      verified: static-analysis
    - id: view.digest_markdown
      output_path: tracks/<track>/digests/<date>.md
      purpose: human-readable daily/update digest generated from structured JSON
      verified: static-analysis
    - id: view.ranked_overview_markdown
      output_path: tracks/<track>/ranked_overview.md
      purpose: persistent ranked history table of surfaced jobs
      verified: static-analysis
    - id: view.sources_markdown
      output_path: tracks/<track>/sources.md
      purpose: read-only summary of source config, cadence, term/filters
      verified: static-analysis
  shared_components:
    - name: digest_renderer_sections
      source: scripts/digest_json.py
      sections:
        - executive_summary
        - recommended_actions
        - top_matches
        - other_new_roles
        - filtered_roles
        - source_notes
        - seen_jobs_to_append
        - notes_for_next_run
      component_contract:
        run_header_fields: [run_timestamp, sources_checked, new_roles_found, high_signal_matches]
        top_match_fields: [title, company, listing_url, location, remote, team_or_domain, posted_date, source, why_match, concerns, fit_score, recommendation]
      used_by:
        - scripts/render_digest.py
        - scripts/send_digest_email.py (via digest_email)
        - scripts/send_digest_telegram.py (via digest_email rendering)
    - name: ranked_overview_table
      source: scripts/update_ranked_overview.py
      columns: [fit_score, company, title, listing_url, date_seen]
      used_by:
        - tracks/<track>/ranked_overview.md
        - scripts/digest_email.py ranked snippet
    - name: source_summary_tables
      source: scripts/source_config.py::render_sources_markdown
      sections:
        - cadence_group_tables
        - track_wide_terms
        - source_specific_terms_with_override_marker
        - source_specific_native_filters
      used_by:
        - scripts/render_sources_md.py
  interaction_patterns:
    - pattern: scheduled_run
      flow:
        - scheduler dispatches run_track with selected deliveries
        - run_track builds/uses discovery artifact
        - provider agent writes structured digest
        - post-processing updates state + markdown views
    - pattern: source_integration_queue
      flow:
        - queued source selected by priority/status/day guard
        - discovery + eval determine pass/config_tuning/coding_loop
        - state entry updated with attempts/artifact pointers/next action
    - pattern: delivery_preview_then_send
      flow:
        - dry-run for email/telegram can render preview without secrets-loaded send
        - send path requires resolved runtime secrets
  design_system:
    medium: markdown and plain text
    typography:
      headings: markdown H1-H4
      emphasis: bold, bullets, fenced blocks
    spacing: blank-line-separated sections with short bullet lists/tables
    color_usage: none in generated markdown
    responsive_behavior: not_applicable
  assets:
    screenshot_directory: .arkitype/assets/
    captured_files: []
    note: "No browser-rendered screenshots captured; repository has no first-party web UI runtime."
  open_decisions:
    - The issue template assumes page/component web UI extraction; this repository exposes CLI commands plus generated markdown views, so UI contracts are represented as command surfaces and rendered document sections.
```
