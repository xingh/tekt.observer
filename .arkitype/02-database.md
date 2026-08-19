# Data and Content

PocketBase is the operational database and REST/realtime/authORIZATION boundary. Every domain record carries a `workspace` relation. Existing JSON discovery and digest artifacts remain durable pipeline outputs and are imported without changing canonical watcher IDs.

```yaml
DATABASE:
  engine: PocketBase 0.39.11
  migrations: committed and reproducible
  collections:
    users: auth identities; local mode creates an implicit owner
    workspaces: name, slug, monotonically increasing revision, definition JSON
    memberships: workspace + user + role; unique per pair
    watchers: workspace + immutable slug + structured definition
    sources: watcher source registry, configuration, and health
    runs: lifecycle, summary, and provenance
    items: normalized content, score, ranking detail, and provenance
    feedback: user curation and agent context
    operations: queued worker commands, claims, retries, cancellation, progress, and result
    exports: bundle revision, hashes, status, and publication destination
  roles:
    owner: [members, configuration, operations, imports, exports, read, curation]
    editor: [watchers, sources, runs, curation, read]
    viewer: [read, export]
    worker: trusted service credential; operation claim and result writes only
  isolation: API rules deny anonymous hosted access and cross-workspace access
  revisions: every portable workspace mutation increments workspaces.revision
  exchange_bundle:
    schema_version: 1
    encoding: canonical UTF-8 JSON with sorted keys and one trailing newline
    identity: content-derived bundle ID
    contents: [manifest, workspace, watchers, sources, runs, items, feedback, digests, provenance]
    excluded: [credentials, auth records, environment values, operation logs, claim tokens]
    import: validates schema and hashes, then creates a workspace or explicit fork
    publish_guard: manifest workspace revision must equal current workspace revision
    merge: out of scope
```
