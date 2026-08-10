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
import re
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

    def organized(self, slug: str, date: str) -> dict[str, Any] | None:
        return self._read_json(
            self.root / "artifacts" / "organized" / slug / f"{date}.json"
        )

    def trends(self, slug: str, date: str) -> dict[str, Any] | None:
        return self._read_json(
            self.root / "artifacts" / "trends" / slug / f"{date}.json"
        )

    def ranked_audience(self, slug: str, audience: str, date: str) -> dict[str, Any] | None:
        return self._read_json(
            self.root / "artifacts" / "ranked_audience" / slug / audience / f"{date}.json"
        )

    def audiences_for(self, slug: str, date: str) -> list[str]:
        base = self.root / "artifacts" / "ranked_audience" / slug
        if not base.is_dir():
            return []
        out: list[str] = []
        for sub in sorted(base.iterdir()):
            if sub.is_dir() and (sub / f"{date}.json").is_file():
                out.append(sub.name)
        return out

    def organized_dates(self, slug: str) -> list[str]:
        return self._list_dated_json(self.root / "artifacts" / "organized" / slug)

    def trends_dates(self, slug: str) -> list[str]:
        return self._list_dated_json(self.root / "artifacts" / "trends" / slug)

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

/* Feed */
.feed-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.feed-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.feed-card .thumb {
  width: 100%;
  aspect-ratio: 1.91 / 1;
  background: linear-gradient(135deg, #dcdcdc 0%, #b8b8b8 100%);
  background-size: cover;
  background-position: center;
  display: block;
  border-bottom: 1px solid var(--border);
}
@media (prefers-color-scheme: dark) {
  .feed-card .thumb {
    background: linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%);
  }
}
.feed-card .thumb.placeholder::before {
  content: attr(data-initials);
  display: flex;
  height: 100%;
  align-items: center;
  justify-content: center;
  font-size: 42px;
  font-weight: 600;
  color: rgba(255,255,255,0.6);
  letter-spacing: 2px;
}
.feed-card .body { padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
.feed-card .body .title { font-weight: 600; font-size: 15px; line-height: 1.35; }
.feed-card .body .title a { color: inherit; text-decoration: none; }
.feed-card .body .title a:hover { text-decoration: underline; }
.feed-card .body .desc { color: var(--muted); font-size: 13px; line-height: 1.5; }
.feed-card .body .meta-row { color: var(--muted); font-size: 12px; margin-top: auto; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }

/* Trends */
.bar-row { display: flex; align-items: center; gap: 10px; margin: 4px 0; font-size: 13px; }
.bar-row .label { flex: 0 0 200px; color: var(--fg); }
.bar-row .bar { flex: 1; height: 14px; background: var(--code-bg); border-radius: 3px; overflow: hidden; }
.bar-row .bar > span { display: block; height: 100%; background: var(--accent); }
.bar-row .count { flex: 0 0 44px; text-align: right; color: var(--muted); }
.velocity-up { color: #16a34a; }
.velocity-down { color: #b91c1c; }
.velocity-flat { color: var(--muted); }
.kw-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
.kw-cloud .kw { background: var(--code-bg); border-radius: 12px; padding: 2px 10px; font-size: 13px; }

/* Report */
.report-hero { padding: 4px 0 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
.report-hero h1 { font-size: 30px; margin: 0 0 4px 0; }
.report-hero .sub { color: var(--muted); font-size: 14px; }
.report-hero .quick-links { margin-top: 6px; }
.report-hero .quick-links a { margin-right: 10px; font-size: 13px; }
.exec-summary {
  background: var(--card);
  border-left: 3px solid var(--accent);
  padding: 12px 16px;
  border-radius: 0 6px 6px 0;
  margin: 12px 0;
  font-size: 15px;
}
.stats-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  background: var(--code-bg);
  padding: 10px 14px;
  border-radius: 6px;
  margin: 12px 0 20px 0;
  font-size: 13px;
}
.stats-strip .stat { display: flex; flex-direction: column; }
.stats-strip .stat .num { font-size: 22px; font-weight: 600; color: var(--fg); line-height: 1.1; }
.stats-strip .stat .lbl { color: var(--muted); font-size: 12px; }
.pillrow { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.pillrow .pill {
  background: var(--code-bg);
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 13px;
  color: var(--fg);
}
.pillrow .pill .n { color: var(--muted); margin-left: 4px; }
.report-section { margin-top: 32px; }
.report-section .section-head {
  display: flex; align-items: baseline; gap: 10px; margin-bottom: 8px;
  border-bottom: 1px solid var(--border); padding-bottom: 4px;
}
.report-section .section-head h2 { margin: 0; border: 0; padding: 0; }
.report-section .section-head .count { color: var(--muted); font-size: 14px; }
.feed-card .why { font-size: 12.5px; color: var(--muted); margin-top: 4px; padding-left: 16px; }
.feed-card .why li { margin: 2px 0; }
@media print {
  nav.crumbs, .quick-links, details, .report-hero .quick-links { display: none; }
  body { background: white; color: black; }
  .card, .feed-card, .stats-strip { background: white; border-color: #ccc; }
  a { color: black; text-decoration: none; }
}
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
    extra_links: list[str] = []
    if t.ranked_jobs:
        extra_links.append(f'<a href="/track/{_e(slug)}/ranked">Ranked overview</a>')
    organized_dates = model.organized_dates(slug)
    if organized_dates:
        latest_org = organized_dates[0]
        extra_links.append(f'<a href="/track/{_e(slug)}/feed/{_e(latest_org)}">Feed</a>')
    trends_dates = model.trends_dates(slug)
    if trends_dates:
        latest_tr = trends_dates[0]
        extra_links.append(f'<a href="/track/{_e(slug)}/trends/{_e(latest_tr)}">Trends</a>')
    ranked_link = "".join(f" &middot; {l}" for l in extra_links)
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


def _initials(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text or "")
    if not words:
        return "??"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _feed_card(item: dict, enrichment: dict) -> str:
    url = item.get("url", "")
    title = enrichment.get("og_title") or item.get("title", "") or "(untitled)"
    desc = enrichment.get("og_description") or item.get("rationale", "") or ""
    site = enrichment.get("og_site_name") or item.get("source_id", "")
    img = enrichment.get("og_image") or ""
    topic = item.get("topic", "")
    ctype = item.get("content_type", "")
    audiences = item.get("audiences") or []
    if img:
        thumb = f'<a class="thumb" href="{_e(url)}" style="background-image: url(\'{_e(img)}\');"></a>'
    else:
        thumb = (
            f'<a class="thumb placeholder" href="{_e(url)}" '
            f'data-initials="{_e(_initials(site or title))}"></a>'
        )
    aud_badges = " ".join(f'<span class="badge">{_e(a)}</span>' for a in audiences)
    return (
        f'<article class="feed-card">'
        f"{thumb}"
        f'<div class="body">'
        f'<div class="title"><a href="{_e(url)}">{_e(title)}</a></div>'
        + (f'<div class="desc">{_e(desc[:220])}</div>' if desc else "")
        + f'<div class="meta-row">'
          f'<span class="badge">{_e(topic)}</span>'
          f'<span class="badge">{_e(ctype)}</span>'
          f"{aud_badges}"
          f'<span>{_e(site)}</span>'
        f"</div>"
        f"</div>"
        f"</article>"
    )


def _lookup_enrichment(discovery: dict | None) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    if not discovery:
        return lookup
    for source in discovery.get("sources", []):
        for cand in source.get("candidates", []):
            url = cand.get("url") or ""
            if url and "enrichment" in cand:
                lookup[url] = cand["enrichment"] or {}
    return lookup


def render_feed(model: Model, slug: str, date: str) -> str:
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    crumbs = [
        ("Home", "/"),
        (t.display_name, f"/track/{slug}/"),
        (f"Feed {date}", ""),
    ]
    organized = model.organized(slug, date)
    if not organized:
        body = (
            f"<h1>{_e(t.display_name)} — Feed {_e(date)}</h1>"
            '<p class="section-empty">No organized artifact for this date.</p>'
        )
        return _page(f"{t.display_name} feed {date}", crumbs, body)
    enrichment_map = _lookup_enrichment(model.discovery(slug, date))
    items = organized.get("items", [])
    by_topic: dict[str, list[dict]] = {}
    for it in items:
        by_topic.setdefault(it.get("topic", "other"), []).append(it)
    topic_order = sorted(by_topic.keys(), key=lambda k: -len(by_topic[k]))
    parts: list[str] = [
        f"<h1>{_e(t.display_name)} — Feed <span class=\"meta\">{_e(date)}</span></h1>",
        f'<p class="meta">{len(items)} items across {len(by_topic)} topic(s). '
        f'Grouped by topic; card image comes from the destination page&apos;s OpenGraph metadata when available.</p>',
    ]
    for topic in topic_order:
        topic_items = by_topic[topic]
        parts.append(f'<h2>{_e(topic)} <span class="meta">({len(topic_items)})</span></h2>')
        parts.append('<div class="feed-grid">')
        for it in topic_items:
            enr = enrichment_map.get(it.get("url", ""), {})
            parts.append(_feed_card(it, enr))
        parts.append("</div>")
    return _page(f"{t.display_name} feed {date}", crumbs, "".join(parts))


def _bar_row(label: str, count: int, total: int) -> str:
    pct = int((count / total) * 100) if total > 0 else 0
    return (
        f'<div class="bar-row"><div class="label">{_e(label)}</div>'
        f'<div class="bar"><span style="width: {pct}%"></span></div>'
        f'<div class="count">{count}</div></div>'
    )


def render_trends(model: Model, slug: str, date: str) -> str:
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    crumbs = [
        ("Home", "/"),
        (t.display_name, f"/track/{slug}/"),
        (f"Trends {date}", ""),
    ]
    trends = model.trends(slug, date)
    if not trends:
        body = (
            f"<h1>{_e(t.display_name)} — Trends {_e(date)}</h1>"
            '<p class="section-empty">No trend report for this date.</p>'
        )
        return _page(f"{t.display_name} trends {date}", crumbs, body)
    total = trends.get("total_items", 0)
    parts: list[str] = [
        f"<h1>{_e(t.display_name)} — Trends <span class=\"meta\">{_e(date)}</span></h1>",
        f'<p class="meta">{total} items surfaced. Generated {_e(trends.get("generated_at", ""))}.</p>',
    ]

    def _section(title: str, rows: list[dict], label_key: str, count_key: str = "count") -> str:
        if not rows:
            return f'<h2>{_e(title)}</h2><p class="section-empty">none</p>'
        max_count = max((r.get(count_key, 0) for r in rows), default=1)
        body = "".join(_bar_row(r.get(label_key, ""), r.get(count_key, 0), max_count) for r in rows)
        return f"<h2>{_e(title)}</h2>{body}"

    parts.append(_section("Items per topic", trends.get("items_per_topic", []), "topic"))
    parts.append(_section("Items per source", trends.get("items_per_source", []), "source_id"))
    parts.append(_section("Items per content type", trends.get("items_per_content_type", []), "content_type"))
    parts.append(_section("Items per audience", trends.get("items_per_audience", []), "audience"))

    vel = trends.get("topic_velocity_vs_previous", [])
    parts.append("<h2>Topic velocity (vs previous day)</h2>")
    if not vel:
        parts.append('<p class="section-empty">no prior-day organized artifact to compare against</p>')
    else:
        rows = []
        for v in vel:
            delta = v.get("delta", 0)
            cls = "velocity-up" if delta > 0 else ("velocity-down" if delta < 0 else "velocity-flat")
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")
            rows.append(f'<tr><td>{_e(v.get("topic", ""))}</td><td class="{cls}">{arrow} {delta:+d}</td></tr>')
        parts.append("<table><tr><th>Topic</th><th>Delta</th></tr>" + "".join(rows) + "</table>")

    cross = trends.get("cross_source_urls", [])
    parts.append("<h2>URLs surfaced by multiple sources</h2>")
    if not cross:
        parts.append('<p class="section-empty">none today</p>')
    else:
        rows = []
        for c in cross:
            u = c.get("url", "")
            rows.append(
                f'<tr><td><a href="{_e(u)}">{_e(u)}</a></td>'
                f'<td>{_e(", ".join(c.get("sources") or []))}</td></tr>'
            )
        parts.append("<table><tr><th>URL</th><th>Sources</th></tr>" + "".join(rows) + "</table>")

    kws = trends.get("top_keywords", [])
    parts.append("<h2>Top title keywords</h2>")
    if not kws:
        parts.append('<p class="section-empty">none</p>')
    else:
        cloud = "".join(
            f'<span class="kw">{_e(k.get("token", ""))} <span class="meta">({k.get("count", 0)})</span></span>'
            for k in kws
        )
        parts.append(f'<div class="kw-cloud">{cloud}</div>')

    return _page(f"{t.display_name} trends {date}", crumbs, "".join(parts))


def _stats_strip(discovery: dict | None, organized: dict | None, trends: dict | None) -> str:
    total_items = len(organized.get("items", [])) if organized else 0
    sources_ok = 0
    sources_total = 0
    if discovery:
        for s in discovery.get("sources", []):
            sources_total += 1
            if s.get("status") == "complete":
                sources_ok += 1
    topics = len({i.get("topic") for i in (organized.get("items", []) if organized else [])})
    cross = len(trends.get("cross_source_urls", [])) if trends else 0
    generated = (trends and trends.get("generated_at")) or (organized and organized.get("generated_at")) or ""
    parts = [
        f'<div class="stat"><span class="num">{total_items}</span><span class="lbl">items</span></div>',
        f'<div class="stat"><span class="num">{sources_ok}/{sources_total}</span><span class="lbl">sources OK</span></div>',
        f'<div class="stat"><span class="num">{topics}</span><span class="lbl">topics</span></div>',
        f'<div class="stat"><span class="num">{cross}</span><span class="lbl">cross-source URLs</span></div>',
    ]
    if generated:
        parts.append(f'<div class="stat"><span class="num">{_e(generated[-9:-1])}</span><span class="lbl">generated (UTC)</span></div>')
    return f'<div class="stats-strip">{"".join(parts)}</div>'


def _topic_pills(trends: dict | None) -> str:
    if not trends:
        return ""
    rows = trends.get("items_per_topic", [])
    if not rows:
        return ""
    pills = "".join(
        f'<span class="pill">{_e(r.get("topic", ""))}<span class="n">{r.get("count", 0)}</span></span>'
        for r in rows
    )
    return f'<div class="pillrow">{pills}</div>'


def _keyword_pills(trends: dict | None, limit: int = 12) -> str:
    if not trends:
        return ""
    rows = trends.get("top_keywords", [])[:limit]
    if not rows:
        return ""
    pills = "".join(
        f'<span class="pill">{_e(r.get("token", ""))}<span class="n">{r.get("count", 0)}</span></span>'
        for r in rows
    )
    return f'<div class="pillrow">{pills}</div>'


def _report_feed_card(item: dict, enrichment: dict, why: list[str] | None = None) -> str:
    card = _feed_card(item, enrichment)
    if not why:
        return card
    why_html = "".join(f"<li>{_e(w)}</li>" for w in why if w)
    return card.replace(
        '</div></article>',
        f'<ul class="why">{why_html}</ul></div></article>',
        1,
    )


def render_report(model: Model, slug: str, date: str, audience: str | None = None) -> str:
    """Consolidated single-page daily report.

    Combines executive summary + trend highlights + feed cards grouped by
    topic (with OG images) + top-matches (with why bullets) + source
    coverage into one publishable document.

    When `audience` is given and a matching artifacts/ranked_audience/
    file exists, the top-matches section is replaced with the top-N
    items ranked for that audience.
    """
    t = model.find_track(slug)
    if not t:
        return _not_found(slug)
    crumbs = [("Home", "/"), (t.display_name, f"/track/{slug}/"), (date, "")]
    digest = model.digest(slug, date)
    discovery = model.discovery(slug, date)
    organized = model.organized(slug, date)
    trends = model.trends(slug, date)
    if not organized:
        return render_run(model, slug, date)
    enrichment_map = _lookup_enrichment(discovery)
    items = organized.get("items", [])
    available_audiences = model.audiences_for(slug, date)

    # Assemble the top-matches list. If an audience is scoped, use the
    # per-audience ranked artifact; otherwise use the digest top_matches.
    top_matches_data: list[dict] = []
    top_urls: set[str] = set()
    audience_topN = 8
    audience_ranked_items: list[dict] = []
    if audience and audience in available_audiences:
        r = model.ranked_audience(slug, audience, date)
        if r:
            audience_ranked_items = r.get("ranked", [])[:audience_topN]
            for it in audience_ranked_items:
                top_urls.add(it.get("url", ""))
    else:
        if digest:
            for run in digest.get("runs", []):
                for m in run.get("top_matches") or []:
                    top_matches_data.append(m)
        top_urls = {m.get("listing_url") for m in top_matches_data}

    header = [
        '<div class="report-hero">',
        f'<h1>{_e(t.display_name)} — Daily Report <span class="meta">{_e(date)}</span></h1>',
    ]
    audience_hint = ""
    if t.persona_rel:
        audience_hint = f' · Persona: <code>{_e(t.persona_rel)}</code>'
    if audience:
        audience_hint += f' · Audience lens: <strong>{_e(audience)}</strong>'
    header.append(
        f'<div class="sub">Track <code>{_e(slug)}</code>'
        f'{audience_hint}</div>'
    )
    # Audience selector links
    if available_audiences:
        link_parts = [
            (
                f'<a href="/track/{_e(slug)}/{_e(date)}">All</a>'
                if audience is not None
                else '<strong>All</strong>'
            )
        ]
        for a in available_audiences:
            if audience == a:
                link_parts.append(f'<strong>{_e(a)}</strong>')
            else:
                link_parts.append(f'<a href="/track/{_e(slug)}/{_e(date)}/audience/{_e(a)}">{_e(a)}</a>')
        header.append(
            f'<div class="sub" style="margin-top:2px;">Audience: '
            f'{" · ".join(link_parts)}</div>'
        )
    header.append(
        '<div class="quick-links">'
        f'<a href="/track/{_e(slug)}/feed/{_e(date)}">Full feed grid</a>'
        f'<a href="/track/{_e(slug)}/trends/{_e(date)}">Trend detail</a>'
        f'<a href="/track/{_e(slug)}/{_e(date)}/details">Structured digest</a>'
        f'<a href="/raw/digests/{_e(slug)}/{_e(date)}.json">Digest JSON</a>'
        '</div>'
    )
    header.append("</div>")

    parts: list[str] = ["".join(header)]

    # Executive summary
    if digest:
        run = (digest.get("runs") or [{}])[0]
        exec_summary = run.get("executive_summary") or ""
        if exec_summary:
            parts.append(f'<div class="exec-summary">{_e(exec_summary)}</div>')

    # Stats strip
    parts.append(_stats_strip(discovery, organized, trends))

    # Trend highlights (topics + top keywords)
    tp = _topic_pills(trends)
    kw = _keyword_pills(trends)
    if tp or kw:
        parts.append('<div class="report-section">')
        parts.append('<div class="section-head"><h2>Trend highlights</h2></div>')
        if tp:
            parts.append('<h3 style="margin-top:8px;">Topics today</h3>')
            parts.append(tp)
        if kw:
            parts.append('<h3>Buzzwords in titles</h3>')
            parts.append(kw)
        cross = trends.get("cross_source_urls", []) if trends else []
        if cross:
            parts.append('<h3>URLs surfaced by multiple sources</h3>')
            crows = "".join(
                f'<li><a href="{_e(c.get("url", ""))}">{_e(c.get("url", ""))}</a> '
                f'<span class="meta">— {_e(", ".join(c.get("sources") or []))}</span></li>'
                for c in cross
            )
            parts.append(f"<ul>{crows}</ul>")
        parts.append('</div>')

    # Top matches
    if audience and audience_ranked_items:
        parts.append('<div class="report-section">')
        parts.append(
            f'<div class="section-head"><h2>Top matches for {_e(audience)}</h2>'
            f'<span class="count">top {len(audience_ranked_items)} ranked for this audience</span></div>'
        )
        parts.append('<div class="feed-grid">')
        for it in audience_ranked_items:
            why = [
                f"audience_score: {it.get('audience_score')}",
                f"rank: {it.get('rank')}",
                f"selected: {'yes' if it.get('selected') else 'no (extrapolated)'}",
                it.get("rationale", ""),
            ]
            parts.append(_report_feed_card(it, enrichment_map.get(it.get("url", ""), {}), why))
        parts.append('</div>')
        parts.append('</div>')
    elif top_matches_data:
        parts.append('<div class="report-section">')
        parts.append(
            f'<div class="section-head"><h2>Top matches</h2>'
            f'<span class="count">{len(top_matches_data)} item(s) picked by the digest ranker</span></div>'
        )
        parts.append('<div class="feed-grid">')
        top_items_by_url = {m.get("listing_url"): m for m in top_matches_data}
        # Prefer organized items so we get topic + audiences + enrichment matched by url
        rendered_urls: set[str] = set()
        for it in items:
            if it.get("url") in top_items_by_url:
                m = top_items_by_url[it["url"]]
                why = m.get("why_match") or []
                parts.append(_report_feed_card(it, enrichment_map.get(it["url"], {}), why))
                rendered_urls.add(it["url"])
        # Fallback: any digest top match without a matching organized item
        for m in top_matches_data:
            if m.get("listing_url") in rendered_urls:
                continue
            pseudo = {
                "url": m.get("listing_url", ""),
                "title": m.get("title", ""),
                "topic": m.get("team_or_domain", ""),
                "content_type": "post",
                "audiences": [],
                "source_id": m.get("source", ""),
            }
            parts.append(_report_feed_card(pseudo, {}, m.get("why_match") or []))
        parts.append('</div>')
        parts.append('</div>')

    # Everything else, grouped by topic
    other_items = [i for i in items if i.get("url") not in top_urls]
    if other_items:
        by_topic: dict[str, list[dict]] = {}
        for it in other_items:
            by_topic.setdefault(it.get("topic", "other"), []).append(it)
        parts.append('<div class="report-section">')
        parts.append(
            f'<div class="section-head"><h2>All items by topic</h2>'
            f'<span class="count">{len(other_items)} additional item(s)</span></div>'
        )
        for topic in sorted(by_topic.keys(), key=lambda k: -len(by_topic[k])):
            group = by_topic[topic]
            parts.append(f'<h3>{_e(topic)} <span class="meta">({len(group)})</span></h3>')
            parts.append('<div class="feed-grid">')
            for it in group:
                parts.append(_feed_card(it, enrichment_map.get(it.get("url", ""), {})))
            parts.append('</div>')
        parts.append('</div>')

    # Source coverage
    if discovery:
        parts.append('<div class="report-section">')
        parts.append('<div class="section-head"><h2>Source coverage</h2></div>')
        parts.append(_render_discovery_block(discovery).replace("<h2>Discovery</h2>", "", 1))
        parts.append('</div>')

    # Raw downloads
    parts.append('<div class="report-section">')
    parts.append('<div class="section-head"><h2>Raw artifacts</h2></div>')
    raw_links = []
    for kind, label in [
        ("digests", "Digest JSON"),
        ("discovery", "Discovery JSON"),
        ("organized", "Organized JSON"),
        ("trends", "Trends JSON"),
    ]:
        if model.raw_path(kind, slug, date):
            raw_links.append(
                f'<li><a href="/raw/{_e(kind)}/{_e(slug)}/{_e(date)}.json">{_e(label)}</a></li>'
            )
    if raw_links:
        parts.append(f"<ul>{''.join(raw_links)}</ul>")
    parts.append('</div>')

    return _page(f"{t.display_name} report {date}", crumbs, "".join(parts))


def rewrite_urls_for_static(html_text: str) -> str:
    """Rewrite root-anchored / URLs to relative paths for static output."""
    return html_text
