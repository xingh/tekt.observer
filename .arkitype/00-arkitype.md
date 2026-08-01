# Identity & Site Profile

```yaml
SITE_PROFILE:
  site_name: jobwatch
  canonical_repository:
    primary: https://github.com/jvdheyden/jobwatch
    current_fork: https://github.com/xingh/tekt.observer
  domain:
    type: repository_local_cli_app
    public_web_domain: null
  tagline: "Agent-assisted job-search workflow with deterministic source discovery and ranked digests"
  purpose:
    - monitor direct job sources selected per track
    - filter and rank roles against user profile and track preferences
    - publish concise local digests, with optional Logseq/email/Telegram delivery
  audience:
    primary:
      - technical job seekers comfortable with CLI tooling
    secondary:
      - contributors extending source providers and workflow automation
  brand_tokens:
    colors: []
    fonts: []
    logo_reference: docs/images/digest_email.png
  content_domain:
    core_entities:
      - track
      - source
      - candidate_job
      - digest_run
      - integration_ticket
    taxonomy:
      cadence_groups: [every_run, every_3_runs, every_month]
      recommendations: [apply_now, watch, skip]
      source_statuses: [complete, partial, failed]
      integration_statuses: [pending, integration_needed, deferred, pass, blocked]
  external_service_endpoints:
    telegram:
      api_base_default: https://api.telegram.org
      operation: bot sendMessage
    email:
      smtp_provider_presets:
        gmail: smtp.gmail.com:587
        fastmail: smtp.fastmail.com:587
        hotmail_outlook: smtp-mail.outlook.com:587
        proton_business: smtp.protonmail.ch:587
    source_discovery:
      endpoint_family: official employer career pages, job-board APIs, and RSS/HTML feeds declared per source in track config
  feature_toggles:
    optional_delivery_targets: [logseq, email, telegram]
    source_quality_reviewer_mode: [auto, off, force]
    scheduler_cadence_modes: [daily, weekly, monthly]
  constellation_membership:
    role: upstream project with fork-based derivatives
    siblings: []
    mothership: https://github.com/jvdheyden/jobwatch
    cross_navigation_targets:
      - docs/architecture.md
      - shared/discovery_modes.md
```
