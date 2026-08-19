# Identity & Site Profile

## I9–I14 product identity

tekt.observer is a local-first single-user portfolio of observation tracks. Portfolios are named ordered collections of tracks and global reusable interests; topics and audiences belong to tracks. The product centers on a unified scored signal inbox, then curation, configuration, guided setup, and operational controls. Local files remain canonical. Databases, accounts, hosted tenancy, remote writes, and client frameworks are out of scope. Legacy tracks must work without migration and static output remains read-only.

```yaml
SITE_PROFILE:
  site_name: tekt.observer
  canonical_repository:
    primary: https://github.com/jvdheyden/jobwatch
    current_fork: https://github.com/xingh/tekt.observer
  domain:
    type: repository_local_cli_app
    public_web_domain: tekt.md
  tagline: "Agent-assisted {job,opportunity,industry}-search workflow with deterministic source discovery and ranked digests"
  purpose:    
    - monitor direct {job,opportunity,industry} sources selected per track
    - filter and rank {roles,opportunities,interests] against user profile and track preferences
    - automate data collection through web page browsing,
    - process that discovers a path, and then builds a repeatable path to the data/knowledge with code
    - one approach discovers and then generates code, another browses and creates scripts that get translated into code
    - publish concise local digests, and optional delivery to email/Telegram and sae to Logseq format
  audience:
    primary:
      - knowledge managers who have to watch and analyze knowledge from various places for their job 
      - investors who want to know what's happening across their portfolio from their various subscriptions
      - researchers, writers, professionals who want to look for non profit foundation or government grants 
      - ai leaders, managers, and architects who want a predictable way to run long running knowledge processes
    secondary:
      - technical job seekers comfortable with CLI tooling
      - contributors extending source providers and workflow automation
  brand_tokens:
    colors: []
    fonts: []
    logo_reference: .knowledge/images/digest_email.png
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
      - .knowledge/architecture.md
      - shared/discovery_modes.md
```
