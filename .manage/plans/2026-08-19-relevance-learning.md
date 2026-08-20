# Relevance, Career, and Network Watch Evolution

Status: in_progress
Owner: Codex; agent_id: 01a017a7-56d7-70d2-b10b-a806a3aeac3c
Last updated: 2026-08-19 America/New_York

## Goal

Make each product iteration measurably better at selecting sources, rejecting noise, scoring useful items, and presenting a small review set. Keep every gathered item in immutable storage, but show only the strongest 20–30% by default. Use `career_watch` consistently as the canonical opportunity and career-intelligence watcher.

## Product contract

- Collection and visibility are separate: low-ranked and rejected items remain auditable without flooding the default inbox.
- The default inbox uses the current candidate set's 75th-percentile score as its minimum; users can control minimum and maximum scores from 0–100.
- Scores are comparable only within a versioned watcher rubric. Every explanation identifies evidence, concerns, rubric version, and source.
- Curation feedback affects later source quality and ranking evaluation; it never silently rewrites historical scores.
- `career_watch` covers job opportunities plus career-relevant news, companies, skills, labor-market shifts, and professional events.
- A future `network_watch` will find people, authors, speakers, hiring leaders, practitioners, and communities worth connecting with and will share global profile/preferences with `career_watch`.

## Iterations

### Iteration 0 — bounded review surface

- [x] Default the inbox to the top quartile of the active candidate set.
- [x] Add user-controlled minimum and maximum score filters with Top 25% and Show all shortcuts.
- [x] Keep filtering client-side and non-destructive so all immutable records remain available.
- Verify with frontend build/component tests and live-workspace count comparisons.

### Iteration 1 — versioned scoring contracts

- Add a scoring rubric to every watcher spec: dimensions, weights, hard exclusions, confidence penalties, score bands, and rubric version.
- Store `score`, `score_version`, `score_dimensions`, `why_relevant`, `concerns`, and `visibility_decision` on normalized items.
- Update `organize-filter-items` and `understand-prioritize-items` to produce evidence-backed structured decisions for content, career, market, and people records—not only jobs.
- Acceptance: deterministic fixture scoring plus agent-output schema tests; no high score without positive evidence.

### Iteration 2 — pre-inbox quality gate

- Separate `collected`, `eligible`, `ranked`, and `visible` states.
- Apply hard exclusions, duplicate suppression, stale-item rules, minimum evidence requirements, and source-specific match rules before ranking.
- Persist rejected items with machine-readable reasons; exclude them from the default API projection unless audit mode is requested.
- Acceptance: top-quartile visibility contains no hard-excluded fixtures and every hidden item has a reason.

### Iteration 3 — career watcher expansion

- [x] Rename the canonical slug, Arkitype spec, runtime track, schemas, classifier/synthesizer, starter commands, UI data, tests, and documentation to `career_watch`.
- Use canonical `career_watch` across taxonomy, samples, sources, artifacts, schedules, feedback, UI labels, scripts, and generated schemas.
- Expand its item types from `job` to `job`, `career_news`, `company_signal`, `skill_signal`, `labor_market`, and `event`.
- Prefer official employer/ATS feeds, professional associations, selected practitioner sources, and labor-market sources; cap broad search aggregators.
- Acceptance: all new writes use `career_watch`, and the digest mixes opportunities with clearly labeled career intelligence.

### Backlog — shared career context and network watcher

- Create a versioned `career_context` shared by `career_watch` and `network_watch`: CV evidence, goals, target roles, industries, locations, constraints, companies, skills, and connection intent.
- When promoted from backlog, add `network_watch` with people-specific fields: person, role, organization, reason_to_connect, shared_context, evidence_url, suggested_approach, and freshness.
- Start from authors/speakers/maintainers/hiring leaders already observed by career sources, then add a small curated source pack after the local profile is ready.
- Allow duplicates across career/network initially; preserve a common provenance key for later entity resolution.
- Acceptance: network results explain why this person matters and never infer private contact data.

### Iteration 5 — source precision learning

- Track per-source yield: collected, eligible, top-quartile, saved, dismissed, duplicate, failed, and stale counts by rubric version.
- Rank sources using precision-at-visible, save rate, dismissal rate, freshness, coverage diversity, and fetch reliability.
- Automatically reduce cadence or quarantine persistently noisy sources; require review before permanent removal.
- Feed source-quality findings into `explore-start`, `explore-discover-sources`, and `gather-curate-items` recommendations.
- Acceptance: noisy-source fixtures are down-weighted without hiding a source's historical records.

### Iteration 6 — relevance evaluation and feedback calibration

- Build privacy-safe golden fixture sets per watcher and replay actual Save/Dismiss feedback locally.
- Report precision@k, recall of known good items, NDCG, visible-set size, source diversity, explanation completeness, and score calibration.
- Gate changes to skills, watcher specs, ranking code, or starter sources on non-regression thresholds.
- Surface score-distribution and source-yield diagnostics in the Watchers UI.
- Acceptance: every product iteration reports before/after relevance metrics and the active rubric/source versions.

## Profile gate

Personalized `career_watch` source selection, and the future `network_watch`, require `profile/cv.md` and `profile/prefs_global.md`. They are currently missing. Until the user supplies or initializes them, do not claim that generic sources are personalized.

## Verification

- Focused UI tests for percentile defaults and score-bound changes.
- Watcher generation and canonical-slug tests.
- Item-decision schema and immutable replay tests.
- Per-watcher scoring/source-quality fixture evaluation.
- Full `scripts/test.sh` before every completed iteration.
- Current checkpoint: local immutable state migrated 151 records with zero old-slug records remaining; 143 career items retained; full suite passes with 720 passed and 28 skipped.
