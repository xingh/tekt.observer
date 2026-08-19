# Identity & Site Profile

tekt.observer is a collaborative observation workspace. It turns repeatable source collection, agent-assisted interpretation, and human feedback into a calm unified signal inbox. PocketBase is the operational authority; versioned deterministic JSON bundles are the permanent portability and agent-handoff contract.

```yaml
SITE_PROFILE:
  site_name: tekt.observer
  product_name_rule: "Use tekt.observer; tekt is reserved for a separate product."
  domain:
    type: local_and_hosted_workspace_application
    handoff_destination_example: "tekt.space:"
  purpose:
    - observe official and selected sources through reusable watcher definitions
    - rank, curate, and synthesize signals with deterministic pipelines and bounded agent work
    - collaborate inside a hosted workspace with owner, editor, and viewer roles
    - exchange immutable, verifiable JSON bundles between people and agents
  canonical_watchers: [topic_watch, job_watch, market_watch]
  core_entities: [workspace, membership, watcher, source, run, item, feedback, operation, export]
  authority:
    operational: PocketBase
    portable: versioned JSON exchange bundles
    artifacts: structured discovery and digest JSON
  modes:
    local: implicit owner, loopback services, same schema and frontend as hosted
    hosted: authenticated collaboration, single-writer PocketBase deployment
  non_goals:
    - bidirectional cross-instance synchronization
    - custom PocketBase Go extensions or JavaScript hooks
    - FastAPI
    - local model hosting without a selected inference provider
```
