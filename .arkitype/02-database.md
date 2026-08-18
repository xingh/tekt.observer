# Database

## I9–I14 private file model

`profile/interests.json` stores global interests; `profile/portfolios.json` stores named ordered track/interest collections and one default; `tracks/<slug>/track.json` stores display/lifecycle/default-audience/mapping metadata; `tracks/<slug>/taxonomy.json` stores editable topics and audiences; and `logs/portfolio-operations.json` stores bounded operation history. IDs are immutable validated slugs. Sidecar flock plus atomic rename protects writes. Dangling references and orphaned mappings are rejected. Missing files yield an implicit All Tracks projection and never cause automatic migration.

```yaml
DATABASE:
  architecture:
    type: file_backed_json_state
    relational_database_present: false
    statement: "No SQL/ORM datastore is used; canonical persisted state is JSON/Markdown files under tracks/, artifacts/, and shared/."
    source_of_record:
      primary:
        - scripts/source_config.py (validators, writers, atomic write + lock semantics)
        - scripts/digest_json.py (structured digest schema + normalization)
        - scripts/discover/runner.py (discovery artifact payload shape)
      secondary_examples:
        - shared/templates/track_sources.json
        - shared/templates/track_source_state.json
        - shared/digest_schema.md
        - tracks/test_workflow/*.json
    constellation_invariance: "Schema contracts are invariant across tracks/sites; row-level/source-level content differs by profile and track configuration."
  collections:
    - name: tracks/<track>/sources.json
      schema:
        schema_version: {type: int, required: true, const: 1}
        track: {type: string, required: true, non_empty: true}
        track_terms: {type: array, required: true, items: string_non_empty}
        sources:
          type: array
          required: true
          items:
            id: {type: string, required: true, unique_within_file: true}
            name: {type: string, required: true}
            url: {type: string, required: true}
            discovery_mode: {type: string, required: true, enum_source: discover.registry.modes}
            cadence_group: {type: string, required: true, enum: [every_run, every_3_runs, every_month]}
            search_terms:
              type: object
              required: false
              fields:
                mode: {type: string, enum: [append, override], default: append}
                terms: {type: array, items: string_non_empty}
            filters:
              type: object
              required: false
              additional_properties: {type: array, items: string_non_empty}
      indexes_and_keys:
        primary_key: sources[].id
    - name: tracks/<track>/source_state.json
      schema:
        schema_version: {type: int, required: true, const: 1}
        track: {type: string, required: true}
        sources:
          type: object
          key: source_id
          value:
            last_checked: {type: string_or_null, format: YYYY-MM-DD}
            integration:
              type: object
              required: false
              fields:
                status: {type: string, enum: [pending, integration_needed, deferred, pass, blocked]}
                priority: {type: int, default: 0}
                attempts: {type: int, default: 0}
                last_attempted: {type: string_or_null, format: YYYY-MM-DD}
                next_action: {type: string, required: false}
                last_ticket_summary: {type: string, required: false}
                last_note: {type: string, required: false}
                canary:
                  type: object
                  required: false
                  fields:
                    title: {type: string, required: false}
                    url: {type: string, required: false}
                artifacts:
                  type: object
                  required: false
                  fields:
                    last_discovery: {type: string, required: false}
                    last_eval: {type: string, required: false}
                    last_loop_summary: {type: string, required: false}
      indexes_and_keys:
        primary_key: sources.<source_id>
    - name: tracks/<track>/seen_jobs.json
      schema:
        schema_version: {type: int, required: true, const: 1}
        track: {type: string, required: true}
        jobs:
          type: array
          items:
            date_seen: {type: string, format: YYYY-MM-DD}
            company: {type: string}
            title: {type: string}
            location: {type: string, default: unknown}
            url: {type: string}
      dedupe_rule: normalize(company,title,url)
    - name: artifacts/discovery/<track>/<date>.json
      schema:
        schema_version: {type: int, const: 1}
        track: {type: string}
        today: {type: string, format: YYYY-MM-DD}
        generated_at: {type: string, format: ISO8601}
        mode: {type: string, enum: [list_sources, plan_only, discover]}
        sources:
          type: array
          items:
            source_id: {type: string}
            source: {type: string}
            url: {type: string}
            source_url: {type: string}
            discovery_mode: {type: string}
            cadence_group: {type: string}
            due_today: {type: boolean}
            status: {type: string, enum: [complete, partial, failed]}
            listing_pages_scanned: {type: int_or_string}
            search_terms: {type: array, items: string}
            search_terms_tried: {type: array, items: string}
            result_pages_scanned: {type: string}
            direct_job_pages_opened: {type: int}
            enumerated_jobs: {type: int}
            matched_jobs: {type: int}
            limitations: {type: array, items: string}
            filters: {type: object, additional_properties: array_of_strings}
            candidates:
              type: array
              items:
                employer: {type: string}
                title: {type: string}
                url: {type: string}
                source_url: {type: string}
                alternate_url: {type: string, required: false}
                location: {type: string, default: unknown}
                remote: {type: string, default: unknown}
                matched_terms: {type: array, items: string}
                notes: {type: string}
                description: {type: string}
                description_truncated: {type: boolean}
      indexes_and_keys:
        primary_key: sources[].source_id
    - name: artifacts/digests/<track>/<date>.json
      schema_reference: shared/digest_schema.md
      schema:
        schema_version: {type: int, const: 1}
        track: {type: string}
        date: {type: string, format: YYYY-MM-DD}
        runs:
          type: array
          min_items: 1
          first_item_rule: kind == initial
          items:
            kind: {type: string, enum: [initial, update]}
            generated_at: {type: string, format: ISO8601_like}
            executive_summary: {type: string, nullable: true}
            recommended_actions: {type: array, items: string}
            top_matches:
              type: array
              items:
                job_key: {type: string_or_null}
                company: {type: string}
                title: {type: string}
                listing_url: {type: string}
                alternate_url: {type: string_or_null}
                location: {type: string_or_null}
                remote: {type: string_or_null}
                team_or_domain: {type: string_or_null}
                posted_date: {type: string_or_null}
                updated_date: {type: string_or_null}
                source: {type: string_or_null}
                source_url: {type: string_or_null}
                fit_score: {type: number_or_null}
                recommendation: {type: string, enum: [apply_now, watch, skip]}
                why_match: {type: array, items: string}
                concerns: {type: array, items: string}
            other_new_roles:
              type: array
              items:
                company: {type: string}
                title: {type: string}
                listing_url: {type: string}
                recommendation: {type: string, enum: [apply_now, watch, skip]}
                short_note: {type: string}
                fit_score: {type: number_or_null}
            filtered_roles:
              type: array
              items:
                company: {type: string}
                title: {type: string}
                reason_filtered_out: {type: string}
                listing_url: {type: string_or_null}
            source_notes:
              type: array
              items:
                source: {type: string}
                discovery_mode: {type: string}
                status: {type: string, enum: [complete, partial, failed]}
                listing_pages_scanned: {type: string_number_or_null}
                search_terms_tried: {type: array, items: string}
                result_pages_summary: {type: string_number_or_null}
                direct_job_pages_opened: {type: string_number_or_null}
                limitations: {type: array, items: string}
                note: {type: string_or_null}
            notes_for_next_run: {type: array, items: string}
            discovery_artifacts: {type: array, items: string}
    - name: shared/ranked_jobs/<track>.json
      schema:
        track: {type: string}
        generated_at: {type: string, format: ISO8601}
        jobs:
          type: array
          items:
            job_key: {type: string}
            company: {type: string}
            title: {type: string}
            url: {type: string}
            fit_score: {type: number_or_null}
            date_seen: {type: string, format: YYYY-MM-DD}
            date_seen_page: {type: string}
            last_seen: {type: string, format: YYYY-MM-DD}
            times_seen: {type: int}
      sort_order: fit_score_desc_then_date_company_title
    - name: artifacts/evals/<track>/<source_slug>/<date>.json
      schema:
        schema_version: {type: int, const: 1}
        generated_at: {type: string}
        track: {type: string}
        source: {type: string}
        date: {type: string}
        artifact_path: {type: string}
        canary:
          title: {type: string}
          url: {type: string}
        deterministic:
          confidence: {type: string, enum: [high, medium, low, failed]}
          checks: {type: array}
          warnings: {type: array, items: string}
        reviewer:
          status: {type: string, enum: [completed, skipped, blocked]}
          defects: {type: array}
        final_status: {type: string, enum: [pass, integration_needed, blocked]}
        integration_ticket: {type: object_or_null}
    - name: artifacts/evals/<track>/<source_slug>/<date>.source_integration_loop.json
      schema:
        schema_version: {type: int, const: 1}
        track: {type: string}
        source: {type: string}
        date: {type: string}
        max_attempts: {type: int}
        integration_attempts_used: {type: int}
        attempts: {type: array}
        final_status: {type: string, enum: [pass, blocked, retry_limit, running]}
  foreign_keys_and_relationships:
    - from: source_state.sources.<source_id>
      to: sources.sources[].id
      rule: logical reference (application-enforced)
    - from: discovery.sources[].source_id
      to: sources.sources[].id
      rule: logical reference
    - from: eval.source
      to: discovery.sources[].source
      rule: logical reference by source display name
  access_control:
    rls_policies: none
    access_rules: "Local filesystem permissions and gitignore separation; no DB-level ACL layer."
  seed_data:
    canonical_templates:
      - shared/templates/track_sources.json
      - shared/templates/track_source_state.json
      - shared/templates/track_match_rules.json
    tracked_example_seed:
      track: test_workflow
      sources:
        - id: local_test_board
          name: Local Test Board
          discovery_mode: html
          cadence_group: every_run
      source_state:
        local_test_board:
          last_checked: null
```
