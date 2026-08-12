# Presentation Kit

_For an agent (or human) asked to "make a presentation about tekt.observer."_

Everything here is structure and narrative. **Facts live in
[`capabilities.md`](./capabilities.md)** — pull every number, claim, and status
from there rather than restating them in this file, so the two can never drift.
If a fact you need isn't in `capabilities.md`, verify it in the repo and add it
there first.

## Before you build anything

1. Read [`capabilities.md`](./capabilities.md) end to end — it is the status of record.
2. Skim [`tracks_pipeline.md`](./tracks_pipeline.md) for the stage-by-stage script map.
3. Skim [`architecture.md`](./architecture.md) for the two Mermaid diagrams you can reuse verbatim.
4. Check `git log --oneline -15` — commits are tagged by iteration (`Iteration I8: ...`), which gives you a real "what shipped when" timeline.
5. Confirm the iteration table is still current; if `capabilities.md` is stale, refresh it before presenting stale status as fact.

## Pick the audience first

The same material supports three different talks. Choose one; don't average them.

| Audience | What they want | Lead with | Skip |
|---|---|---|---|
| **Practitioners / potential users** | "Would this save me time?" | The 60-second live demo, then the feedback loop | Iteration numbers, internal architecture |
| **Engineers / contributors** | "How is it built, where can I help?" | The six-stage pipeline and the generic-vs-track-specific split | Setup instructions |
| **Stakeholders / reviewers** | "Is this real, and what's next?" | The iteration status table and the honest-gaps list | Script names, CLI flags |

## Slide outline (12 slides, ~15 minutes)

Trim to 6 for a lightning talk by keeping the starred (★) slides.

1. ★ **The problem.** Aggregators are late and noisy. By the time something
   reaches a big board or a "top stories" page, you're reading it after everyone
   else — filtered by someone else's idea of what matters. *One sentence, no bullets.*
2. ★ **What tekt.observer is.** One line from the top of `capabilities.md`: it
   turns a question you care about into a daily briefing you actually read.
   Name the three shipped tracks and the question each answers.
3. **The six stages.** Use the explore → seek → gather → organize → understand →
   generate diagram from `capabilities.md`. The point to land: *the same pipeline
   serves AI news, market news, and job postings* — only the taxonomy and
   classifier change.
4. ★ **Demo.** See the demo script below. This is the slide that sells it; give
   it the most time.
5. **Sources, not aggregators.** The discovery-mode count and the keyless feed
   reader. Contrast: a keyword alert versus reading the source directly.
6. **Taxonomy and audiences.** Every track declares audiences; every item is
   scored for every audience in one pass. Show the audience-switcher URLs — the
   *same day's data*, reranked for a different reader.
7. ★ **The feedback loop.** save / hide / click → append-only event log → boosts
   applied on the next run. Show the boost values. This is the "SignalFlow"
   idea made concrete: delivery signals feed back into ranking.
8. **Deterministic by default.** No API keys, no LLM calls, in the daily loop —
   free, reproducible, fast. Agents are used for setup and for self-healing
   sources, where judgment actually helps. Name the token cost of a daily run: zero.
9. **Self-healing sources.** The source-integration loop: eval → integration
   ticket → coding agent → re-discover → re-evaluate. Reuse the sequence diagram
   from `architecture.md`. This usually gets the best reaction from engineers.
10. ★ **Where it stands.** The I0–I8 iteration table from `capabilities.md`,
    unedited. Do not soften the 🟡 and ❌ cells.
11. **The honest gaps.** Especially the measurement gap — nothing writes the
    declared `metrics_artifact_path`, so iteration success criteria are currently
    unmeasured. Presenting this openly earns more credibility than omitting it.
12. ★ **What's next / how to help.** Pull queued items from
    [`roadmap.md`](./roadmap.md) and the gaps list. Close with the quick-start
    commands so the audience can run it in 60 seconds.

## Demo script

Rehearse this; it's four commands and about 90 seconds of waiting.

```bash
# 1. Setup (do this BEFORE the talk — it takes ~30s and is boring to watch)
bash scripts/bootstrap_venv.sh --no-chromium

# 2. Live run — narrate the stage banners as they print
bash scripts/run_pipeline.sh --track ai_topics --live

# 3. Show the artifacts — one file per stage, predictable paths
tree tests/tmp/ai_topics/artifacts | head -30

# 4. Open the report
./.venv/bin/python scripts/serve_html.py --root tests/tmp/ai_topics
```

In the browser, walk this path — it maps to slides 4, 6, and 7:

1. `/` — the track index
2. `/track/ai_topics/<date>` — the consolidated daily report
3. `/track/ai_topics/<date>?audience=builders` then `?audience=leaders` — same
   day, different reader, different top matches
4. `/track/ai_topics/trends/<date>` — velocity and the keyword cloud
5. `/track/ai_topics/feed/<date>` — click **save** on a card, then say the line:
   *"that just appended an event; the next run ranks it higher."*

**Offline fallback:** drop `--live` and the run uses a shipped HTML fixture, so
the demo works with no network. Say so out loud — "this is fixture mode" — rather
than letting the audience assume it fetched live.

**Failure fallback:** if a live feed times out mid-demo, keep going. The pipeline
continues past individual stage failures by design, and saying that is a better
story than a clean run.

## Diagrams you can reuse

| Diagram | Source | Good for slide |
|---|---|---|
| Six-stage ASCII flow | `capabilities.md` | 3 |
| Pipeline + artifact paths | `tracks_pipeline.md` | 3, 4 |
| Component map (Mermaid flowchart) | `architecture.md` | 9 |
| Scheduled run (Mermaid sequence) | `architecture.md` | 8 |
| Source-integration loop (Mermaid sequence) | `architecture.md` | 9 |
| Example digest email screenshot | `docs/images/digest_email.png` | 4 or 12 |

If you're building an HTML artifact rather than slides, Mermaid renders natively
in fenced ```mermaid blocks — copy the diagrams straight across.

## Likely questions

- **"How much does it cost to run?"** The daily pipeline makes no LLM calls —
  it's deterministic Python over public feeds. Cost is agent tokens during track
  setup and source integration only.
- **"How is this different from an RSS reader?"** Classification against a
  taxonomy you declare, per-audience reranking, trend and cross-source detection,
  and a feedback loop that changes tomorrow's ranking. A reader shows you
  everything in order; this ranks it for a specific reader.
- **"Why deterministic classification instead of an LLM?"** Free, reproducible,
  and it's the baseline an LLM classifier has to beat. The LLM classifier is a
  declared iteration (I5) that has not landed for job_watch.
- **"Does it work for X?"** Adding a track is a documented seven-step recipe in
  `tracks_pipeline.md`; reranking, per-audience digests, and feedback come free
  once the taxonomy declares audiences.
- **"Is my data going anywhere?"** No. Artifacts are local files; delivery is
  opt-in per run; secrets are loaded at runtime from outside the repo.

## Claims to avoid

- Don't say the classifiers are AI-powered. They are keyword/regex today.
- Don't present I5 or the job_watch employer list as shipped.
- Don't quote precision, recall, or "lift" numbers — none are measured yet
  (see the measurement gap).
- Don't imply Reuters or SEC EDGAR are wired into market_watch.
- Don't promise Windows support; macOS and Linux only.
