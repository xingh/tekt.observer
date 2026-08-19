# .manage

Work-management layer for this repository. This folder holds plans, projects, processes, routines, and roadmap — the operational state of the work. It is deliberately separate from `.arkitype/`, which holds regeneration inputs, and `.knowledge/`, which holds durable project documentation. Nothing in `.manage/` is required to rebuild the site; everything in it is required to know what we are doing and why.

The same schema is used in every repository in the constellation. Only the contents differ.

## Starting state

Begin flat. Create these six markdown files and nothing else:

```
.manage/
  README.md          (this file)
  1.plans.md
  2.projects.md
  3.processes.md
  4.routines.md
  5.roadmap.md
  6.knowledge.md
  plans/             (detailed plan documents linked from 1.plans.md or projects)
```

Each file opens with a YAML frontmatter block and then plain markdown sections, one per item:

```yaml
---
type: projects          # matches the filename
site: <from SITE PROFILE in .arkitype/00>
updated: 2026-07-31
---
```

Item convention inside every file: a `##` heading per item, followed by a small YAML block with at minimum `status` (idea | active | blocked | done) and `updated`, then prose. That is the entire format. Do not add structure speculatively.

What goes where:

- **1.plans.md** — forward-looking intent with a horizon: what we intend to do and roughly when. Longer plan documents live in `.manage/plans/` and are linked from here. A plan graduates into a project when work starts.
- **2.projects.md** — bounded efforts with a definition of done. One `##` section per project.
- **3.processes.md** — repeatable procedures: how a thing is done when it needs doing. No schedule.
- **4.routines.md** — processes bound to a cadence: what runs daily, weekly, monthly, and per release.
- **5.roadmap.md** — the sequenced view across plans and projects; the only file allowed to reference items in the others rather than contain its own.
- **6.knowledge.md** — decisions made, findings, and pointers to data. Append-only in spirit: correct by adding, not rewriting.

## Growth rule: promote file to folder

A file is outgrown when any single item inside it needs more than roughly a screen of content, needs its own attachments, or needs sub-files. When that happens, promote — never restructure:

1. Replace `2.projects.md` with a folder `2.projects/`.
2. Move the old file's frontmatter and any small remaining items into `2.projects/00-index.md`.
3. Give each large item its own file: `2.projects/site-launch.md`, each with the same frontmatter-plus-sections format.
4. If an individual item later outgrows its file, apply the same rule recursively: `2.projects/site-launch/00-index.md`.

The promotion is invisible to a reader who starts at the index: the name is identical, the index summarizes what the flat file used to contain, and links point down. Never mix: a category is either a file or a folder, not both.

## Archiving

When a task or detailed plan is complete, move it out of `.manage/` into the repository-level `.archive/<YYYY>/` folder and rename it with a `.completed.md` suffix:

```
.archive/2026/2026-08-18-site-launch.completed.md
```

Use the completion year for `<YYYY>`. Preserve the original date and descriptive stem when one exists. Set the document status to `complete` or `done`, update inbound links, and remove its active section or link from `.manage/`. Archived files are historical records; correct them only to repair a broken reference or factual error.

## Rules

1. Flat until it hurts. The promotion rule is the only way structure is added, except for the established `.manage/plans/` collection; no empty folders or speculative folders.
2. One home per item. An item lives in exactly one file; the roadmap references, it never duplicates.
3. Same schema everywhere. Every constellation repo uses these six categories with these names and numbers. If a repo needs a seventh category, that is a constellation-level decision — record it here in every repo or not at all.
4. Agents read the index first. Any agent working in this repo reads this README, then the frontmatter of each top-level file or `00-index.md`, before acting. Status fields are the source of truth for what is active.
5. Degrade loudly. If something doesn't fit the six categories, put it in the nearest one under an `## unsorted` heading rather than inventing a new location silently.
6. Archive completion. Completed task and plan documents do not remain active under `.manage/`; move them to `.archive/<YYYY>/<name>.completed.md`.
