# Infrastructure

```yaml
INFRASTRUCTURE:
  pocketbase:
    version: 0.39.11
    executable: unmodified upstream binary
    migrations: pocketbase/pb_migrations
    data_volume: persistent
    topology: single-writer, vertically scaled
  frontend:
    stack: [React, TypeScript, Vite, Tailwind, shadcn/ui, PocketBase JavaScript SDK, TanStack Query]
    deployment: static assets served beside PocketBase
  worker:
    runtime: Python 3.10+
    responsibilities: [claim operations, run observation pipelines, write JSON artifacts, update PocketBase progress]
    retained_tools: [Crawl4AI, browser-use, Codex CLI, Claude CLI]
  immutable_json_store:
    root_default: state/
    write_durability: fsync every new event before acknowledgement
    compaction: immutable deterministic snapshot after event-count or elapsed-time threshold
    recovery: validate filename hashes and the event hash chain, then replay after latest snapshot
  local:
    bind: loopback
    launcher: tekt.observer up
    implicit_workspace: local
  hosted:
    requirements: [TLS reverse proxy, PocketBase authentication, persistent PocketBase and artifact volumes, backups]
  transport:
    command: rclone copy --immutable
    supported_destinations: [local filesystem remote, S3-compatible remote, configured rclone remote]
    forbidden: [rclone sync, embedded cloud credentials, AWS-specific SDK]
  environment:
    - TEKT_OBSERVER_POCKETBASE_URL
    - TEKT_OBSERVER_TOKEN
    - TEKT_OBSERVER_PORT
    - TEKT_OBSERVER_STORE
    - TEKT_OBSERVER_COMPACT_EVERY
    - TEKT_OBSERVER_COMPACT_SECONDS
  commands:
    - tekt.observer up
    - tekt.observer worker
    - tekt.observer import <bundle>
    - tekt.observer export --workspace <id>
    - tekt.observer publish --workspace <id> --bundle <bundle> --remote <remote:path>
    - tekt.observer store <put|delete|show|compact>
  compatibility:
    legacy_shell_entrypoints: retained until equivalent PocketBase workflows pass
    legacy_environment_names: temporary shims only
```
