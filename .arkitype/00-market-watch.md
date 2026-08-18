# Market Watch — Arkitype Overview

`market_watch` is the built-in watcher for AI-related public companies, semiconductor and cloud exposure, earnings and capital expenditure, and AI regulation or policy.

Its canonical executable specification lives in [`watchers/market_watch/`](./watchers/market_watch/): `watcher.json`, `taxonomy.json`, `sources.json`, `brief.md`, and `samples.json`.

Run `./.venv/bin/python scripts/generate_watchers.py` after editing the spec. Runtime files under `tracks/market_watch/` and `shared/schemas/market_watch_*` are generated and checked by `scripts/test.sh`.
