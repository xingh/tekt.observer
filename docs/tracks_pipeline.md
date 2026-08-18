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
| Discover / gather | `scripts/feed_gather.py` (RSS / Atom / HN Algolia, `--registry`) | `scripts/discover_jobs.py` (jobwatch), `scripts/topic_watch_discover.py` (local HTML fixture) |
| Enrich | `scripts/feed_enrich.py` (per-URL OpenGraph / Twitter / canonical, cached) | — |
| Classify | — | `scripts/topic_watch_classify.py`, `scripts/market_watch_classify.py`, `scripts/job_watch_classify.py` |
| Trends | `scripts/track_trends.py` (topic/source/audience counts, velocity, cross-source URLs, keyword cloud) | — |
| Rerank per audience (I6) | `scripts/track_rerank.py` (reads `<track>_taxonomy.json` audiences; supports `--with-feedback` from I8) | — |
| Synthesize digest — persona | — | `scripts/topic_watch_synthesize_digest.py`, `scripts/market_watch_synthesize_digest.py`, `scripts/job_watch_synthesize_digest.py`. jobwatch's own `test_workflow` track uses the provider LLM agent instead. |
| Synthesize digest — per audience (I7) | `scripts/synthesize_audience_digests.py` (one digest JSON + markdown per audience declared in `<track>_taxonomy.json`) | — |
| Render (markdown) | `scripts/render_digest.py` | — |
| Render (HTML site) | `scripts/render_html.py` (static) and `scripts/serve_html.py` (live) — shared `scripts/html_viewer.py` | — |
| Feedback (I8) | `scripts/track_feedback.py` (event append + rerank boosts). `serve_html.py` exposes `POST /feedback`; feed cards show save/hide/click buttons. `track_rerank.py --with-feedback` applies boosts on the next run. | — |

## Config that lives in JSON

- **Source registry** — one per feed-driven track:
  `shared/schemas/<track>_source_registry.json`
- **Taxonomy** — machine-readable form of the arkitype spec:
  `shared/schemas/<track>_taxonomy.json` (present for all three shipped tracks).
  Declaring `audiences` here is what turns on per-audience rerank (I6),
  per-audience digests (I7), and the feedback loop (I8) — those three stages are
  track-generic and need no per-track code.

## Config that lives in Python

Classifier weights, watchlists, keyword sets, and audience heuristics all
change often and benefit from real Python (imports, list comprehensions,
regex). They live in the track-specific classifier module rather than
JSON:

- `scripts/topic_watch_classify.py` — `TOPIC_KEYWORDS`, `AUDIENCE_KEYWORDS`, `CONTENT_TYPE_HINTS`
- `scripts/market_watch_classify.py` — `DEFAULT_WATCHLIST`, keyword → event_type map

## How each track uses the pipeline today

### jobwatch-style tracks (e.g. `test_workflow`)

- **Discover:** `scripts/discover_jobs.py` (60 registered discovery modes for career pages / job APIs — see [`../shared/discovery_modes.md`](../shared/discovery_modes.md))
- **Enrich:** optional; `scripts/feed_enrich.py --track test_workflow` would work today
- **Classify:** the provider LLM agent writes the digest directly (no separate classify)
- **Trends:** would require adding an organized artifact first
- **Synthesize:** the provider LLM agent (via `run_track.sh`)
- **Render:** the shared markdown + HTML renderers

### topic_watch

- **Discover:** `scripts/topic_watch_discover.py` (local HTML fixture) or `scripts/feed_gather.py` (RSS from `shared/schemas/topic_watch_source_registry.json`)
- **Enrich:** `scripts/feed_enrich.py`
- **Classify:** `scripts/topic_watch_classify.py` — topic keyword matching against `shared/schemas/topic_watch_taxonomy.json`
- **Trends:** `scripts/track_trends.py`
- **Synthesize:** `scripts/topic_watch_synthesize_digest.py` — picks top matches by audience overlap
- **Render:** shared

### market_watch

- **Discover:** `scripts/feed_gather.py` with `shared/schemas/market_watch_source_registry.json` (16 sources spanning market news, central banks, the SEC, the US Federal Register, and focused HN queries including AI public companies and regulation)
- **Enrich:** `scripts/feed_enrich.py`
- **Classify:** `scripts/market_watch_classify.py` — asset-class + event-type keywords, watchlist matching for portfolio alerts
- **Trends:** `scripts/track_trends.py`
- **Synthesize:** `scripts/market_watch_synthesize_digest.py` — `is_portfolio_alert` → `top_matches`
- **Render:** shared

### job_watch

- **Discover:** `scripts/feed_gather.py` with `shared/schemas/job_watch_source_registry.json` (13 sources: HN Jobs, ai-jobs.net, We Work Remotely, and focused queries for engineering, product/design, architecture, governance, automation, education, DevRel, and customer-facing AI roles). The ATS adapters under `scripts/discover/sources/` remain available for private employer-specific tracks.
- **Enrich:** `scripts/feed_enrich.py`
- **Classify:** `scripts/job_watch_classify.py` — role_type + seniority audience + remote-friendliness from keyword sets
- **Trends:** `scripts/track_trends.py`
- **Synthesize:** `scripts/job_watch_synthesize_digest.py`, plus the generic per-audience digests
- **Render:** shared

### Where each track stands

Which iteration (`I0`–`I8`) each track has actually reached, plus the known
gaps, is tracked in [`capabilities.md`](./capabilities.md#iteration-status).
The original iteration plans are summarized by the `.arkitype/00-*-watch.md`
overviews; executable watcher definitions live under `.arkitype/watchers/`.

## Running the pipeline

```bash
# fixture mode (no network)
bash scripts/run_pipeline.sh --track topic_watch
bash scripts/run_pipeline.sh --track market_watch

# live mode (uses the track's source registry)
bash scripts/run_pipeline.sh --track topic_watch --live
bash scripts/run_pipeline.sh --track market_watch --live

# view the result
./.venv/bin/python scripts/serve_html.py --root tests/tmp/topic_watch
./.venv/bin/python scripts/render_html.py --root tests/tmp/topic_watch --out site/
```

The pipeline writes into a scratch `JOB_AGENT_ROOT` (default
`tests/tmp/<track>`) so the tracked working tree stays clean, mirroring
`scripts/test_track_workflow.sh`.

The two per-track wrappers `run_topic_watch_e2e.sh` and
`run_market_watch_e2e.sh` remain as thin back-compat shims that just
invoke `run_pipeline.sh --track <slug>`.

## Backfill mode

`run_pipeline.sh` covers "today". `scripts/backfill.sh` covers "the past
N days", one date at a time, with real per-date data where the source
supports it. Use it for demos, month-in-review reports, or seeding a
fresh scratch tree with history before daily runs start.

```bash
# One track, one date range (inclusive UTC dates — use past-or-present dates only;
# future dates will fetch nothing and produce empty artifacts).
bash scripts/backfill.sh --track topic_watch --start 2026-08-01 --end 2026-08-13

# Explicit list (useful for batching across parallel runs)
bash scripts/backfill.sh --track topic_watch --dates '2026-08-10 2026-08-11 2026-08-12 2026-08-13'

# All three tracks in parallel for the last four UTC days
DATES=$(for i in $(seq 3 -1 0); do date -u -d "$i days ago" +%F; done)
bash scripts/backfill.sh --track topic_watch    --dates "$DATES" &
bash scripts/backfill.sh --track market_watch --dates "$DATES" &
bash scripts/backfill.sh --track job_watch    --dates "$DATES" &
wait
```

### How real historical fetch works per source kind

`scripts/feed_gather.py` takes an optional `--for-date YYYY-MM-DD`. When
set, it applies a UTC day window:

| Source kind | Historical behavior |
|---|---|
| `hn_algolia` | Server-side filter via `numericFilters=created_at_i>=…,created_at_i<=…` — real per-date results for the whole HN history. |
| `rss` / `atom` | Client-side filter on the parsed `pubDate` / `published` field — only entries whose timestamp falls in the target UTC day are kept. Feeds that only expose their latest window (Substacks, arXiv, most newswires) will return 0 for older dates. |
| Anything else | Fetched as-is (no window applied). |

Consequence: an older date's discovery artifact will look thinner than
today's because most non-HN feeds don't carry archived entries in the
feed body itself. For deeper historical coverage of a specific source,
add a per-source archive-page scraper (e.g. Simon Willison's date-indexed
archive, arXiv's `list/cs.LG/YYMM`, Substack `/archive?year=…`) as its
own new source kind.

### What backfill.sh runs per date

For every date in the range it runs the deterministic pipeline stages
against the historical discovery artifact:

1. `feed_gather.py --for-date <date>` — real per-day window per source
2. `feed_enrich.py` — shared URL cache across all dates
3. `<track>_classify.py` — same classifier as daily runs
4. `track_trends.py` — velocity vs. the previous date if present
5. `track_rerank.py --with-feedback` — feedback boosts apply here too
6. `synthesize_audience_digests.py` — per-audience digests (I7)
7. `<track>_synthesize_digest.py` — persona digest
8. `render_digest.py` — markdown

The scratch tree at `tests/tmp/<track>/` accumulates all dates side by
side. Re-running `backfill.sh` for a date that already has artifacts
overwrites them cleanly.

### Rendering a multi-track, per-day-folder site

Once the scratch trees have several dates each, render into a single
publishable folder with one directory per day per track:

```bash
./.venv/bin/python scripts/render_multitrack_site.py \
  --track topic_watch --track market_watch --track job_watch \
  --out /path/to/output/
```

Layout produced:

```
<out>/
    index.html                             — one card per track, 31 date chips per card
    style.css
    <track>/index.html                     — track landing: date table with feed/trends/digest links
    <track>/sources.html                   — sources + persona
    <track>/<date>/index.html              — daily report (consolidated)
    <track>/<date>/details.html            — structured digest tables
    <track>/<date>/feed.html               — social feed grid with OG images
    <track>/<date>/trends.html             — trend charts + keyword cloud
    <track>/<date>/audience/<audience>.html — per-audience report variant
    raw/<kind>/<track>/<date>.json         — raw JSON behind every page
```

`render_multitrack_site.py` reuses the shared `html_viewer` renderers
and only rewrites the root-anchored URLs (`/track/…`, `/style.css`,
`/raw/…`) to relative paths so the output works via `file://` or from
any subdirectory of an HTTP server.

## Adding a new track

1. Copy one `.arkitype/watchers/<slug>/` directory and give it a new file-safe slug.
2. Edit its `watcher.json`, `brief.md`, `taxonomy.json`, `sources.json`, and `samples.json`. IDs referenced by sources and samples must exist in the taxonomy.
3. Run `./.venv/bin/python scripts/generate_watchers.py`. Do not hand-edit the generated `tracks/<slug>/{track.json,prefs.md}` or `shared/schemas/<slug>_*` files.
4. Add `scripts/<slug>_classify.py` and `scripts/<slug>_synthesize_digest.py` when the watcher needs type-specific organization or digest logic. The generic runner discovers these by filename; feed gathering, trends, audience reranking, and rendering are shared.
5. Run `./.venv/bin/python scripts/generate_watchers.py --check` and `bash scripts/run_pipeline.sh --track <slug> --live`. The check also reports stamped generated files left behind by a renamed or removed watcher; review and remove those explicitly.
6. Render with `./.venv/bin/python scripts/render_html.py --root tests/tmp/<slug> --out site/`.

## Where artifacts live

```
artifacts/
    discovery/<track>/<date>.json                     -- gather / discover output
    discovery/<track>/latest.json                     -- latest copy
    enrichment/<track>/urls.json                      -- per-URL OG cache
    organized/<track>/<date>.json                     -- classifier output
    trends/<track>/<date>.json                        -- trend aggregation
    ranked_audience/<track>/<audience>/<date>.json    -- I6 per-audience rerank
    digests/<track>/<date>.json                       -- persona digest (source of truth)
    digests/<track>/<audience>/<date>.json            -- I7 per-audience digest
    digests/<track>/latest.json                       -- latest persona digest copy
    feedback/<track>/<audience>/events.jsonl          -- I8 append-only feedback log
tracks/<track>/digests/<date>.md                      -- rendered markdown persona digest
tracks/<track>/digests/<audience>/<date>.md           -- I7 per-audience markdown
site/                                                 -- rendered HTML site (render_html.py)
```

The HTML viewer reads all of these and renders a single consolidated
report at `site/track/<track>/<date>.html`, plus per-audience variants
at `site/track/<track>/<date>/audience/<aud>.html`. See
[`../scripts/html_viewer.py`](../scripts/html_viewer.py) for the page
structure.

## Feedback loop (I8)

Feed cards in the report and feed pages carry `save` / `hide` / `click`
buttons. On the live server (`scripts/serve_html.py`), each click posts a
one-line JSON event to `artifacts/feedback/<track>/<audience>/events.jsonl`.

On the next pipeline run, `track_rerank.py --with-feedback` reads those
events and applies per-item boosts (`save +0.20`, `click +0.05`,
`note +0.10`, `hide −0.35`) to the audience_score. The most recent event
per item wins when it is a stronger signal.

CLI equivalents for scripted use:

```bash
./.venv/bin/python scripts/track_feedback.py --root tests/tmp/topic_watch \
  append --track topic_watch --audience builders --item-key ai-abc123... --action save

./.venv/bin/python scripts/track_feedback.py --root tests/tmp/topic_watch \
  summary --track topic_watch --audience builders
```

On a static site opened via `file://`, the buttons render but each click
gracefully turns into a "live only" state — no server to accept the POST.
