# tekt.observer

I am extending the work that Jonas van der Heyden did and integrating it with a practice of AI Fleet Management called SignalFlow. It's how we coordinate a series of steps in a process to achieve a goal useful for people. 

Tekt.Observer helps with Explore, Seek, Gather, Organize, Understand, and Generate. 

It's focused on being the best at exploring uncharted territories, creating paths for which seekers can go and get to those destinations ( by generating code or script ), it can execute the process of gathering this data, as well as organizing/categorizing/ annotating it, understanding (in the way that makes sense as it relates to us, our goals), and then generating (digests, reports)


Starting points 

## tekt.md 
Tekt is used as the core tooling engine, and installs all the different agents that we want to use. 

- Claude Desktop/Cowork, Claude Code 
- Codex CLI, ChatGPT Codex/App (coming soon)
- OpenClaw, Hermes Agent, ZeroClaw, NanoClaw
- VSCode, Zed 

It also sets up communications tooling for S3 to communicate with other instanes of Tekt or anyone else syncing on the same buckets. 

## tekt.signalflow 
We have made a set of prompts for an AI fleet to execute parts of the work and collect / organize data with S3. 
This is the following process that tekt.observer needs to complement.

- explore - using browser use to understand and generate crawl4ai script for new sources
- seek - use crawl4ai to execute the crawl4ai script on existing sources
- gather - run scheduler to seek data from sources and gather it one place
- organize - organize, categorize, annotate, relate,correlate, index
- understand - rerank opportunities based on a profile, prioritize for impact
- generate - create digest that includes a brief of how to move towards success

## jobwatch 

jobwatch helps technical job seekers find relevant roles from direct sources before they are buried on large job boards.

It monitors company career pages and other unaggregated sources you choose, reads the full job description, and matches jobs against your CV and preferences. Instead of noisy keyword alerts, you get a short digest of opportunities that are actually worth your attention.

Example:

![Example daily digest email showing ranked job matches.](docs/images/digest_email.png)

<!--
jobwatch finds the roles. Trackers manage the ones you already found; writers draft applications you haven't decided on yet. This is the step before both.
-->
### Quick start:
1. `git clone git@github.com:xingh/tekt.observer.git && cd "$(basename "$_" .git)"`
2. `bash scripts/bootstrap_machine.sh --agent {claude,codex,gemini}`
3. Optional: run `bash scripts/start_setup_agent.sh --agent {claude,codex,gemini}` only if bootstrap did not start guided setup automatically or was invoked with `--no-start-setup-agent`.

For a more detailed set-up guide, see [New User Setup](#new-user-setup).

## Quick start — the three example tracks

The repo ships three example tracks that share the same six-stage pipeline (`docs/tracks_pipeline.md`):

- **`ai_topics`** — AI content tracker (posts, papers, videos, podcasts) for an Architect audience
- **`market_watch`** — investor market-news tracker with a watchlist-driven portfolio-alert digest
- **`job_watch`** — AI-enabled engineering roles (AI Engineer, prompt engineer, AI instructor / trainer, DevRel)

Each runs end-to-end without any API keys or provider CLI. Bootstrap once, then run any track.

```bash
# One-time: create the repo-local virtualenv (~30 s; skip Chromium for the feed pipeline)
bash scripts/bootstrap_venv.sh --no-chromium

# Live run: fetches real sources, enriches with OpenGraph metadata,
# classifies, computes trends, reranks per audience, synthesizes per-audience digests.
bash scripts/run_pipeline.sh --track ai_topics    --live
bash scripts/run_pipeline.sh --track market_watch --live
bash scripts/run_pipeline.sh --track job_watch    --live

# Fixture / offline mode (omit --live). ai_topics reads a shipped HTML fixture;
# market_watch and job_watch produce empty discovery to exercise the pipeline shape.
bash scripts/run_pipeline.sh --track ai_topics
```

Each run writes into `tests/tmp/<track>/`, mirroring `scripts/test_track_workflow.sh` so the tracked working tree stays clean.

### Review each step

For any track, the pipeline puts each stage's output in a predictable place. After a run:

```bash
TRACK=ai_topics DATE=$(date +%F)
tree tests/tmp/$TRACK/artifacts | head -30

# Concrete files:
tests/tmp/$TRACK/artifacts/discovery/$TRACK/$DATE.json         # 1. gather
tests/tmp/$TRACK/artifacts/enrichment/$TRACK/urls.json         # 2. enrich (cached across runs)
tests/tmp/$TRACK/artifacts/organized/$TRACK/$DATE.json         # 3. classify
tests/tmp/$TRACK/artifacts/trends/$TRACK/$DATE.json            # 4. trends
tests/tmp/$TRACK/artifacts/ranked_audience/$TRACK/*/$DATE.json # 5. rerank (per audience)
tests/tmp/$TRACK/artifacts/digests/$TRACK/$DATE.json           # 6. synthesize (default)
tests/tmp/$TRACK/artifacts/digests/$TRACK/*/$DATE.json         # 6. synthesize (per audience, I7)
tests/tmp/$TRACK/tracks/$TRACK/digests/$DATE.md                # 6. rendered markdown
```

### View the result

Two ways: a live server (auto-reloads on refresh) or a publishable static site.

```bash
# Live viewer (loopback only, defaults to 127.0.0.1:8765)
./.venv/bin/python scripts/serve_html.py --root tests/tmp/ai_topics

# Then open any of these in a browser:
#   http://127.0.0.1:8765/                                              — track index
#   http://127.0.0.1:8765/track/ai_topics/<YYYY-MM-DD>                  — consolidated daily report
#   http://127.0.0.1:8765/track/ai_topics/<YYYY-MM-DD>?audience=builders — same report scoped to an audience
#   http://127.0.0.1:8765/track/ai_topics/feed/<YYYY-MM-DD>             — social-feed grid with OG images
#   http://127.0.0.1:8765/track/ai_topics/trends/<YYYY-MM-DD>           — trend charts + keyword cloud
#   http://127.0.0.1:8765/track/ai_topics/<YYYY-MM-DD>/details          — structured digest tables
#   http://127.0.0.1:8765/track/ai_topics/sources                       — sources + persona
#   http://127.0.0.1:8765/raw/digests/ai_topics/<YYYY-MM-DD>.json       — raw digest JSON

# Publishable static site
./.venv/bin/python scripts/render_html.py --root tests/tmp/ai_topics --out site/
# then open file://.../site/index.html or upload the site/ directory anywhere
```

### Audience switching

Each track's arkitype spec declares an audience list (see `.arkitype/00-*.md`). The rerank stage
scores every item for every audience; the report swaps top-matches for the requested audience.

- ai_topics: `builders · operators · managers · architects · leaders`
- market_watch: `investors · portfolio_managers · allocators · gps · lps`
- job_watch: `individual_contributor · senior_ic · tech_lead · manager · instructor`

The report hero has a link row for one-click switching; the URL forms are
`/track/<track>/<date>?audience=<id>` (live) and `/track/<track>/<date>/audience/<id>` (both).

## Why use it?

- **Find roles earlier:** track company pages and other direct sources, not just aggregators.
- **Better matching:** evaluate the full job description against your CV and preferences, not just keywords.
- **Stay focused:** get a concise digest by email, Telegram, or as Markdown.

## Who is it for?

jobwatch is a good fit if you:

- are comfortable using the command line
- want more control than standard job alerts provide

It is probably **not** a good fit if you:

- do not have access to a supported coding-agent CLI account or API key
- do not want to use a CLI tool
- are on Windows (we support MacOS and most Linux distributions)

<!-- 
*How much will this cost me in tokens?*

Since most of the functionality is deterministic code, the daily checks will be very cheap (< 100k tokens). One-time set-up might be more expensive due to the need to integrate new sources.
-->
## New User Setup

This repository runs an agent-assisted job-search workflow with per-track discovery, ranking, digest generation, and optional delivery to Logseq, email, or Telegram. Scheduled automation supports Codex CLI, Claude Code CLI, and Gemini CLI.

Each track run produces local JSON and Markdown artifacts first. Delivery is a separate opt-in step.

1. Requirements:
   - Python 3
   - the Codex CLI, Claude Code CLI, or Gemini CLI
   - for Claude, run Claude Code login locally before scheduled runs
   - for Gemini, authenticate Gemini CLI locally before scheduled runs
   - on Linux with Codex, `bwrap` if you want Codex sandboxing backed by Bubblewrap
2. From the repo root, choose the automation agent and bootstrap the checkout for local use:

   ```bash
   bash scripts/bootstrap_machine.sh --agent claude
   # or
   bash scripts/bootstrap_machine.sh --agent codex
   # or
   bash scripts/bootstrap_machine.sh --agent gemini
   ```

   This writes machine-local config, creates local profile placeholders, bootstraps the repo-local virtualenv, and generates scheduler artifacts under `.scheduler/`. In an interactive terminal, bootstrap offers to start the guided setup agent; in non-interactive runs, pass `--start-setup-agent` to launch it automatically.

   <details><summary>What the bootstrap script writes</summary>
   Machine-local config lives in `.env.local`, which is gitignored. `setup_machine.sh` writes:

   - `JOB_AGENT_ROOT`
   - `JOB_AGENT_PROVIDER`
   - `JOB_AGENT_BIN`
   - optional `LOGSEQ_GRAPH_DIR`
   - optional `JOB_AGENT_SECRETS_FILE` plus non-secret `JOB_AGENT_SMTP_*` placeholders for email delivery

   Local profile data lives in `profile/`, which is also gitignored. Setup creates default placeholders:

   - `profile/cv.md`: the primary agent-readable CV context
   - `profile/prefs_global.md`: durable preferences that apply across tracks

   Before or during your first track setup, replace those placeholders with your own information. You can also copy a PDF CV into `profile/`; if `profile/cv.md` is still the default, the setup agent can help turn the PDF into Markdown. The Markdown CV remains the canonical file the agent reads.

   If you only need to regenerate machine-local config later, run:

   ```bash
   bash scripts/setup_machine.sh --agent claude
   # or
   bash scripts/setup_machine.sh --agent codex
   # or
   bash scripts/setup_machine.sh --agent gemini
   ```
   </details>

3. If you are on Ubuntu and using Codex with `bwrap`, install the generated AppArmor profile:

   ```bash
   sudo bash scripts/install_bwrap_apparmor.sh
   ```

   Skip this on macOS. On Linux, this is only needed on hosts where AppArmor restricts unprivileged user namespaces.

4. Run the guided setup agent to create your first search track:

   ```bash
   bash scripts/start_setup_agent.sh --agent claude
   # or
   bash scripts/start_setup_agent.sh --agent codex
   # or
   bash scripts/start_setup_agent.sh --agent gemini
   ```

   The setup flow fills local profile files, creates the track files, discovers and validates sources, runs the first local digest before email testing, asks which delivery methods you want, configures scheduling if requested, and validates the track.

   Track-specific preferences live in `tracks/<track-slug>/prefs.md`. They are still required even when `profile/cv.md` and `profile/prefs_global.md` are filled, because each track can have narrower goals, keywords, constraints, and red flags.

5. Let the setup agent configure delivery and scheduling.

   The setup agent asks whether you want scheduled runs, how often they should run, and at what local time. It then writes `.schedule.local` with `scripts/configure_schedule.py` and installs the shared scheduler with `bash scripts/install_scheduler.sh`.

   Supported schedule choices:

   - daily at `HH:MM`
   - weekly on `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, or `sun` at `HH:MM`
   - monthly on day `1` through `31` at `HH:MM`

   On Linux, scheduler install updates your user crontab with a checkout-specific per-minute dispatcher. On macOS, it installs a checkout-specific LaunchAgent. If you skip scheduling during setup, you can still run tracks manually.


## Manual Run

To run a track immediately:

```bash
bash scripts/run_track.sh --track <track-slug>
```

By default, this leaves the local JSON and Markdown artifacts in the repository and does not deliver them anywhere else.

Optional delivery targets can be requested per run:

```bash
bash scripts/run_track.sh --track <track-slug> --delivery logseq
bash scripts/run_track.sh --track <track-slug> --delivery email
bash scripts/run_track.sh --track <track-slug> --delivery telegram
bash scripts/run_track.sh --track <track-slug> --delivery logseq --delivery email
bash scripts/run_track.sh --track <track-slug> --delivery logseq --delivery telegram
```
<!--

## Source Integration Loop

The setup agent auto-runs the source integration loop on the top 2 `integration_needed` sources during initial bring-up of a new track, so most users won't need to invoke it directly. Run it manually when you want to integrate sources beyond that budget, when you add a new source to an existing track, or when you want to upgrade lower-importance sources later:

```bash
./.venv/bin/python scripts/source_integration.py --track <track-slug> --source "<Source Name>" --today YYYY-MM-DD --canary-title "<Expected Title>"
```

The script orchestrates `eval_source_quality.py` (deterministic validator plus an LLM reviewer) and dispatches a coding agent against the resulting `integration_ticket`, then rediscovers and re-evaluates. It iterates up to `--max-attempts` and exits at `pass`, `blocked`, or `retry_limit`.

Successful source integrations land as edits in your working tree. To upstream them, push the branch from your fork and open a PR per [`CONTRIBUTING.md`](./CONTRIBUTING.md). See [`docs/architecture.md`](./docs/architecture.md) for the full source-integration-loop diagram and artifact layout.


## Agent Provider

Select the provider explicitly during setup. The setup scripts write the selected provider and executable path into `.env.local`.

For Codex:

```bash
export JOB_AGENT_PROVIDER=codex
export JOB_AGENT_BIN=/absolute/path/to/codex
```

For Claude Code:

```bash
export JOB_AGENT_PROVIDER=claude
export JOB_AGENT_BIN=/absolute/path/to/claude
```

`scripts/setup_machine.sh --agent claude` writes those values when `claude` is discoverable on `PATH`. Claude runs use `claude -p` noninteractively with scoped allowed tools and normal project context loading; `--bare` is not used by default.

For Gemini CLI:

```bash
export JOB_AGENT_PROVIDER=gemini
export JOB_AGENT_BIN=/absolute/path/to/gemini
```

`scripts/setup_machine.sh --agent gemini` writes those values when `gemini` is discoverable on `PATH`. Scheduled Gemini runs use headless mode with `--output-format stream-json`, `--approval-mode yolo`, and `GEMINI_SANDBOX=false` by default. Override with `JOB_AGENT_GEMINI_APPROVAL_MODE`, `JOB_AGENT_GEMINI_SCHEDULED_APPROVAL_MODE`, or `JOB_AGENT_GEMINI_SANDBOX` if your local Gemini configuration needs stricter policy.

## Scheduled Runs

The setup agent normally manages `.schedule.local`. For manual maintenance, use the helper rather than editing scheduler syntax by hand:

```bash
./.venv/bin/python scripts/configure_schedule.py --track <track-slug> --cadence daily --time 08:00
./.venv/bin/python scripts/configure_schedule.py --track <track-slug> --cadence weekly --weekday mon --time 08:00 --delivery logseq
./.venv/bin/python scripts/configure_schedule.py --track <track-slug> --cadence monthly --month-day 1 --time 08:00 --delivery email
./.venv/bin/python scripts/configure_schedule.py --track <track-slug> --cadence weekly --weekday fri --time 18:00 --delivery telegram
bash scripts/install_scheduler.sh
```

`configure_schedule.py` keeps one active schedule entry per track, replaces that track's old entry, and preserves other scheduled tracks.

## Email Digest

Daily digest emails are rendered from the structured digest JSON and ranked overview JSON, not from the Logseq/Markdown output.

Preview an email without sending it:

```bash
./.venv/bin/python scripts/send_digest_email.py --track <track-slug> --date YYYY-MM-DD --dry-run
```

To send through SMTP, keep only non-secret SMTP config in `.env.local`. Put the real app password or SMTP token either behind `JOB_AGENT_SMTP_PASSWORD_CMD` in `.env.local` or as `export JOB_AGENT_SMTP_PASSWORD=...` in the external shell snippet named by `JOB_AGENT_SECRETS_FILE`. For common providers, you can start with `JOB_AGENT_EMAIL_PROVIDER` plus `JOB_AGENT_EMAIL_ACCOUNT`; explicit `JOB_AGENT_SMTP_*` values still override the provider defaults.

```text
JOB_AGENT_EMAIL_PROVIDER
JOB_AGENT_EMAIL_ACCOUNT
JOB_AGENT_SECRETS_FILE
JOB_AGENT_SMTP_HOST
JOB_AGENT_SMTP_PORT
JOB_AGENT_SMTP_FROM
JOB_AGENT_SMTP_TO
JOB_AGENT_SMTP_USERNAME
JOB_AGENT_SMTP_PASSWORD_CMD
JOB_AGENT_SMTP_TLS
```

Current provider presets cover Gmail, Fastmail, Outlook.com/Hotmail, and Proton business SMTP. For Proton, `JOB_AGENT_EMAIL_PROVIDER=proton` assumes Proton's business SMTP flow: use a custom-domain sending address in `JOB_AGENT_EMAIL_ACCOUNT`, authenticate with a Proton-generated SMTP token, and keep real secrets outside the repo. Proton Mail Bridge is still out of scope for the preset path. Do not put SMTP passwords in tracked files, `.env.local`, or chat transcripts. Plaintext repo-local `JOB_AGENT_SMTP_PASSWORD` is no longer supported; use `JOB_AGENT_SMTP_PASSWORD_CMD` or put `export JOB_AGENT_SMTP_PASSWORD=...` in the external file named by `JOB_AGENT_SECRETS_FILE`. After `.env.local` is filled and a digest JSON exists, run the dry-run command first, then test the same command without `--dry-run` or use `--delivery email` on `run_track.sh`.

Provider-specific credential notes:

- Gmail: `JOB_AGENT_EMAIL_PROVIDER=gmail` fills `smtp.gmail.com`, port `587`, and `STARTTLS`. Google only exposes app passwords for accounts with 2-Step Verification enabled. Put the generated app password in your password store and point `JOB_AGENT_SMTP_PASSWORD_CMD` at it, or put `export JOB_AGENT_SMTP_PASSWORD=...` in `JOB_AGENT_SECRETS_FILE`.
- Fastmail: `JOB_AGENT_EMAIL_PROVIDER=fastmail` fills `smtp.fastmail.com`, port `587`, and `STARTTLS`. Fastmail requires app passwords for third-party SMTP clients; keep that app password outside the repo and retrieve it via `JOB_AGENT_SMTP_PASSWORD_CMD` or `JOB_AGENT_SECRETS_FILE`.
- Outlook.com / Hotmail: `JOB_AGENT_EMAIL_PROVIDER=outlook` or `hotmail` fills `smtp-mail.outlook.com`, port `587`, and `STARTTLS`. Microsoft documents Modern Auth / OAuth2 as the preferred path, so use this preset only when your account has a working app password or SMTP credential for SMTP AUTH. Store that secret outside the repo the same way.
- Proton business SMTP: `JOB_AGENT_EMAIL_PROVIDER=proton` fills `smtp.protonmail.ch`, port `587`, and `STARTTLS`. Use a custom-domain sending address in `JOB_AGENT_EMAIL_ACCOUNT` and store the Proton-generated SMTP token outside the repo. Proton Mail Bridge remains out of scope for this preset path.

## Telegram Delivery

Telegram delivery reuses the concise digest body rendered from the structured digest JSON and ranked overview JSON. Long digests are split across multiple Telegram messages automatically.

Preview the Telegram messages without sending them:

```bash
./.venv/bin/python scripts/send_digest_telegram.py --track <track-slug> --date YYYY-MM-DD --dry-run
```

For real Telegram delivery, keep the non-secret chat id in `.env.local` and keep the bot token outside the repo:

```text
JOB_AGENT_SECRETS_FILE
JOB_AGENT_TELEGRAM_CHAT_ID
JOB_AGENT_TELEGRAM_BOT_TOKEN_CMD
```

If you prefer a password manager, point `JOB_AGENT_TELEGRAM_BOT_TOKEN_CMD` at it. If you prefer a static token, put `export JOB_AGENT_TELEGRAM_BOT_TOKEN=...` only in the external file named by `JOB_AGENT_SECRETS_FILE`. After a digest JSON exists, run the dry run first, then use `--delivery telegram` on `run_track.sh` or test `scripts/send_digest_telegram.py` without `--dry-run`.

## Logseq Delivery

Logseq delivery copies the rendered daily digest and ranked overview into a Logseq graph.

Set `LOGSEQ_GRAPH_DIR` in `.env.local`, either by rerunning setup:

```bash
bash scripts/setup_machine.sh --agent claude --logseq-graph-dir /absolute/path/to/logseq
# or
bash scripts/setup_machine.sh --agent codex --logseq-graph-dir /absolute/path/to/logseq
# or
bash scripts/setup_machine.sh --agent gemini --logseq-graph-dir /absolute/path/to/logseq
```

or by editing `.env.local` locally:

```bash
export LOGSEQ_GRAPH_DIR=/absolute/path/to/logseq
```

Then run `scripts/run_track.sh` with `--delivery logseq`.

-->
## Development Checks

To run the repo test suite:

```bash
bash scripts/test.sh
```

## Contributing

For an architecture overview see [`docs/architecture.md`](./docs/architecture.md).
For the shared six-stage pipeline (discover → enrich → classify → trends → synthesize → render) used by jobwatch, ai_topics, and market_watch tracks, see [`docs/tracks_pipeline.md`](./docs/tracks_pipeline.md).
For the fork-and-PR workflow see [`CONTRIBUTING.md`](./CONTRIBUTING.md).
