# Tracks Pipeline

tekt.observer runs one or more **tracks**. Each track is a small folder
under `tracks/<slug>/` with its config (sources, cadence, preferences) and
its own artifact history under `artifacts/*/<slug>/`.

Every track flows through some subset of the same six stages. Which
stages actually run depends on which per-track scripts (and source
registries) exist. The generic orchestrator is
[`scripts/run_pipeline.sh`](../scripts/run_pipeline.sh); it dispatches
each stage conditionally.

```
    discover / gather      →  artifacts/discovery/<track>/<date>.json
        │
        ▼
     enrich (OG meta)      →  artifacts/enrichment/<track>/urls.json
        │
        ▼
   classify / organize     →  artifacts/organized/<track>/<date>.json
        │
        ▼
        trends             →  artifacts/trends/<track>/<date>.json
        │
        ▼
    synthesize digest      →  artifacts/digests/<track>/<date>.json
        │
        ▼
       render              →  tracks/<track>/digests/<date>.md
                              site/track/<track>/<date>.html
                              site/track/<track>/feed/<date>.html
                              site/track/<track>/trends/<date>.html
```

## Stage-by-stage script map

| Stage | Generic (any track) | Track-specific |
|---|---|---|
| Discover / gather | `scripts/feed_gather.py` (RSS / Atom / HN Algolia, `--registry`) | `scripts/discover_jobs.py` (jobwatch), `scripts/ai_topics_discover.py` (local HTML fixture) |
| Enrich | `scripts/feed_enrich.py` (per-URL OpenGraph / Twitter / canonical, cached) | — |
| Classify | — | `scripts/ai_topics_classify.py`, `scripts/market_watch_classify.py` |
| Trends | `scripts/track_trends.py` (topic/source/audience counts, velocity, cross-source URLs, keyword cloud) | — |
| Synthesize digest | — | `scripts/ai_topics_synthesize_digest.py`, `scripts/market_watch_synthesize_digest.py`. jobwatch tracks write the digest via the provider LLM agent instead. |
| Render (markdown) | `scripts/render_digest.py` | — |
| Render (HTML site) | `scripts/render_html.py` (static) and `scripts/serve_html.py` (live) — shared `scripts/html_viewer.py` | — |

## Config that lives in JSON

- **Source registry** — one per feed-driven track:
  `shared/schemas/<track>_source_registry.json`
- **Taxonomy** — machine-readable form of the arkitype spec:
  `shared/schemas/<track>_taxonomy.json` (present for ai_topics + market_watch)

## Config that lives in Python

Classifier weights, watchlists, keyword sets, and audience heuristics all
change often and benefit from real Python (imports, list comprehensions,
regex). They live in the track-specific classifier module rather than
JSON:

- `scripts/ai_topics_classify.py` — `TOPIC_KEYWORDS`, `AUDIENCE_KEYWORDS`, `CONTENT_TYPE_HINTS`
- `scripts/market_watch_classify.py` — `DEFAULT_WATCHLIST`, keyword → event_type map

## How each track uses the pipeline today

### jobwatch-style tracks (e.g. `test_workflow`)

- **Discover:** `scripts/discover_jobs.py` (60+ registered discovery modes for career pages / job APIs)
- **Enrich:** optional; `scripts/feed_enrich.py --track test_workflow` would work today
- **Classify:** the provider LLM agent writes the digest directly (no separate classify)
- **Trends:** would require adding an organized artifact first
- **Synthesize:** the provider LLM agent (via `run_track.sh`)
- **Render:** the shared markdown + HTML renderers

### ai_topics

- **Discover:** `scripts/ai_topics_discover.py` (local HTML fixture) or `scripts/feed_gather.py` (RSS from `shared/schemas/ai_topics_source_registry.json`)
- **Enrich:** `scripts/feed_enrich.py`
- **Classify:** `scripts/ai_topics_classify.py` — topic keyword matching against `shared/schemas/ai_topics_taxonomy.json`
- **Trends:** `scripts/track_trends.py`
- **Synthesize:** `scripts/ai_topics_synthesize_digest.py` — picks top matches by audience overlap
- **Render:** shared

### market_watch

- **Discover:** `scripts/feed_gather.py` with `shared/schemas/market_watch_source_registry.json` (Fed press, SEC press, BoE, Yahoo Finance, HN Algolia earnings + funding)
- **Enrich:** `scripts/feed_enrich.py`
- **Classify:** `scripts/market_watch_classify.py` — asset-class + event-type keywords, watchlist matching for portfolio alerts
- **Trends:** `scripts/track_trends.py`
- **Synthesize:** `scripts/market_watch_synthesize_digest.py` — `is_portfolio_alert` → `top_matches`
- **Render:** shared

## Running the pipeline

```bash
# fixture mode (no network)
bash scripts/run_pipeline.sh --track ai_topics
bash scripts/run_pipeline.sh --track market_watch

# live mode (uses the track's source registry)
bash scripts/run_pipeline.sh --track ai_topics --live
bash scripts/run_pipeline.sh --track market_watch --live

# view the result
./.venv/bin/python scripts/serve_html.py --root tests/tmp/ai_topics
./.venv/bin/python scripts/render_html.py --root tests/tmp/ai_topics --out site/
```

The pipeline writes into a scratch `JOB_AGENT_ROOT` (default
`tests/tmp/<track>`) so the tracked working tree stays clean, mirroring
`scripts/test_track_workflow.sh`.

The two per-track wrappers `run_ai_topics_e2e.sh` and
`run_market_watch_e2e.sh` remain as thin back-compat shims that just
invoke `run_pipeline.sh --track <slug>`.

## Adding a new track

1. Author `.arkitype/00-<name>.md` — the SITE_PROFILE-style purpose spec
   (taxonomy, audiences, iteration plan). Follow
   `.arkitype/00-topic-tracker.md` or `.arkitype/00-market-watch.md`.
2. Scaffold `tracks/<name>/` (AGENTS.md, prefs.md, sources.json,
   source_state.json). Mirror `tracks/ai_topics/` shape.
3. Encode the taxonomy as
   `shared/schemas/<name>_taxonomy.json` if the classifier will read it.
4. If feed-driven, author
   `shared/schemas/<name>_source_registry.json`.
5. Write `scripts/<name>_classify.py` and
   `scripts/<name>_synthesize_digest.py`. The generic runner picks them
   up automatically.
6. If a persona applies, add `profile/personas/<name>.md` and reference
   it from the track's `AGENTS.md`.
7. `bash scripts/run_pipeline.sh --track <name> --live`.
8. `./.venv/bin/python scripts/render_html.py --root tests/tmp/<name> --out site/`.

## Where artifacts live

```
artifacts/
    discovery/<track>/<date>.json     -- gather / discover output
    discovery/<track>/latest.json     -- symlink-like copy of the most recent
    enrichment/<track>/urls.json      -- per-URL OG cache
    organized/<track>/<date>.json     -- classifier output
    trends/<track>/<date>.json        -- trend aggregation
    digests/<track>/<date>.json       -- structured digest (source of truth for the digest)
    digests/<track>/latest.json       -- latest copy
tracks/<track>/digests/<date>.md      -- rendered markdown digest
site/                                 -- rendered HTML site (from render_html.py)
```

The HTML viewer reads all of these and renders a single consolidated
report at `site/track/<track>/<date>.html`. See
[`../scripts/html_viewer.py`](../scripts/html_viewer.py) for the page
structure.
