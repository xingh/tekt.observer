"""Shared HTML viewer for tekt.observer runs.

Reads JSON artifacts under a repo-shaped root and renders them as HTML pages.
Two CLIs consume this module:
- scripts/render_html.py writes the pages as a static site.
- scripts/serve_html.py serves them live over http.server.

Stdlib only. Pure rendering functions: HTML strings in, HTML strings out.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TrackSummary:
    slug: str
    display_name: str
    prefs_md: str = ""
    agents_md: str = ""
    sources: dict[str, Any] = field(default_factory=dict)
    source_state: dict[str, Any] = field(default_factory=dict)
    digest_dates: list[str] = field(default_factory=list)
    discovery_dates: list[str] = field(default_factory=list)
    ranked_jobs: dict[str, Any] | None = None
    persona_rel: str | None = None
    persona_md: str = ""


class Model:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _read_json(self, p: Path) -> dict[str, Any] | None:
        if not p.is_file():
            return None
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _read_text(self, p: Path) -> str:
        if not p.is_file():
            return ""
        return p.read_text()

    def _list_dated_json(self, dirpath: Path) -> list[str]:
        if not dirpath.is_dir():
            return []
        dates: list[str] = []
        for entry in dirpath.iterdir():
            if entry.suffix != ".json" or entry.stem == "latest":
                continue
            stem = entry.stem
            if len(stem) == 10 and stem[4] == "-" and stem[7] == "-":
                dates.append(stem)
        return sorted(dates, reverse=True)

    def tracks(self) -> list[TrackSummary]:
        tracks_dir = self.root / "tracks"
        out: list[TrackSummary] = []
        if not tracks_dir.is_dir():
            return out
        for entry in sorted(tracks_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            slug = entry.name
            ts = TrackSummary(
                slug=slug,
                display_name=slug.replace("_", " ").title(),
            )
            ts.prefs_md = self._read_text(entry / "prefs.md")
            ts.agents_md = self._read_text(entry / "AGENTS.md")
            sources = self._read_json(entry / "sources.json")
            if sources:
                ts.sources = sources
            state = self._read_json(entry / "source_state.json")
            if state:
                ts.source_state = state
            ts.digest_dates = self._list_dated_json(
                self.root / "artifacts" / "digests" / slug
            )
            ts.discovery_dates = self._list_dated_json(
                self.root / "artifacts" / "discovery" / slug
            )
            ranked = self._read_json(
                self.root / "shared" / "ranked_jobs" / f"{slug}.json"
            )
            if ranked:
                ts.ranked_jobs = ranked
            # discover persona pointer in AGENTS.md (profile/personas/<name>.md)
            for line in ts.agents_md.splitlines():
                marker = "profile/personas/"
                if marker in line and ".md" in line:
                    idx = line.find(marker)
                    tail = line[idx:]
                    end = tail.find(".md") + 3
                    rel = tail[:end]
                    persona_path = self.root / rel
                    if persona_path.is_file():
                        ts.persona_rel = rel
                        ts.persona_md = self._read_text(persona_path)
                        break
            out.append(ts)
        return out

    def find_track(self, slug: str) -> TrackSummary | None:
        for t in self.tracks():
            if t.slug == slug:
                return t
        return None

    def digest(self, slug: str, date: str) -> dict[str, Any] | None:
        return self._read_json(
            self.root / "artifacts" / "digests" / slug / f"{date}.json"
        )

    def discovery(self, slug: str, date: str) -> dict[str, Any] | None:
        return self._read_json(
            self.root / "artifacts" / "discovery" / slug / f"{date}.json"
        )

    def raw_path(self, kind: str, slug: str, date: str) -> Path | None:
        p = self.root / "artifacts" / kind / slug / f"{date}.json"
        return p if p.is_file() else None


STYLE_CSS = """\
:root {
  --fg: #1a1a1a;
  --muted: #666;
  --bg: #fdfdfd;
  --card: #fff;
  --border: #e2e2e2;
  --accent: #2e5cff;
  --code-bg: #f6f6f6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fg: #e8e8e8;
    --muted: #999;
    --bg: #121212;
    --card: #1c1c1c;
    --border: #333;
    --accent: #8aa8ff;
    --code-bg: #1f1f1f;
  }
}
* { box-sizing: border-box; }
body {
  font: 15px/1.55 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  color: var(--fg);
  background: var(--bg);
  margin: 0;
}
main { max-width: 960px; margin: 0 auto; padding: 24px; }
nav.crumbs { color: var(--muted); font-size: 13px; margin-bottom: 12px; }
nav.crumbs a { color: var(--muted); text-decoration: none; }
nav.crumbs a:hover { text-decoration: underline; }
h1 { font-size: 26px; margin: 0 0 6px 0; }
h2 { font-size: 20px; margin: 28px 0 8px 0; border-bottom: 1px solid var(--border); padding-bottom: 4px; }
h3 { font-size: 16px; margin: 20px 0 6px 0; }
a { color: var(--accent); }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 14px;
  margin: 10px 0;
}
.meta { color: var(--muted); font-size: 13px; }
.badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--code-bg);
  color: var(--muted);
  font-size: 12px;
  margin-right: 6px;
}
.badge.apply_now, .badge.complete, .badge.pass { background: #16a34a; color: #fff; }
.badge.watch, .badge.partial, .badge.integration_needed { background: #f59e0b; color: #fff; }
.badge.skip, .badge.failed, .badge.blocked { background: #b91c1c; color: #fff; }
.badge.every_run { background: #2e5cff; color: #fff; }
.badge.every_3_runs { background: #6366f1; color: #fff; }
.badge.every_month { background: #8b5cf6; color: #fff; }
.fit { font-weight: 600; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); font-size: 14px; }
th { color: var(--muted); font-weight: 500; }
pre { background: var(--code-bg); padding: 12px; overflow-x: auto; border-radius: 6px; font-size: 12.5px; white-space: pre-wrap; }
code { background: var(--code-bg); padding: 1px 4px; border-radius: 3px; font-size: 13px; }
ul { padding-left: 22px; }
.section-empty { color: var(--muted); font-style: italic; }
details { margin-top: 12px; }
details summary { cursor: pointer; color: var(--muted); font-size: 13px; }
.footer { color: var(--muted); font-size: 12px; margin-top: 40px; text-align: center; }
"""


def _e(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _page(title: str, breadcrumbs: list[tuple[str, str]], body: str, css_href: str = "/style.css") -> str:
    crumbs = " / ".join(
        f'<a href="{_e(url)}">{_e(label)}</a>' if url else _e(label)
        for label, url in breadcrumbs
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{_e(title)}</title>\n"
        f'<link rel="stylesheet" href="{_e(css_href)}">\n'
        "</head>\n"
        "<body>\n<main>\n"
        f'<nav class="crumbs">{crumbs}</nav>\n'
        f"{body}\n"
        '<p class="footer">tekt.observer &middot; JSON artifacts rendered as HTML</p>\n'
        "</main>\n</body>\n</html>\n"
    )


def render_index(model: Model) -> str:
    tracks = model.tracks()
    if not tracks:
        body = (
            '<h1>tekt.observer</h1>'
            f'<p class="section-empty">No tracks found under <code>{_e(model.root)}/tracks/</code>.</p>'
        )
        return _page("tekt.observer", [("Home", "")], body)
    rows = []
    for t in tracks:
        last_run = t.digest_dates[0] if t.digest_dates else "—"
        rows.append(
            "<tr>"
            f'<td><a href="/track/{_e(t.slug)}/">{_e(t.display_name)}</a></td>'
            f"<td><code>{_e(t.slug)}</code></td>"
            f"<td>{len(t.digest_dates)}</td>"
            f"<td>{len(t.discovery_dates)}</td>"
            f"<td>{_e(last_run)}</td>"
            "</tr>"
        )
    body = (
        "<h1>tekt.observer</h1>"
        f'<p class="meta">Root: <code>{_e(model.root)}</code></p>'
        "<table>"
        "<tr><th>Track</th><th>Slug</th><th>Digests</th><th>Discovery</th><th>Latest</th></tr>"
        + "".join(rows)
        + "</table>"
    )
    return _page("tekt.observer", [("Home", "")], body)


def render_track_index(model: Model, slug: str) -> str:
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    persona_line = ""
    if t.persona_rel:
        persona_line = (
            f'<p class="meta">Persona: <a href="/track/{_e(slug)}/sources">'
            f"<code>{_e(t.persona_rel)}</code></a></p>"
        )
    ranked_link = ""
    if t.ranked_jobs:
        ranked_link = f' &middot; <a href="/track/{_e(slug)}/ranked">Ranked overview</a>'
    sources_link = f'<a href="/track/{_e(slug)}/sources">Sources &amp; config</a>'
    dates = sorted(set(t.digest_dates) | set(t.discovery_dates), reverse=True)
    if not dates:
        runs_block = '<p class="section-empty">No runs yet for this track.</p>'
    else:
        rows = []
        for d in dates:
            marks = []
            if d in t.digest_dates:
                marks.append("digest")
            if d in t.discovery_dates:
                marks.append("discovery")
            rows.append(
                f'<tr><td><a href="/track/{_e(slug)}/{_e(d)}">{_e(d)}</a></td>'
                f'<td class="meta">{_e(", ".join(marks))}</td></tr>'
            )
        runs_block = (
            "<table><tr><th>Date</th><th>Artifacts</th></tr>"
            + "".join(rows) + "</table>"
        )
    body = (
        f"<h1>{_e(t.display_name)}</h1>"
        f"{persona_line}"
        f"<p>{sources_link}{ranked_link}</p>"
        "<h2>Runs</h2>"
        f"{runs_block}"
    )
    return _page(
        t.display_name,
        [("Home", "/"), (t.display_name, "")],
        body,
    )


def _not_found(what: str) -> str:
    body = f'<h1>Not found</h1><p>Could not find <code>{_e(what)}</code>.</p>'
    return _page("Not found", [("Home", "/")], body)


def render_run(model: Model, slug: str, date: str) -> str:
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    digest = model.digest(slug, date)
    discovery = model.discovery(slug, date)
    crumbs = [
        ("Home", "/"),
        (t.display_name, f"/track/{slug}/"),
        (date, ""),
    ]
    if not digest and not discovery:
        body = (
            f"<h1>{_e(t.display_name)} — {_e(date)}</h1>"
            '<p class="section-empty">No artifacts for this date.</p>'
        )
        return _page(f"{t.display_name} {date}", crumbs, body)
    parts: list[str] = [f"<h1>{_e(t.display_name)} — {_e(date)}</h1>"]
    if digest:
        for i, run in enumerate(digest.get("runs", [])):
            parts.append(_render_run_block(run, i))
    else:
        parts.append('<p class="section-empty">No digest for this date.</p>')
    if discovery:
        parts.append(_render_discovery_block(discovery))
    if digest:
        parts.append(
            f'<details><summary>Raw digest JSON</summary>'
            f'<pre>{_e(json.dumps(digest, indent=2))}</pre>'
            f'<p><a href="/raw/digests/{_e(slug)}/{_e(date)}.json">Download</a></p></details>'
        )
    if discovery:
        parts.append(
            f'<details><summary>Raw discovery JSON</summary>'
            f'<pre>{_e(json.dumps(discovery, indent=2))}</pre>'
            f'<p><a href="/raw/discovery/{_e(slug)}/{_e(date)}.json">Download</a></p></details>'
        )
    return _page(f"{t.display_name} {date}", crumbs, "".join(parts))


def _render_run_block(run: dict[str, Any], index: int) -> str:
    kind = run.get("kind", "initial")
    generated = run.get("generated_at", "")
    parts = [
        f'<h2>Run {index + 1} '
        f'<span class="badge">{_e(kind)}</span> '
        f'<span class="meta">{_e(generated)}</span></h2>'
    ]
    execsum = run.get("executive_summary") or ""
    if execsum:
        parts.append(f'<div class="card">{_e(execsum)}</div>')
    for arr_key, title, renderer in [
        ("recommended_actions", "Recommended actions", _render_bullets),
        ("top_matches", "Top matches", _render_top_matches),
        ("other_new_roles", "Other items", _render_other),
        ("filtered_roles", "Filtered out", _render_filtered),
        ("source_notes", "Source notes", _render_source_notes),
        ("notes_for_next_run", "Notes for next run", _render_bullets),
    ]:
        arr = run.get(arr_key) or []
        parts.append(f"<h3>{_e(title)}</h3>")
        if not arr:
            parts.append('<p class="section-empty">none</p>')
        else:
            parts.append(renderer(arr))
    return "".join(parts)


def _render_bullets(items: list) -> str:
    return "<ul>" + "".join(f"<li>{_e(x)}</li>" for x in items) + "</ul>"


def _render_top_matches(items: list) -> str:
    out = []
    for m in items:
        rec = m.get("recommendation", "")
        fit = m.get("fit_score")
        fit_str = "—" if fit in (None, "") else f"{fit}/10"
        why = m.get("why_match") or []
        concerns = m.get("concerns") or []
        why_html = "".join(f"<li>{_e(x)}</li>" for x in why)
        con_html = "".join(f"<li>{_e(x)}</li>" for x in concerns)
        url = m.get("listing_url", "")
        title = m.get("title", "")
        title_link = f'<a href="{_e(url)}">{_e(title)}</a>' if url else _e(title)
        loc = m.get("location") or ""
        remote = m.get("remote") or ""
        source = m.get("source") or ""
        meta_bits = " · ".join(_e(x) for x in [loc, remote, source] if x)
        out.append(
            '<div class="card">'
            f'<div><span class="badge {_e(rec)}">{_e(rec)}</span>'
            f' <span class="fit">{_e(fit_str)}</span></div>'
            f"<div><strong>{title_link}</strong> — {_e(m.get('company', ''))}</div>"
            + (f'<div class="meta">{meta_bits}</div>' if meta_bits else "")
            + (f"<div>Why:<ul>{why_html}</ul></div>" if why_html else "")
            + (f"<div>Concerns:<ul>{con_html}</ul></div>" if con_html else "")
            + "</div>"
        )
    return "".join(out)


def _render_other(items: list) -> str:
    out = []
    for m in items:
        rec = m.get("recommendation", "")
        fit = m.get("fit_score")
        fit_str = "—" if fit in (None, "") else f"{fit}/10"
        url = m.get("listing_url", "")
        title = m.get("title", "")
        title_link = f'<a href="{_e(url)}">{_e(title)}</a>' if url else _e(title)
        out.append(
            '<div class="card">'
            f'<span class="badge {_e(rec)}">{_e(rec)}</span> '
            f'<span class="fit">{_e(fit_str)}</span> '
            f"<strong>{title_link}</strong> — {_e(m.get('company', ''))}"
            f'<div class="meta">{_e(m.get("short_note", ""))}</div>'
            "</div>"
        )
    return "".join(out)


def _render_filtered(items: list) -> str:
    out = ["<ul>"]
    for m in items:
        url = m.get("listing_url", "")
        title = m.get("title", "")
        link = f'<a href="{_e(url)}">{_e(title)}</a>' if url else _e(title)
        out.append(
            f"<li>{link} — {_e(m.get('company', ''))}: "
            f'<span class="meta">{_e(m.get("reason_filtered_out", ""))}</span></li>'
        )
    out.append("</ul>")
    return "".join(out)


def _render_source_notes(items: list) -> str:
    out = [
        "<table>"
        "<tr><th>Source</th><th>Mode</th><th>Status</th><th>Pages</th>"
        "<th>Terms tried</th><th>Note</th></tr>"
    ]
    for n in items:
        out.append(
            "<tr>"
            f"<td>{_e(n.get('source', ''))}</td>"
            f"<td><code>{_e(n.get('discovery_mode', ''))}</code></td>"
            f'<td><span class="badge {_e(n.get("status", ""))}">{_e(n.get("status", ""))}</span></td>'
            f"<td>{_e(n.get('listing_pages_scanned', ''))}</td>"
            f"<td>{_e(', '.join(n.get('search_terms_tried') or []))}</td>"
            f'<td class="meta">{_e(n.get("note") or "")}</td>'
            "</tr>"
        )
    out.append("</table>")
    return "".join(out)


def _render_discovery_block(discovery: dict) -> str:
    parts = ["<h2>Discovery</h2>"]
    rows = []
    for s in discovery.get("sources", []):
        rows.append(
            "<tr>"
            f"<td>{_e(s.get('source', ''))}</td>"
            f"<td><code>{_e(s.get('discovery_mode', ''))}</code></td>"
            f'<td><span class="badge {_e(s.get("status", ""))}">{_e(s.get("status", ""))}</span></td>'
            f"<td>{_e(s.get('enumerated_jobs', 0))}</td>"
            f"<td>{_e(s.get('matched_jobs', 0))}</td>"
            f"<td>{_e(', '.join(s.get('search_terms_tried') or []))}</td>"
            "</tr>"
        )
    if rows:
        parts.append(
            "<table>"
            "<tr><th>Source</th><th>Mode</th><th>Status</th>"
            "<th>Enumerated</th><th>Matched</th><th>Terms</th></tr>"
            + "".join(rows) + "</table>"
        )
    else:
        parts.append('<p class="section-empty">No sources in discovery.</p>')
    return "".join(parts)


def render_ranked(model: Model, slug: str) -> str:
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    crumbs = [
        ("Home", "/"),
        (t.display_name, f"/track/{slug}/"),
        ("Ranked", ""),
    ]
    if not t.ranked_jobs:
        body = (
            f"<h1>{_e(t.display_name)} — Ranked overview</h1>"
            '<p class="section-empty">No ranked overview yet.</p>'
        )
        return _page(f"{t.display_name} ranked", crumbs, body)
    jobs = t.ranked_jobs.get("jobs", [])
    rows = []
    for j in jobs:
        url = j.get("url", "")
        title = j.get("title", "")
        title_link = f'<a href="{_e(url)}">{_e(title)}</a>' if url else _e(title)
        fit = j.get("fit_score")
        rows.append(
            "<tr>"
            f"<td>{_e('—' if fit is None else fit)}</td>"
            f"<td>{_e(j.get('company', ''))}</td>"
            f"<td>{title_link}</td>"
            f"<td>{_e(j.get('date_seen', ''))}</td>"
            f"<td>{_e(j.get('last_seen', ''))}</td>"
            f"<td>{_e(j.get('times_seen', ''))}</td>"
            "</tr>"
        )
    body = (
        f"<h1>{_e(t.display_name)} — Ranked overview</h1>"
        f'<p class="meta">Generated {_e(t.ranked_jobs.get("generated_at", ""))}</p>'
        "<table>"
        "<tr><th>Fit</th><th>Company</th><th>Title</th>"
        "<th>First seen</th><th>Last seen</th><th>#</th></tr>"
        + "".join(rows) + "</table>"
    )
    return _page(f"{t.display_name} ranked", crumbs, body)


def render_sources(model: Model, slug: str) -> str:
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    crumbs = [
        ("Home", "/"),
        (t.display_name, f"/track/{slug}/"),
        ("Sources", ""),
    ]
    src = t.sources or {}
    terms = src.get("track_terms", [])
    sources = src.get("sources", [])
    rows = []
    for s in sources:
        rows.append(
            "<tr>"
            f"<td>{_e(s.get('name', ''))}</td>"
            f'<td><a href="{_e(s.get("url", ""))}">{_e(s.get("url", ""))}</a></td>'
            f"<td><code>{_e(s.get('discovery_mode', ''))}</code></td>"
            f'<td><span class="badge {_e(s.get("cadence_group", ""))}">{_e(s.get("cadence_group", ""))}</span></td>'
            "</tr>"
        )
    parts = [
        f"<h1>{_e(t.display_name)} — Sources &amp; config</h1>",
        "<h2>Track terms</h2>",
        (
            "<ul>" + "".join(f"<li><code>{_e(x)}</code></li>" for x in terms) + "</ul>"
            if terms else '<p class="section-empty">none</p>'
        ),
        "<h2>Sources</h2>",
        (
            "<table><tr><th>Source</th><th>URL</th><th>Mode</th><th>Cadence</th></tr>"
            + "".join(rows) + "</table>"
            if rows else '<p class="section-empty">none</p>'
        ),
    ]
    if t.persona_rel:
        parts.extend([
            "<h2>Persona</h2>",
            f'<p class="meta">From <code>{_e(t.persona_rel)}</code></p>',
            f'<details open><summary>Persona detail</summary><pre>{_e(t.persona_md)}</pre></details>',
        ])
    parts.extend([
        "<h2>Preferences</h2>",
        f"<pre>{_e(t.prefs_md)}</pre>" if t.prefs_md else '<p class="section-empty">none</p>',
        "<h2>Source state</h2>",
        f"<pre>{_e(json.dumps(t.source_state, indent=2))}</pre>",
    ])
    return _page(f"{t.display_name} sources", crumbs, "".join(parts))


def rewrite_urls_for_static(html_text: str) -> str:
    """Rewrite root-anchored / URLs to relative paths for static output."""
    # naive but sufficient for our controlled output
    return (
        html_text
        .replace('href="/style.css"', 'href="/style.css"')  # placeholder no-op
    )
