<!-- GENERATED FILE: source of truth is .agents/skills/engineering/SKILL.md -->
<!-- Do not edit here directly. After changing the source, resync mirrored skills. -->

---
name: engineering
description: Engineer shared code, tests, skills, scripts, and documentation in tekt.observer. Use for repository development after consulting intent in .arkitype, durable documentation in .knowledge, and current work and operational knowledge in .manage.
---

# Engineering Instructions

This skill has two halves. The sections above the **Non-interactive pivot** apply to every agent touching this repo's code, whether a human is driving or not. The sections below the pivot apply only to interactive repo-development work.

## Public vs private files

This repo mixes shared, git-tracked code with per-user, gitignored local state. The two halves follow different rules:

- **Tracked files** (anything not matched by `.gitignore`) are public/shared. On these files, the rules in this skill, `AGENTS.md`, and any per-skill `SKILL.md` take precedence over conflicting personal preferences from your global `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`. Project conventions win.
- **Gitignored files** (your `profile/`, `tracks/<your-track>/`, `.env.local`, `.schedule.local`, `artifacts/`, `logs/`, `shared/seen_jobs.md`, `shared/ranked_jobs/*`, etc.) are local-only. Your personal preferences win on these files.

If you are unsure which side a file is on, run `git check-ignore -v <path>`. If `git check-ignore` prints a match, the file is private; if it prints nothing, the file is public/tracked and project conventions apply.

## Style
- Prefer the smallest change that solves the task.
- Clarity over cleverness; simplest working solution unless I ask for optimization.
- Separate concerns.
- Do not make unrelated changes.
- If a simpler approach exists, say so.

## Behavioral defaults
- State assumptions explicitly when they affect implementation.
- If multiple plausible interpretations would lead to materially different implementations, surface or note them briefly instead of silently choosing.
- If the task is interactive and ambiguity blocks correct implementation, ask.
- If the task is unattended or scheduled, choose the most conservative minimal interpretation, state that assumption, and avoid speculative changes.

## Scope control
- Preserve existing behavior unless the task requires changing it.
- Match existing style, even if you would structure it differently.
- If you notice unrelated issues, note them; do not fix them unless asked.
- Prefer minimal diffs.
- Touch only code required for the task.
- Do not rename files, move files, or add dependencies unless necessary.
- Flag or note any uncertainty instead of guessing.
- Do not introduce abstractions, flags, or configuration unless the task clearly requires them.

## Non-interactive pivot

**If you are a non-interactive agent — a subprocess-invoked run, a scheduled job, a Codex `exec` session, a Claude `-p --no-session-persistence` session, or any other single-shot automation — your prompt is the contract. Stop reading here. Only the sections above (public vs private files, style, behavioral defaults, scope control) apply to you. Everything below this pivot applies only to interactive repo-development work where a human is in the loop.**

---

## Repo context

This is an open-source repository for an agent-assisted observation workflow. Product identity and regeneration inputs live in `.arkitype/`; durable project documentation lives in `.knowledge/`; active plans, detailed plan files, projects, processes, routines, roadmap, and operational knowledge live in `.manage/`. The implementation combines deterministic Python under `scripts/`, agent skills under `.agents/skills/`, tests under `tests/`, and gitignored per-user state such as `profile/`, `tracks/<your-track>/`, `artifacts/`, and `logs/`.

Use this skill for **repo development**: changing shared code, tests, skills, scripts, or docs. Do not treat every task like a generic Python edit; first identify which subsystem you are touching and preserve the existing architecture and mode boundaries described in the repo docs.

## Read before editing

Before making non-trivial changes, read the smallest relevant set of canonical references for the subsystem you are touching:

- `AGENTS.md` for mode routing and repo-level rules
- `.arkitype/00-arkitype.md` for product identity and scope
- `.arkitype/03-software.md` for software components, contracts, and boundaries
- `.knowledge/README.md` for the documentation index and `.knowledge/architecture.md` for the high-level system map
- `.manage/README.md` for the work-management schema, then the relevant `.manage/{1.plans,2.projects,3.processes,4.routines,5.roadmap,6.knowledge}.md` sections
- `CONTRIBUTING.md` for contributor workflow and placement rules

When relevant, also read:

- `shared/discovery_modes.md` if the task touches discovery behavior or provider capabilities
- `.knowledge/contributing/adding-sources.md` if the task adds or changes a discovery source
- the relevant skill under `.agents/skills/<skill>/SKILL.md` if the task touches agent behavior
- existing tests and fixtures in `tests/` for the subsystem you are changing

Do not read the entire repo by default for tiny localized edits. Read enough to understand the affected subsystem and avoid breaking architectural boundaries.

## Code understanding
When explaining code, prefer call diagrams and (if relevant) state diagrams.

## Planning and handoff

For non-trivial repository work, add or update one bounded item in `.manage/2.projects.md`; keep forward-looking work in `.manage/1.plans.md`, detailed plan documents in `.manage/plans/`, and sequencing in `.manage/5.roadmap.md`. Pair each implementation step with a concrete verification check. Follow `.manage/README.md` rather than creating a parallel plan hierarchy. Tiny single-step edits and docs-only answers may skip a work item.

Owner requirements:
- Include the current agent/provider name.
- Include a concrete resumable agent id when the runtime exposes one.
- Check common runtime variables first, especially `$CODEX_THREAD_ID` for Codex sessions. A safe shell check is: `printf '%s\n' "${CODEX_THREAD_ID:-unknown}"`.
- For local Claude Code sessions, read `$CLAUDE_SESSION_ID` by running `echo $CLAUDE_SESSION_ID` (or the safer `printf '%s\n' "${CLAUDE_SESSION_ID:-unknown}"`).
- For Claude Code cloud sessions, check `$CLAUDE_CODE_REMOTE_SESSION_ID`. A safe shell check is: `printf '%s\n' "${CLAUDE_CODE_REMOTE_SESSION_ID:-unknown}"`. `$CLAUDECODE=1` only means the shell was spawned by Claude Code; it is not a resumable session id.
- If no resumable id is available, write `agent_id: unknown` rather than omitting the field.

Progress tracking rules:
- Keep the active `.manage/2.projects.md` item current after milestones, test runs, blockers, or scope changes.
- Before ending, record files changed, verification, next step, unresolved risks, and whether `scripts/test.sh` passed.
- If resuming work, read `.manage/README.md` and the relevant active project first instead of reconstructing state from chat.
- When work completes, mark the project `done` and update `.manage/5.roadmap.md` if it references the project.
- Record durable technical decisions or findings in `.manage/6.knowledge.md`; do not bury them in transient handoff prose.

## Skill mirroring
- Canonical skill files live in `.agents/skills/`.
- After changing any skill, run `bash scripts/sync_claude_skills.sh` to refresh the generated mirrors in `.claude/skills/`.
- Never edit `.claude/skills/` directly unless explicitly asked.
- Before finishing any skill change, run `bash scripts/sync_claude_skills.sh --check`.

## Testing and verification
- Use the repo-local Python virtualenv at `./.venv` for Python tests and helper scripts.
- If `./.venv` is missing, bootstrap it with `bash scripts/bootstrap_venv.sh` before running Python test commands.
- Prefer `./.venv/bin/python -m pytest ...` over bare `pytest` or `python3 -m pytest`.
- When changing behavior or fixing a bug, add or update tests where reasonable.
- Prefer behavioral tests or consumer-level checks over prose-locking tests.
- Do not add tests that merely assert literal strings in docs, `AGENTS.md`, or skill files unless some script, parser, generator, or harness depends on that exact text.
- For docs-only or instruction-only changes, verification may be limited to manual review, mirror sync, and targeted checks of consuming code or generated artifacts.
- Avoid brittle tests that lock down non-semantic wording.
- Do not force TDD for trivial refactors, config changes, or docs-only edits.
- Run relevant checks during development when helpful.
- Always run `scripts/test.sh` before finishing, unless the task is explicitly docs-only or the script is not applicable.
- If tests or checks fail, say so clearly and do not present the task as complete.

## Required response contract after code changes
After making changes, always:
1. Explain what changed and why.
2. Report how you verified it.
3. State whether `scripts/test.sh` passed or failed.
4. Mention any remaining caveats or assumptions.
5. Suggest a succinct commit message.
