# Deterministic JSON handoff

A tekt.observer bundle is canonical UTF-8 JSON with sorted object keys, compact separators, and one trailing newline. Schema version 1 contains a manifest plus workspace, watcher, source, run, normalized item, feedback, digest, and provenance payloads. Every payload section has a SHA-256 hash; the content-derived bundle ID makes retries idempotent when content and revision are unchanged.

Bundles exclude user/auth records, credentials, environment values, operation logs, and claim tokens. Import validates the schema and every hash before writing, then creates a new workspace or explicit fork. Existing-workspace merging is deliberately unsupported.

An export is publishable only when the manifest revision equals the current PocketBase workspace revision. Publication uses:

```bash
./tekt.observer publish --workspace <id> --bundle <file> --remote <remote:path>
```

The implementation invokes `rclone copy --immutable`; `rclone sync` is forbidden because a handoff must not delete or overwrite remote history. Configure rclone credentials outside the repository. A local-filesystem remote is suitable for offline acceptance tests; S3-compatible systems use rclone's S3 remote without an AWS-specific SDK.

Compatibility is governed by `manifest.schema_version`. Readers must reject unknown versions and hash mismatches. Schema evolution should add an explicit reader/migrator and retain fixtures for every supported version.
