# Immutable JSON storage

tekt.observer acknowledges durable writes only after creating and fsyncing a new canonical JSON event file and its containing directory. Files are named `<20-digit-sequence>-<sha256>.json`; every event also records the previous event's hash. Existing event files are never opened for writing.

The event operations are deliberately small: `put` replaces one record in one collection, and `delete` removes it from the materialized state. The journal is deterministically replayable. PocketBase is a queryable operational projection and API/auth boundary, not the sole durable representation.

Compaction creates a new immutable full-state snapshot. By default this happens after 100 events or when an uncompacted event remains for 300 seconds and the store is next serviced. Each append services the compaction policy; long-running workers should also call the due check on their normal polling cadence. `CURRENT.json` is atomically replaced as a cache pointer. Recovery does not trust or require it: the reader verifies immutable filename hashes, validates the event chain, loads the highest valid snapshot, and replays later events.

Compaction does not delete journal segments or earlier snapshots. Retention/pruning must be a separately designed archival operation with an externally verified backup; it is not automatic.

Multi-record pipeline ingestion uses `append_many` to hold the writer lock and scan the existing chain once. Every change still receives its own sequence, previous-event hash, immutable JSON file, file fsync, and directory fsync. This removes repeated directory scans without weakening event-level durability.

Configuration:

- `TEKT_OBSERVER_STORE` — root directory, default `state/`
- `TEKT_OBSERVER_COMPACT_EVERY` — events between snapshots, default `100`
- `TEKT_OBSERVER_COMPACT_SECONDS` — maximum snapshot interval, default `300`

```bash
./tekt.observer store put items item-1 '{"title":"Example","status":"new"}'
./tekt.observer store delete items item-1
./tekt.observer store show
./tekt.observer store compact --force
```

For large records, prefix a JSON file path with `@` instead of placing JSON on the command line. Store roots, exports, credentials, and other runtime state are gitignored.
