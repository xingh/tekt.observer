# Career Watch — Arkitype Overview

`career_watch` is the built-in watcher for opportunities and career intelligence across engineering, product, architecture, governance, automation, education, developer relations, and customer-facing work.

Its canonical executable specification lives in [`watchers/career_watch/`](./watchers/career_watch/): `watcher.json`, `taxonomy.json`, `sources.json`, `brief.md`, and `samples.json`.

Run `./.venv/bin/python scripts/generate_watchers.py` after editing the spec. Runtime files under `tracks/career_watch/` and `shared/schemas/career_watch_*` are generated and checked by `scripts/test.sh`.
