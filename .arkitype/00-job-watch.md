# Job Watch — Arkitype Overview

`job_watch` is the built-in watcher for AI-enabled professions across engineering, product, architecture, governance, automation, education, developer relations, and customer-facing work.

Its canonical executable specification lives in [`watchers/job_watch/`](./watchers/job_watch/): `watcher.json`, `taxonomy.json`, `sources.json`, `brief.md`, and `samples.json`.

Run `./.venv/bin/python scripts/generate_watchers.py` after editing the spec. Runtime files under `tracks/job_watch/` and `shared/schemas/job_watch_*` are generated and checked by `scripts/test.sh`.
