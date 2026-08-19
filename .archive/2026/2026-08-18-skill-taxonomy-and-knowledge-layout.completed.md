# Skill taxonomy and knowledge layout

```yaml
status: complete
completed: 2026-08-18
```

Renamed the six project skills to `engineering`, `explore-start`,
`explore-discover-sources`, `gather-curate-items`, `organize-filter-items`, and
`understand-prioritize-items`. Updated routing, setup prompts, track templates,
Claude/Gemini enforcement hooks, generated Claude mirrors, contributor guidance,
and tests.

Moved durable documentation from `docs/` to `.knowledge/`, moved detailed plans
to `.manage/plans/`, and established `.archive/<YYYY>/<name>.completed.md` for
completed task and plan documents. Existing local coding-gate installations are
migrated to the engineering-gate commands on the next setup run.

Verification:

- six canonical skills validated with the skill validator
- Claude skill mirror check passed
- focused agent, gate, and machine-setup tests passed
- legacy skill-name and obsolete documentation-path audits passed
- full `scripts/test.sh` result recorded in the final task handoff
