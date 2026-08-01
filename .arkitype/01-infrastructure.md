# Infrastructure

```yaml
INFRASTRUCTURE:
  runtime_stack:
    language: python
    language_version_constraint: "python3 (repo scripts use stdlib + pytest/playwright in dev env)"
    framework_style: "scripted CLI pipeline (no web framework)"
    package_manager:
      tool: pip
      lockfile: none
      declared_dev_dependencies:
        - pytest==9.0.2
        - playwright==1.58.0
    shell_runtime: bash
  repository_layout_contract:
    entrypoints:
      - scripts/bootstrap_machine.sh
      - scripts/setup_machine.sh
      - scripts/run_track.sh
      - scripts/run_scheduled_jobs.sh
      - scripts/discover_jobs.py
      - scripts/render_digest.py
      - scripts/send_digest_email.py
      - scripts/send_digest_telegram.py
    tracked_example_track: tracks/test_workflow
  build_and_run_commands:
    bootstrap_env:
      - bash scripts/bootstrap_venv.sh
      - bash scripts/bootstrap_machine.sh --agent <codex|claude|gemini>
    run_track:
      - bash scripts/run_track.sh --track <track-slug>
      - bash scripts/run_track.sh --track <track-slug> --delivery <logseq|email|telegram>
    schedule_config:
      - ./.venv/bin/python scripts/configure_schedule.py --track <track-slug> --cadence <daily|weekly|monthly> --time HH:MM [--weekday mon] [--month-day N] [--delivery ...]
      - bash scripts/install_scheduler.sh
    integration_loop:
      - ./.venv/bin/python scripts/integrate_next_source.py --track <track-slug>
      - ./.venv/bin/python scripts/start_source_integration.py --track <track-slug>
    verification:
      - bash scripts/test.sh
  hosting_target:
    primary_mode: local_machine_checkout
    scheduler_backends:
      linux: cron (per-minute dispatcher)
      macos: launchd LaunchAgent
    persistent_state_paths:
      - .env.local
      - .schedule.local
      - .scheduler/
      - tracks/<track>/
      - artifacts/
      - logs/
      - shared/ranked_jobs/
  environment_variables:
    core_runtime:
      - name: JOB_AGENT_ROOT
        purpose: absolute repo root used by scripts
        example: /absolute/path/to/repo
      - name: JOB_AGENT_ENV_FILE
        purpose: override path to machine-local env exports file
        example: /absolute/path/to/repo/.env.local
      - name: JOB_AGENT_PROVIDER
        purpose: select automation provider
        allowed: [codex, claude, gemini]
      - name: JOB_AGENT_BIN
        purpose: executable path/name for selected provider CLI
        example: /usr/local/bin/codex
      - name: JOB_AGENT_CODER_BIN
        purpose: optional coder-only binary override
      - name: JOB_AGENT_REVIEWER_BIN
        purpose: optional reviewer-only binary override
      - name: JOB_AGENT_PYTHON
        purpose: python executable override for setup hook installers
    scheduling:
      - name: JOB_AGENT_SCHEDULE_FILE
        purpose: override .schedule.local path
      - name: JOB_AGENT_SCHEDULER_DIR
        purpose: override generated scheduler artifact directory
      - name: JOB_AGENT_SCHEDULER_STATE_DIR
        purpose: scheduler dedup stamp location
      - name: JOB_AGENT_SCHEDULE_TIME
        purpose: injected current time for scheduler/testing
      - name: JOB_AGENT_SCHEDULE_STAMP
        purpose: injected current datetime stamp for scheduler/testing
      - name: JOB_AGENT_SCHEDULE_DATE
        purpose: injected current date for scheduler/testing
      - name: JOB_AGENT_SCHEDULE_WEEKDAY
        purpose: injected weekday for scheduler/testing
      - name: JOB_AGENT_SCHEDULE_MONTH_DAY
        purpose: injected month day for scheduler/testing
    run_timeouts_and_heartbeats:
      - name: TIMEOUT_SECS
        purpose: max agent phase wall-clock timeout in run_track.sh
      - name: DISCOVERY_TIMEOUT_SECS
        purpose: max discovery artifact generation timeout
      - name: DISCOVERY_HEARTBEAT_SECS
        purpose: discovery heartbeat interval
      - name: AGENT_HEARTBEAT_SECS
        purpose: agent heartbeat interval
      - name: AGENT_IDLE_TIMEOUT_SECS
        purpose: terminate silent agent sessions
    secrets_loading:
      - name: JOB_AGENT_SECRETS_FILE
        purpose: absolute path to external shell file containing exported secrets
      - name: JOB_AGENT_RUNTIME_SECRETS_FILE_LOADED
        purpose: sentinel set when secrets file is sourced
    delivery_email_nonsecret:
      - JOB_AGENT_EMAIL_PROVIDER
      - JOB_AGENT_EMAIL_ACCOUNT
      - JOB_AGENT_SMTP_HOST
      - JOB_AGENT_SMTP_PORT
      - JOB_AGENT_SMTP_FROM
      - JOB_AGENT_SMTP_TO
      - JOB_AGENT_SMTP_USERNAME
      - JOB_AGENT_SMTP_PASSWORD_CMD
      - JOB_AGENT_SMTP_TLS
    delivery_email_secret:
      - JOB_AGENT_SMTP_PASSWORD
    delivery_telegram_nonsecret:
      - JOB_AGENT_TELEGRAM_CHAT_ID
      - JOB_AGENT_TELEGRAM_API_BASE
      - JOB_AGENT_TELEGRAM_BOT_TOKEN_CMD
    delivery_telegram_secret:
      - JOB_AGENT_TELEGRAM_BOT_TOKEN
    optional_logseq:
      - LOGSEQ_GRAPH_DIR
    provider_tuning:
      - JOB_AGENT_CLAUDE_PERMISSION_MODE
      - JOB_AGENT_CLAUDE_REVIEWER_ALLOWED_TOOLS
      - JOB_AGENT_CLAUDE_CODER_ALLOWED_TOOLS
      - JOB_AGENT_CLAUDE_SCHEDULED_ALLOWED_TOOLS
      - JOB_AGENT_GEMINI_APPROVAL_MODE
      - JOB_AGENT_GEMINI_CODER_APPROVAL_MODE
      - JOB_AGENT_GEMINI_REVIEWER_APPROVAL_MODE
      - JOB_AGENT_GEMINI_SCHEDULED_APPROVAL_MODE
      - JOB_AGENT_GEMINI_SETUP_APPROVAL_MODE
      - JOB_AGENT_GEMINI_SETUP_MODEL
      - JOB_AGENT_GEMINI_SANDBOX
      - JOB_AGENT_CODEX_SETUP_MODEL
      - JOB_AGENT_CODEX_SETUP_REASONING_EFFORT
  infrastructure_modes:
    mode_a_local_docker_compose:
      supported: false
      compose_spec: null
      notes: "No Dockerfile/compose manifests present; runtime is host shell + local Python virtualenv."
    mode_b_existing_hosted_endpoints:
      supported: true
      discovery:
        source_endpoints: "Declared per track source row (sources.json)."
        config_path: tracks/<track>/sources.json
      notification_endpoints:
        telegram_api_base: "From SITE_PROFILE.external_service_endpoints.telegram.api_base_default or JOB_AGENT_TELEGRAM_API_BASE"
        smtp_host: "Derived from provider preset or JOB_AGENT_SMTP_HOST"
  ci_and_deploy:
    in_repo_ci_config: none_detected
    verification_script: scripts/test.sh
    deployment_model: "No hosted deploy pipeline in repository; usage is local automation workflow."
```
