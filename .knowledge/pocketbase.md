# PocketBase operations and collaboration

tekt.observer pins PocketBase `0.39.11` in `pocketbase/VERSION`. It is the operational projection and API/auth layer; immutable JSON events and snapshots are the durable record. Committed JavaScript migrations under `pocketbase/pb_migrations/` are the projection schema source of truth. Do not customize the Go binary or add PocketBase JavaScript hooks; the frontend and Python workers use the standard REST/realtime APIs.

Local mode binds PocketBase to loopback and creates a `local` workspace with the three canonical watcher slugs. Hosted mode uses the same collections and frontend behind TLS. It is a single-writer deployment: scale vertically, keep `pb_data` on a persistent volume, and run one coordinated writer/worker group.

Roles are workspace scoped. Owners manage members, configuration, operations, imports, and exports. Editors manage watcher/source/run and curation records. Viewers read and request exports. A worker uses a dedicated trusted service credential; it must never be embedded in a bundle or frontend build. PocketBase API rules are the enforcement boundary, not hidden UI controls.

## Startup

`./tekt.observer up` launches the local compose topology. Set `TEKT_OBSERVER_POCKETBASE_URL` and `TEKT_OBSERVER_TOKEN` for CLI/worker access. Hosted deployments must change the loopback port policy intentionally, add a TLS reverse proxy, and keep credentials outside the repository.

## Upgrade and restore

PocketBase is pre-1.0. To upgrade: read every intervening upstream migration note, stage a copy of `pb_data`, update the exact pin, run committed migrations, and execute authorization plus import/export regression tests before production. Never upgrade a sole production volume in place.

Back up both PocketBase `pb_data` and structured artifact storage from a quiesced snapshot. A restore uses the matching PocketBase version, restores both volumes, starts PocketBase with migrations enabled, verifies workspace revisions and collection counts, then performs an export/hash validation smoke test. Exchange bundles are portability artifacts, not complete operational backups because they intentionally exclude users, credentials, and transient operations.

The current compose file is a local/reference package. Production operators must verify the selected image or upstream binary checksum and test restore procedures on their own storage platform.
