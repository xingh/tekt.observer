# What tekt.observer Can Do Today

_Point-in-time status of `master` as of 2026-08-11. This page is the fact source
for [`presentation-kit.md`](./presentation-kit.md) — update it when an iteration
lands and the deck outline stays valid._

tekt.observer turns a question you care about — *what's happening in AI?*, *what
moved my portfolio?*, *who is hiring for AI-enabled engineering?* — into a daily
briefing you actually read. It watches sources directly instead of waiting for an
aggregator, classifies what it finds against a taxonomy you declare, ranks it for
the specific audience you're speaking to, and renders a digest you can open in a
browser, email to yourself, or push to Telegram.

Three example tracks ship in the repo. All three run end to end **with no API
keys and no LLM calls** — the whole pipeline is deterministic Python. Agents are
used where judgment genuinely helps (setting up a track, integrating a stubborn
source), not in the daily loop.

## The one-minute version

```bash
bash scripts/bootstrap_venv.sh --no-chromium          # ~30s, once
bash scripts/run_pipeline.sh --track ai_topics --live # fetch → classify → rank → digest
./.venv/bin/python scripts/serve_html.py --root tests/tmp/ai_topics
# open http://127.0.0.1:8765/
```

That is a real run against real sources: 7 live feeds, OpenGraph enrichment,
topic classification, trend aggregation, a rerank for each of 5 audiences, and a
per-audience digest — rendered as a browsable report with save/hide/click buttons
that make the *next* run smarter.

## Capability matrix

| Capability | What it does today | Where it lives |
|---|---|---|
| **Direct source watching** | 60 discovery-mode adapters for career pages and job APIs (Greenhouse, Ashby, Lever, Personio, BambooHR, Jobvite, Eightfold, HiBob, Workday-style portals, and company-specific parsers), plus a keyless feed reader for RSS / Atom / Hacker News Algolia | `scripts/discover/sources/`, `scripts/feed_gather.py`, catalog in [`shared/discovery_modes.md`](../shared/discovery_modes.md) |
| **Link enrichment** | Per-URL OpenGraph / Twitter-card / canonical metadata, cached across runs so re-runs are cheap | `scripts/feed_enrich.py` |
| **Taxonomy classification** | Deterministic keyword/regex classification into topic, content type, audiences, and per-track extras (asset class + event type + watchlist matches for markets; role type + seniority + remote-friendliness for jobs) | `scripts/<track>_classify.py`, `shared/schemas/<track>_taxonomy.json` |
| **Trends** | Items per topic / source / content type / audience, day-over-day topic velocity, cross-source URL detection (the same story from multiple outlets), top-25 keyword cloud | `scripts/track_trends.py` |
| **Per-audience reranking** | Every item is scored for every audience declared in the track taxonomy — one pass, five ranked views | `scripts/track_rerank.py` |
| **Digests** | A persona digest plus one digest per audience, as JSON and rendered Markdown | `scripts/synthesize_audience_digests.py`, `scripts/<track>_synthesize_digest.py`, `scripts/render_digest.py` |
| **Browsable output** | Live server or publishable static site: track index, consolidated daily report, social-style feed grid with OG images, trend charts + keyword cloud, structured digest tables, sources + persona page, raw JSON | `scripts/serve_html.py`, `scripts/render_html.py`, `scripts/html_viewer.py` |
| **Feedback loop** | save / hide / click buttons on every card append events to an append-only log; the next run applies per-item boosts (`save +0.20`, `note +0.10`, `click +0.05`, `hide −0.35`) to the audience score | `scripts/track_feedback.py`, `POST /feedback` in `scripts/serve_html.py` |
| **Delivery** | Email (SMTP, with Gmail / Fastmail / Outlook / Proton presets), Telegram (auto-split for long digests), Logseq graph sync — all opt-in per run | `scripts/send_digest_email.py`, `send_digest_telegram.py`, `sync_to_logseq.sh` |
| **Scheduling** | Daily / weekly / monthly per track, installed as a cron dispatcher on Linux or a LaunchAgent on macOS | `scripts/configure_schedule.py`, `scripts/install_scheduler.sh` |
| **Agent-assisted setup** | A guided setup agent creates a track, discovers and probes candidate sources, validates them with canaries, and runs the first digest | `set-up` skill, `scripts/start_setup_agent.sh` |
| **Self-healing sources** | When a source returns noisy or empty results, an eval (deterministic validator + LLM reviewer) emits an `integration_ticket` and dispatches a coding agent to fix the adapter, then re-discovers and re-evaluates — looping until pass, blocked, or retry limit | `scripts/source_integration.py`, `scripts/eval_source_quality.py` |
| **Provider portability** | Claude Code, Codex CLI, or Gemini CLI as the agent backend, selected at setup | `scripts/agent_provider.py`, `.env.local` |

## The six stages

Every track flows through the same pipeline; stages activate based on which
per-track scripts and registries exist. Full detail in
[`tracks_pipeline.md`](./tracks_pipeline.md).

```
explore ──▶ seek ──▶ gather ──▶ organize ──▶ understand ──▶ generate
  find      build     run the    classify     rank for       digest +
 sources    the       fetch      against      the audience   report +
            fetcher              a taxonomy                  delivery
```

Mapped onto the code: `discover/gather` → `enrich` → `classify` → `trends` →
`rerank` → `synthesize` → `render`, orchestrated by
[`scripts/run_pipeline.sh`](../scripts/run_pipeline.sh).

## The three shipped tracks

| Track | Question it answers | Live sources | Audiences |
|---|---|---|---|
| **`ai_topics`** | What's worth reading in AI today? | 7 (5 RSS, 1 Atom, 1 HN Algolia — arXiv cs.LG/cs.CL, Latent Space, Sebastian Raschka, Hacker News) | builders · operators · managers · architects · leaders |
| **`market_watch`** | What moved, and does it touch my watchlist? | 13 (Fed press, SEC press, Bank of England, ECB, CNBC, Yahoo Finance, Ars Technica business, 6 HN Algolia queries for earnings / funding / IPO / rate hikes / acquisitions / central banks) | investors · portfolio_managers · allocators · gps · lps |
| **`job_watch`** | Who is hiring for AI-enabled engineering? | 8 (HN Jobs firehose, 5 HN Algolia role queries, ai-jobs.net, We Work Remotely) | individual_contributor · senior_ic · tech_lead · manager · instructor |

Each track is declared twice: once as a human-readable purpose spec in
`.arkitype/00-<name>.md` (taxonomy, audiences, iteration plan) and once as a
machine-readable `shared/schemas/<track>_taxonomy.json` the classifier and
reranker read. Adding a fourth track is a documented seven-step recipe.

## Iteration status

Each arkitype spec declares an `I0`–`I8` iteration plan. Where the code stands:

| | ai_topics | market_watch | job_watch |
|---|---|---|---|
| I0 scaffold | ✅ | ✅ | ✅ |
| I1 taxonomy + classifier | ✅ | ✅ | ✅ |
| I2 real sources | ✅ 7 feeds | ✅ 13 feeds | ✅ 8 feeds |
| I3 fetchers / ATS modes | ✅ | ✅ | 🟡 adapters exist, employer list not curated into the track |
| I4 gather → artifacts | ✅ | ✅ | ✅ |
| I5 organize / classify | ✅ deterministic | ✅ deterministic | ❌ LLM classifier over full JD not started |
| I6 per-audience rerank | ✅ | ✅ (shared) | ✅ (shared) |
| I7 per-audience digests | ✅ | ✅ (shared) | ✅ (shared) |
| I8 feedback → ranker | ✅ | ✅ (shared) | ✅ (shared) |

Two things this table is saying that are easy to miss:

1. **I6–I8 are track-generic.** `track_rerank.py`, `synthesize_audience_digests.py`,
   and `track_feedback.py` take `--track` and read the taxonomy — so any new track
   inherits reranking, per-audience digests, and the feedback loop for free the
   moment its taxonomy declares audiences.
2. **Classification is deterministic on purpose, for now.** `ai_topics_classify.py`
   describes itself as "a deterministic scaffold, not the eventual LLM-driven
   classifier." That keeps daily runs free and reproducible, and it is the
   deliberate baseline an LLM classifier would have to beat.

## Known gaps — the honest list

- **No iteration metrics.** All three specs declare
  `metrics_artifact_path: artifacts/metrics/<track>/IN-<iteration>.json`, and
  nothing writes it. Every iteration's `test_round_data` — top-K precision,
  dedupe rate, classifier agreement rate, "precision lift vs the I6 baseline",
  feedback weight drift — is currently unmeasured. I8's own success criterion
  cannot be evaluated. This is the biggest single hole.
- **job_watch is the laggard.** The ATS adapters are written and wired, but
  `tracks/job_watch/sources.json` registers a single HN feed, so the curated
  employer list I3 calls for does not exist yet. I5's JD-reading LLM classifier
  has not been started.
- **market_watch substitutes sources.** The spec named Reuters and SEC EDGAR;
  the registry ships CNBC/Yahoo instead of Reuters and SEC *press releases*
  rather than EDGAR filings. Reasonable choices — the specs' open decisions about
  paywalled sources and the EDGAR API are settled in code but not written down.
- **Feedback has been exercised on ai_topics only.** The machinery is generic;
  the mileage is not.
- **Only e2e artifacts exist locally.** Runs write to `tests/tmp/<track>/` by
  design so the working tree stays clean, which also means there is no long
  artifact history to compute drift from yet.

## How it's verified

`bash scripts/test.sh` runs shell syntax checks, Python compile checks, the skill
mirror check, the generated-docs check, and the pytest suite — **616 tests across
49 files** (unit / integration / contract / e2e), green in about 3 minutes on a
laptop. 53 recorded source-contract fixtures let provider adapters be tested
without network access.

## Where to read next

- [`presentation-kit.md`](./presentation-kit.md) — deck outline built from this page
- [`tracks_pipeline.md`](./tracks_pipeline.md) — the six stages, script by script
- [`architecture.md`](./architecture.md) — component map, source-integration loop
- [`roadmap.md`](./roadmap.md) — what's queued next
- [`../README.md`](../README.md) — install and run it yourself
