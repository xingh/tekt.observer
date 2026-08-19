# Local portfolio workspace

The live viewer is a local-first dashboard over the artifacts your workflows produce. It does not replace tracks or the deterministic pipeline: it projects their existing JSON into one signal inbox and adds private, file-backed organization and feedback.

## Start with populated content

A fresh checkout includes three starter workflow definitions and their keyless source registries:

| Workflow | Starting question | Default audience | Sources |
| --- | --- | --- | --- |
| `topic_watch` | How is AI changing business workflows, operating models, governance, and customer operations? | `managers` | 10 AI publications, research feeds, and focused HN queries |
| `market_watch` | What changed for AI-related public companies or the rules governing them? | `investors` | 16 market, regulator, financial-news, and focused HN feeds |
| `job_watch` | Which technical and business professions are being reshaped by applied AI? | `senior_ic` | 13 job feeds and profession-specific HN queries |

These built-ins are generated from `.arkitype/watchers/{topic_watch,job_watch,market_watch}/`. Edit the specs and run `./.venv/bin/python scripts/generate_watchers.py`; do not edit their generated track metadata or shared schemas directly.

Populate one shared workspace and start the viewer:

```bash
bash scripts/bootstrap_venv.sh --no-chromium
bash scripts/run_starter_workflows.sh --serve
```

Open `http://127.0.0.1:8765/`. The launcher writes nine clearly marked sample signals—three per starter—to the ignored `tests/tmp/starter-workflows/` tree, so this path works without network access. Omit `--serve` if you want to inspect the artifacts first. Use `--today YYYY-MM-DD` or `--scratch PATH` to override the defaults.

Replace the sample workspace with current feed data when you are ready:

```bash
bash scripts/run_starter_workflows.sh --live --serve
```

For one workflow only:

```bash
bash scripts/run_pipeline.sh --track topic_watch --live
./.venv/bin/python scripts/serve_html.py --root tests/tmp/topic_watch
```

Live runs depend on upstream availability and feed windows. The sample URLs use `example.com` deliberately and should not be mistaken for fetched reporting or job listings. For deterministic runner validation beyond the sample workspace, use `bash scripts/test_track_workflow.sh`.

## What the dashboard reads

The dashboard combines, without rewriting, items from:

- `artifacts/organized/<track>/`
- `artifacts/ranked_audience/<track>/`
- `artifacts/digests/<track>/`
- `artifacts/discovery/<track>/`

Items receive a stable cross-track ID shaped like `<track>:<item_key>`. When the same item occurs in more than one artifact, the highest audience score wins. Filters can narrow the inbox by portfolio, track, audience, topic, or text.

## Private state

Run the following only when you want explicit editable state:

```bash
./.venv/bin/python scripts/portfolio_state.py init
```

It creates two ignored files:

- `profile/interests.json` — reusable interests with labels, descriptions, and keywords
- `profile/portfolios.json` — named groups of tracks and interests

Optional per-track files are also ignored for user-created tracks:

- `tracks/<track>/track.json` — display name, status, default audience, and interest mappings
- `tracks/<track>/taxonomy.json` — editable topic and audience labels/descriptions layered over the shipped classifier schema

If the profile files do not exist, the server projects an implicit **All Tracks** portfolio in memory. Merely opening the viewer never initializes or rewrites local state.

## HTTP API

Read routes:

| Route | Purpose |
| --- | --- |
| `GET /api/v1/state` | Interests, portfolios, write capability, and the session CSRF token |
| `GET /api/v1/items` | Unified signal items; accepts `track`, `interest`, `audience`, `topic`, and `q` |
| `GET /api/v1/interests` | Reusable interests |
| `GET /api/v1/portfolios` | Named portfolios |
| `GET /api/v1/tracks/<track>` | Track metadata |
| `GET /api/v1/tracks/<track>/taxonomy` | Resolved taxonomy |
| `GET /api/v1/operations` | Recent background operations |
| `GET /api/v1/operations/<id>` | One pollable operation |

Mutation routes support creating, updating, and deleting interests and portfolios; updating track metadata and taxonomy; recording feedback; starting `run` or `validate_sources` operations; and cancelling an active operation. Referenced interests and the default portfolio cannot be deleted.

Writes require all of the following:

- a loopback server binding
- `Content-Type: application/json`
- a matching same-origin request, when `Origin` is present
- the `X-CSRF-Token` returned by `/api/v1/state`
- a body no larger than 256 KiB

Non-loopback bindings are read-only. Static exports remain read-only and contain no management or feedback controls.

## Background operations

Open `/manage` from the dashboard to:

- run a workflow against its live registry
- validate a workflow's configured sources
- create or replace its daily, weekly, or monthly schedule entry
- choose configured Logseq, email, or Telegram delivery targets
- inspect the state and bounded log of recent operations

The local operation manager exposes this work as pollable `run`, `validate_sources`, and `schedule` operations. Only one active operation is allowed per track; state is retained in ignored `logs/portfolio-operations.json`, capped at 200 records. Cancellation works across HTTP requests and preserves the terminal `cancelled` state.

New workflow setup and source curation remain interactive agent tasks because they involve recommendations and reviewable external-source decisions. The management page links to those flows rather than launching an unattended interactive agent. Delivery credentials and scheduler installation also remain in the guided setup documented in [`machine_setup.md`](./machine_setup.md); the browser schedule form only updates `.schedule.local`.

## Customize after exploring

The starter workflows are broad examples. For a durable workflow matched to you, use the guided setup:

```bash
bash scripts/start_setup_agent.sh --agent codex   # or claude / gemini
```

That flow creates a private track, discovers and validates sources, produces the first digest, and then offers scheduling and delivery configuration.
