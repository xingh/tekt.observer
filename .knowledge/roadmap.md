# Roadmap

_Last updated: 2026-08-18_

## Conventions

- Statuses: `new`, `in progress`, `complete`, `parked`
- `in progress` means there is active work, a concrete next step, and a linked plan for non-trivial work
- Non-trivial active items should link to a file in `.manage/plans/`
- `parked` items must include a reason and revisit condition
- Keep entries short; move architecture, migration steps, interfaces, and test detail into linked plan docs
- Keep only recent completed items here; archive older ones elsewhere

## Instructions for AI Agents
- AI Agents should only append to fields, not delete any previous text. Exceptions are the fields Last updated and Status, which can be changed. Additionally, items may be moved between Status headers
- If you are instructed to complete multiple action items, or a sufficiently complex action item, do not implement them yourself. Rather, act as an orchestrator that writes the implementation plans and keeps track. Spawn subagents that implement the actual changes detailed in the plan.

Template:
RM-### — Title
- Status:
- Priority:
- Owner:
- Last updated:
- Links:
- Next step:
- Notes:


## New

### RM-019 — Integrate browser-use as a discovery driver and plugin layer
- Status: new
- Priority: M
- Owner: copilot
- Last updated: 2026-08-02
- Links: [plan](../.manage/plans/2026-08-01-browser-use-integration.md)
- Next step: Phase 1 — add `scripts/probe_with_browser_use.py` for source-structure reconnaissance
- Notes: Three phases: (1) browser-use as reconnaissance driver during source setup, feeding CSS selectors into crawl4ai config; (2) optional `browser_use` discovery mode for interactive sources; (3) package tekt.observer as browser-use custom tools. Depends on RM-016 (crawl4ai). Complements RM-018 (`/explore` phase). Research done; findings in `.manage/6.knowledge.md` ("browser-use — research findings"). Closes #11.

### RM-018 — Multi-agent CLI platform with command phases
- Status: new
- Priority: M
- Owner: copilot
- Last updated: 2026-08-12
- Links: [plan](../.manage/plans/2026-08-01-multi-agent-cli-platform.md)
- Next step: Define Phase protocol in `scripts/phases/__init__.py` and scaffold module structure
- Notes: Six command phases (/explore, /seek, /gather, /organize, /understand, /generate) unify the observation pipeline under the `tekt.observer` CLI name; `tekt` is reserved and must not be used as the executable name. GitHub Copilot CLI and Pi CLI integrate as auxiliary tools for specific phases (command generation and reasoning respectively). Existing codex/claude/gemini remain primary providers. Research done; findings in `.manage/6.knowledge.md` ("Multi-agent CLI platform"). Projects defined in `.manage/2.projects.md`. Its overlapping browser-management UI is superseded by RM-020; the phase/CLI work remains in scope.

### RM-020 — Local portfolio management UI
- Status: in progress
- Priority: H
- Owner: Codex
- Last updated: 2026-08-18
- Links: [plan](../.manage/plans/2026-08-18-local-portfolio-ui.md)
- Next step: define the resumable browser-setup protocol or keep explicit agent handoff, then add browser-level coverage
- Notes: Named portfolios, reusable interests, track-local metadata/taxonomy, a unified inbox, curation, and bounded local operations. Local files stay canonical and static output stays read-only. The fresh-checkout path includes three tracked starter workflows, nine offline sample signals, and an optional combined live run. `/manage` now covers live runs, source validation, schedules, and operation polling; setup/source judgment stays routed to interactive agents.

### RM-017 — Package tekt.observer as an installable Claude skills plugin
- Status: new
- Priority: M
- Owner: copilot
- Last updated: 2026-08-01
- Links: [plan](../.manage/plans/2026-08-01-claude-skills-packaging.md)
- Next step: Phase 1 — add `scripts/install_skills.sh` and document in README
- Notes: Two phases: (1) skills-only export via install script, (2) MCP server wrapping `scripts/`. Research done; findings in `.manage/6.knowledge.md` ("Claude skills packaging"). MCP server needs `mcp>=1.0` dep and `pyproject.toml`.

### RM-016 — Integrate crawl4ai for browser-based source discovery
- Status: new
- Priority: M
- Owner: copilot
- Last updated: 2026-08-01
- Links: [plan](../.manage/plans/2026-08-01-crawl4ai-integration.md)
- Next step: Phase 1 — add `crawl4ai_browser` discovery mode (`scripts/discover/sources/crawl4ai_browser.py`)
- Notes: Research done; crawl4ai adds a CSS-selector-based generic browser mode and an opportunity to consolidate cookie-consent boilerplate. LLM extraction deferred. See plan for phases.

## In progress
## Parked

## Completed
### RM-015 — Run source discovery for core\_crypto
- Status: complete
- Priority: M
- Owner: Jonas
- Last updated: 2026-05-14
- Links: [plan](../.manage/plans/2026-05-14-roadmap-new-items.md)
- Next step: none
- Notes: Recommended a compact `core_crypto` source pack: Proton, OpenZeppelin, Aztec Labs, Succinct, Axiom, Brave, Decentriq, and Giesecke+Devrient, with Tools for Humanity / World deferred pending an Ashby board-slug URL-decoding fix. Implementation follow-up on 2026-05-14 added those sources locally, added Tools for Humanity / World after the Ashby fix, and used the reachable official G+D SuccessFactors search URL because the originally recommended marketing careers URL returned HTTP 401 to deterministic discovery.

### RM-014 — Analysis required: Why does the artifact often not include full listing description for Google / Anthropic etc
- Status: complete
- Priority: M
- Owner: Jonas
- Last updated: 2026-05-14
- Links: [plan](../.manage/plans/2026-05-14-roadmap-new-items.md)
- Next step: none
- Notes: The main obstacle is provider output shape: Google and Greenhouse paths use role bodies for matching but do not preserve concise detail snippets in candidate notes; Google also lacks direct-page enrichment and can hit the browser page cap.

### RM-013 — Change codex\_hooks to hooks
- Status: complete
- Priority: M
- Owner: Jonas
- Last updated: 2026-05-14
- Links: [plan](../.manage/plans/2026-05-14-roadmap-new-items.md)
- Next step: none
- Notes: Updated `/home/jvdh/.codex/config.toml` to use `[features].hooks = true`; verified `codex_hooks` no longer appears in that file.

### RM-012 — Telegram delivery for digests
- Status: complete
- Priority: H
- Owner: Jonas
- Last updated: 2026-04-24
- Links: [plan](../.manage/plans/2026-04-23-rm-012-telegram-delivery.md)
- Next step: none
- Notes: Manual runs, scheduled runs, setup guidance, and dry-run previews now support `--delivery telegram` via `scripts/send_digest_telegram.py`, with bot tokens loaded through the existing runtime-secret boundary.

### RM-010 — Add support for main email providers (gmail, fastmail, proton, hotmail)
- Status: complete
- Priority: H
- Owner: Jonas
- Last updated: 2026-04-23
- Links: [plan](../.manage/plans/2026-04-23-rm-010-email-provider-presets.md)
- Next step: none
- Notes: Provider presets now cover Gmail, Fastmail, Outlook.com/Hotmail, and Proton business SMTP on top of the post-`RM-009` runtime model. Proton Mail Bridge remains intentionally out of scope for this preset path.

### RM-009 — Move secrets out of project directory and import at runtime
- Status: complete
- Priority: H
- Owner: Jonas
- Last updated: 2026-04-23
- Links: [plan](../.manage/plans/2026-04-23-rm-009-runtime-secret-loading.md)
- Next step: none
- Notes: The shared runtime secret-loading boundary is in place, `.env.local` now keeps non-secrets plus `JOB_AGENT_SECRETS_FILE`, and plaintext repo-local `JOB_AGENT_SMTP_PASSWORD` is no longer supported.

### RM-011 — Simplify digest email output
- Status: complete
- Priority: H
- Owner: Jonas
- Last updated: 2026-04-23
- Links: [plan](../.manage/plans/2026-04-23-rm-011-email-output-cleanup.md)
- Next step: none
- Notes: The default digest email body now starts at `Executive summary`, the redundant body header/date lines are gone, and the ranked-overview attachment is no longer emitted by default.
