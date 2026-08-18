# Software

## I9–I14 application services

`portfolio_state.py` owns validation, reference integrity, explicit initialization, taxonomy precedence, and unified item adaptation. `serve_html.py` owns server-rendered portfolio views and `/api/v1` policy. `portfolio_operations.py` owns queued/running/needs_input/validating/first_run/ready/failed/cancelled state with bounded logs. Existing deterministic pipeline and CLI entrypoints remain canonical.

```yaml
SOFTWARE:
  execution_model:
    style: "deterministic Python + shell orchestration, with optional external coding-agent subprocesses"
    entrypoint_script: scripts/run_track.sh
  command_interfaces:
    - name: discover_jobs
      command: scripts/discover_jobs.py
      inputs:
        required: [--track]
        optional: [--today, --source*, --cadence-group*, --due-only, --list-sources, --plan-only, --timeout-seconds, --output, --latest-output, --pretty, --progress]
      outputs:
        artifact: artifacts/discovery/<track>/<today>.json
        mode_values: [list_sources, plan_only, discover]
      behavior:
        - load and validate tracks/<track>/sources.json + source_state.json
        - normalize track/source terms (append or override)
        - dispatch each source by discovery_mode through discover.registry
        - apply track-level filters and enrich candidate job descriptions
    - name: run_track
      command: scripts/run_track.sh
      inputs:
        required: [--track]
        optional: [--delivery*, --timeout-secs, --discovery-timeout-secs]
      outputs:
        - artifacts/discovery/<track>/<date>.json
        - artifacts/digests/<track>/<date>.json (produced by agent phase)
        - tracks/<track>/digests/<date>.md
        - tracks/<track>/seen_jobs.json
        - shared/ranked_jobs/<track>.json
        - tracks/<track>/ranked_overview.md
      behavior:
        - pre-generates discovery artifact
        - invokes provider CLI (codex/claude/gemini) with track-run prompt
        - post-processes source state, digest markdown, seen jobs, ranked overview
        - optionally dispatches logseq/email/telegram delivery
    - name: run_scheduled_jobs
      command: scripts/run_scheduled_jobs.sh
      inputs:
        schedule_file: .schedule.local
      outputs:
        - invokes run_track.sh for each due entry
        - writes daily dedup stamps under .scheduler/state/
      behavior:
        - validates schedule grammar and time window matching
        - deduplicates per job/day (+scheduled time)
        - supports cadence: daily, weekly, monthly
    - name: configure_schedule
      command: scripts/configure_schedule.py
      behavior: upserts one schedule line per track, replacing prior line for that track
    - name: eval_source_quality
      command: scripts/eval_source_quality.py
      outputs: artifacts/evals/<track>/<source_slug>/<date>.json
      behavior:
        - deterministic validation of one source coverage payload
        - optional LLM reviewer pass (auto/off/force)
        - emits integration_ticket when defects remain
    - name: integrate_next_source
      command: scripts/integrate_next_source.py
      behavior:
        - selects highest-priority pending source from source_state integration queue
        - runs discovery + eval
        - if ticket strategy is config tuning, mutates source config and re-evaluates
        - otherwise invokes source_integration.py coding loop
        - updates integration status and artifact pointers in source_state
    - name: source_integration
      command: scripts/source_integration.py
      behavior:
        - iterative coder subprocess loop with timeout/idle guards
        - logs stdout/stderr/last message and postmortem per attempt
        - rediscovery + reeval after each attempt
        - finishes pass, blocked, or retry_limit
    - name: start_source_integration
      command: scripts/start_source_integration.py
      behavior: starts detached integrate_next_source jobs and appends job records to logs/source-integration/jobs.jsonl
    - name: render_digest
      command: scripts/render_digest.py
      behavior: validates structured digest JSON and renders markdown digest
    - name: send_digest_email
      command: scripts/send_digest_email.py
      behavior:
        - loads digest + ranked overview
        - renders plain + html digest content
        - dry-run preview or SMTP send
    - name: send_digest_telegram
      command: scripts/send_digest_telegram.py
      behavior:
        - renders digest message body
        - splits by Telegram size limits
        - dry-run preview or Telegram Bot API sendMessage
  provider_registry:
    adapter_source: scripts/discover/registry.py
    supported_discovery_modes:
      - alphatheta_html
      - apple_jobs
      - ashby_api
      - ashby_html
      - asml_browser
      - auswaertiges_amt_json
      - automattic_browser
      - bamboohr_api
      - bnd_career_search
      - bosch_autocomplete
      - browser
      - bundeswehr_jobsuche
      - coinbase_browser
      - cybernetica_teamdash
      - demant_rss
      - dover_api
      - ecb_avature_rss
      - eightfold_api
      - enbw_phenom
      - factorial
      - getro_api
      - greenhouse_api
      - hackernews_jobs
      - hackernews_whoishiring_api
      - harman_html
      - helsing_browser
      - hibob_api
      - html
      - iacr_jobs
      - ibm_api
      - icims_html
      - infineon_api
      - jobvite_html
      - knds_jobboard
      - krisp_html
      - leastauthority_careers
      - lever_json
      - lifeatspotify_api
      - neclab_jobs
      - partisia_site
      - pcd_team
      - personio_page
      - qedit_inline
      - qusecure_careers
      - recruitee_inline
      - rheinmetall_html
      - secunet_jobboard
      - sennheiser_rss
      - service_bund_links
      - service_bund_search
      - softgarden_html
      - teamtailor_api
      - thales_browser
      - thales_html
      - trailofbits_browser
      - ultipro_api
      - verfassungsschutz_rss
      - workable_api
      - workday_api
      - yc_jobs_board
  business_rules:
    - only due sources are queried in scheduled run mode unless explicitly overridden
    - source_state last_checked is advanced only for discovery status=complete
    - seen_jobs dedup key is normalized(company,title,url)
    - ranked_overview carries highest observed fit_score and count of times_seen
    - source integration queue prioritizes higher integration.priority and prevents repeated same-day attempts unless --force
    - deterministic source validator blocks integration on missing core fields, off-domain URLs, empty artifacts, duplicate URL defects, or missing required canary
  auth_and_authorization:
    application_auth: none
    secrets_policy:
      - .env.local stores non-secret runtime config
      - JOB_AGENT_SECRETS_FILE stores exported secrets outside repository root
      - plaintext repo-local JOB_AGENT_SMTP_PASSWORD is explicitly rejected unless loaded from external secrets file
  background_jobs:
    scheduler: scripts/run_scheduled_jobs.sh
    detached_integration_workers: scripts/start_source_integration.py -> integrate_next_source.py
  third_party_integrations:
    - name: codex_cli
      operations: scheduled/interactive coding-agent execution
      credentials_source: local CLI authentication
    - name: claude_code_cli
      operations: scheduled/interactive coding-agent execution
      credentials_source: local CLI authentication
    - name: gemini_cli
      operations: scheduled/interactive coding-agent execution
      credentials_source: local CLI authentication
    - name: telegram_bot_api
      operations: sendMessage
      credentials_source: JOB_AGENT_TELEGRAM_BOT_TOKEN_CMD or JOB_AGENT_SECRETS_FILE
    - name: smtp_servers
      operations: STARTTLS/SSL/plain SMTP send
      credentials_source: JOB_AGENT_SMTP_PASSWORD_CMD or JOB_AGENT_SECRETS_FILE
    - name: public_career_endpoints
      operations: HTTP fetch/json/rss/browser scraping per discovery mode
      credentials_source: typically none (public sources)
  capability_toggles:
    - name: reviewer_mode
      controls: whether LLM reviewer runs in eval_source_quality
      values: [auto, off, force]
      default: auto
    - name: delivery_targets
      controls: post-run delivery channels
      values: [logseq, email, telegram]
      default: []
    - name: cadence_group
      controls: source due logic
      values: [every_run, every_3_runs, every_month]
      default: every_run
    - name: search_terms_mode
      controls: source term merge strategy
      values: [append, override]
      default: append
    - name: provider
      controls: automation engine selection
      values: [codex, claude, gemini]
      default: codex
    - name: config_tuning_strategy
      controls: whether integration can be fixed by config mutation before coding
      values: [config_url_correction, config_terms_override, config_terms_append, config_native_filters]
      default: n/a (ticket-driven)
  open_decisions:
    - No in-repo policy defines a strict retention/cleanup lifecycle for artifacts/ logs/ and eval attempt files beyond gitignore boundaries.
    - SMTP provider presets exist, but OAuth-native delivery workflows are intentionally out of scope and not standardized.
```
