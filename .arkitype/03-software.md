# Software

```yaml
SOFTWARE:
  boundaries:
    pocketbase: operational CRUD, auth, authorization, realtime, queue state
    frontend: direct PocketBase client; document-centered workspace interactions
    python_worker: deterministic discovery, normalization, export/import, delivery, and subprocess orchestration
    agents: setup, semantic interpretation, ranking, synthesis, and source repair
  discovery:
    retained: [feed adapters, known APIs]
    repeatable_browser_extraction: Crawl4AI
    reconnaissance_and_repair: browser-use
    rule: agents do not replace deterministic routine fetching
  cli:
    executable: tekt.observer
    commands: [up, worker, import, export, publish]
  api:
    style: standard PocketBase REST and realtime
    custom_server_framework: none
  frontend_contract:
    views: [onboarding, workspace navigation, unified inbox, watcher health, source health, item provenance, digests, operations, members, import-export]
    state: PocketBase SDK plus TanStack Query
  transition:
    preserve: [existing Python workers, JSON artifacts, watcher slugs, current pipeline behavior]
    retire_after_parity: [Python http.server UI, redundant shell entrypoints]
```
