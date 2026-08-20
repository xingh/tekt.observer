# Software

```yaml
SOFTWARE:
  boundaries:
    immutable_json_store: durable write-ahead events, validation, replay, and snapshot compaction
    pocketbase: materialized operational CRUD projection, auth, authorization, realtime, queue state
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
    commands: [up, worker, import, export, publish, store]
  api:
    style: standard PocketBase REST and realtime
    custom_server_framework: none
  frontend_contract:
    views: [onboarding, workspace navigation, unified inbox, watcher health, source health, item provenance, digests, operations, members, import-export]
    state: PocketBase SDK plus TanStack Query
    relevance: top-quartile default with user-controlled score bounds and an explicit audit path for hidden items
  watcher_context:
    shared_career_context_consumers: [career_watch]
    planned_shared_context_consumers: [network_watch]
    scoring: versioned per-watcher rubrics with evidence, concerns, dimensions, and visibility decisions
  transition:
    preserve: [existing Python workers, JSON artifacts, watcher slugs, current pipeline behavior]
    retire_after_parity: [Python http.server UI, redundant shell entrypoints]
```
