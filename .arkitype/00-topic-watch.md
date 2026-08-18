# Topic Watch — Arkitype Overview

`topic_watch` is the built-in watcher for AI topics in business use: enterprise adoption, workflow productivity, customer operations, governance, and measurable value.

Its canonical executable specification lives in [`watchers/topic_watch/`](./watchers/topic_watch/):

- `watcher.json` — identity and default audience
- `taxonomy.json` — topics and audiences
- `sources.json` — keyless starter sources
- `brief.md` — generated track preferences
- `samples.json` — offline starter signals

Run `./.venv/bin/python scripts/generate_watchers.py` after editing the spec. Runtime files under `tracks/topic_watch/` and `shared/schemas/topic_watch_*` are generated and checked by `scripts/test.sh`.
