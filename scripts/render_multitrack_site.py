"""Render a multi-track static site with one folder per day per track.

Layout produced:
  <out>/index.html                              — top-level: tracks x dates grid
  <out>/style.css
  <out>/<track>/index.html                       — track landing: dates + links
  <out>/<track>/sources.html                     — sources + persona
  <out>/<track>/<date>/index.html                — daily report
  <out>/<track>/<date>/details.html              — structured digest tables
  <out>/<track>/<date>/feed.html                 — social-feed grid
  <out>/<track>/<date>/trends.html               — trend charts + keyword cloud
  <out>/<track>/<date>/audience/<audience>.html  — per-audience report variant
  <out>/raw/<kind>/<track>/<date>.json           — the raw JSON behind each page

Reuses html_viewer's render functions unchanged; each emitted string carries
root-anchored URLs (/track/..., /style.css, /raw/...). We rewrite those URLs
per output file to point at the reorganised layout.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html_viewer import (  # noqa: E402
    Model,
    STYLE_CSS,
    render_feed,
    render_report,
    render_run,
    render_sources,
    render_trends,
)


_HREF_RE = re.compile(r'(href|src)="(/[^"]*)"')


def _rewrite(html: str, mapper) -> str:
    """Apply a substitution function over every root-anchored href/src."""
    def _sub(match: "re.Match[str]") -> str:
        attr = match.group(1)
        url = match.group(2)
        return f'{attr}="{mapper(url)}"'
    return _HREF_RE.sub(_sub, html)


def _to_out_prefix(depth: int) -> str:
    """`../` × depth so root-anchored URLs resolve back to <out>/."""
    return "" if depth == 0 else "../" * depth


def _translate(url: str, track: str, to_out: str) -> str:
    """Root-anchored URL → new-layout relative URL (from a file at `to_out` prefix)."""
    if url == "/":
        return f"{to_out}index.html"
    if url == "/style.css":
        return f"{to_out}style.css"
    if url == "/index.html":
        return f"{to_out}index.html"

    if url.startswith("/raw/"):
        return f"{to_out}{url[1:]}"

    prefix = f"/track/{track}/"
    if url.startswith(prefix):
        rest = url[len(prefix):]
        # rest can be: "", "sources", "ranked",
        # "<date>", "<date>/details", "<date>/audience/<aud>",
        # "feed/<date>", "trends/<date>"
        if rest == "":
            return f"{to_out}{track}/index.html"
        if rest == "sources":
            return f"{to_out}{track}/sources.html"
        if rest == "ranked":
            return f"{to_out}{track}/ranked.html"
        if rest.startswith("feed/"):
            d = rest[5:]
            return f"{to_out}{track}/{d}/feed.html"
        if rest.startswith("trends/"):
            d = rest[7:]
            return f"{to_out}{track}/{d}/trends.html"
        if "/audience/" in rest:
            d, _, a = rest.partition("/audience/")
            return f"{to_out}{track}/{d}/audience/{a}.html"
        if rest.endswith("/details"):
            d = rest[:-8]
            return f"{to_out}{track}/{d}/details.html"
        # Bare date → date folder index.
        if len(rest) == 10 and rest[4] == "-" and rest[7] == "-":
            return f"{to_out}{track}/{rest}/index.html"
    return url  # unchanged (external or unknown)


def _write(out_dir: Path, rel_path: str, html: str, depth: int, track: str) -> None:
    target = out_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    to_out = _to_out_prefix(depth)
    fixed = _rewrite(html, lambda url: _translate(url, track, to_out))
    target.write_text(fixed)


def _top_index(tracks_info: list[dict]) -> str:
    from html import escape as e
    cards = []
    for info in tracks_info:
        track = info["track"]
        display = info["display"]
        dates = info["dates"]
        audiences = info["audiences"]
        latest = dates[0] if dates else "—"
        date_rows = "".join(
            f'<a class="date-cell" href="./{e(track)}/{e(d)}/index.html">{e(d)}</a>'
            for d in dates
        )
        aud_rows = "".join(
            f'<a class="pill" href="./{e(track)}/{e(latest)}/audience/{e(a)}.html">{e(a)}</a>'
            for a in audiences
        )
        cards.append(f"""
        <div class="track-card">
            <h2><a href="./{e(track)}/index.html">{e(display)}</a></h2>
            <p class="meta">{len(dates)} day(s) · latest {e(latest)}</p>
            <div class="date-grid">{date_rows}</div>
            {'<div class="pillrow">' + aud_rows + '</div>' if aud_rows else ''}
        </div>""")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>tekt.observer — multi-track site</title>
<link rel="stylesheet" href="./style.css">
<style>
.track-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; padding: 18px 20px; margin: 14px 0;
}}
.track-card h2 {{ margin: 0 0 4px 0; font-size: 19px; border: 0; padding: 0; }}
.track-card h2 a {{ color: inherit; text-decoration: none; }}
.track-card h2 a:hover {{ color: var(--accent); }}
.date-grid {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
.date-cell {{
    display: inline-block; padding: 4px 10px; border: 1px solid var(--border);
    border-radius: 4px; color: var(--fg); text-decoration: none; font-size: 13px;
}}
.date-cell:hover {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
</style>
</head>
<body>
<main>
<h1>tekt.observer — multi-track site</h1>
<p class="meta">One card per track, one link per day, plus per-audience report variants.</p>
{''.join(cards)}
<p class="footer">Rendered by scripts/render_multitrack_site.py.</p>
</main>
</body>
</html>
"""


def render_multi(track_roots: dict[str, Path], out_dir: Path) -> tuple[int, int]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "style.css").write_text(STYLE_CSS)

    pages = 0
    raws = 0
    tracks_info: list[dict] = []

    for track, root in track_roots.items():
        model = Model(root)
        t = model.find_track(track)
        if t is None:
            continue

        dates = sorted(
            set(t.digest_dates) | set(t.discovery_dates) | set(model.organized_dates(track)),
            reverse=True,
        )
        audiences: list[str] = []
        if dates:
            audiences = model.audiences_for(track, dates[0])

        # Track landing (list of dates)
        _write(out_dir, f"{track}/index.html", render_track_index_custom(model, track, dates),
               depth=1, track=track)
        pages += 1

        # Sources
        _write(out_dir, f"{track}/sources.html", render_sources(model, track),
               depth=1, track=track)
        pages += 1

        # Per-date pages
        for date in dates:
            _write(out_dir, f"{track}/{date}/index.html",
                   render_report(model, track, date), depth=2, track=track)
            _write(out_dir, f"{track}/{date}/details.html",
                   render_run(model, track, date), depth=2, track=track)
            _write(out_dir, f"{track}/{date}/feed.html",
                   render_feed(model, track, date), depth=2, track=track)
            _write(out_dir, f"{track}/{date}/trends.html",
                   render_trends(model, track, date), depth=2, track=track)
            pages += 4
            for aud in model.audiences_for(track, date):
                _write(out_dir, f"{track}/{date}/audience/{aud}.html",
                       render_report(model, track, date, audience=aud),
                       depth=3, track=track)
                pages += 1

        # Raw copies (shared /raw/<kind>/<track>/<date>.json)
        for kind, date_list in [
            ("digests", t.digest_dates),
            ("discovery", t.discovery_dates),
            ("organized", model.organized_dates(track)),
            ("trends", model.trends_dates(track)),
        ]:
            for date in date_list:
                src = model.raw_path(kind, track, date)
                if src is None:
                    continue
                dst = out_dir / "raw" / kind / track / f"{date}.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                raws += 1

        tracks_info.append({
            "track": track,
            "display": t.display_name,
            "dates": dates,
            "audiences": audiences,
        })

    (out_dir / "index.html").write_text(_top_index(tracks_info))
    pages += 1
    return pages, raws


def render_track_index_custom(model: Model, track: str, dates: list[str]) -> str:
    """Track landing with a compact date list (feeds/trends links per date)."""
    from html import escape as e
    t = model.find_track(track)
    if t is None:
        return "<h1>Not found</h1>"
    rows = []
    for d in dates:
        rows.append(
            f'<tr>'
            f'<td><a href="/track/{e(track)}/{e(d)}">{e(d)}</a></td>'
            f'<td><a href="/track/{e(track)}/feed/{e(d)}">feed</a></td>'
            f'<td><a href="/track/{e(track)}/trends/{e(d)}">trends</a></td>'
            f'<td><a href="/track/{e(track)}/{e(d)}/details">digest</a></td>'
            f'</tr>'
        )
    body = (
        f'<h1>{e(t.display_name)}</h1>'
        f'<p><a href="/track/{e(track)}/sources">Sources &amp; config</a></p>'
        f'<h2>Days</h2>'
        f'<table><tr><th>Date</th><th>Feed</th><th>Trends</th><th>Digest</th></tr>'
        + "".join(rows) + '</table>'
    )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{e(t.display_name)}</title>"
        "<link rel=\"stylesheet\" href=\"/style.css\">"
        "</head><body><main>"
        f'<nav class="crumbs"><a href="/">Home</a> / {e(t.display_name)}</nav>'
        f"{body}"
        "<p class=\"footer\">tekt.observer — multi-track site</p>"
        "</main></body></html>"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--track", action="append", required=True,
                    help="Add a track. Repeatable. Form: slug or slug=root_path")
    ap.add_argument("--out", required=True, help="Output directory (will be wiped)")
    args = ap.parse_args()
    track_roots: dict[str, Path] = {}
    for spec in args.track:
        if "=" in spec:
            slug, path = spec.split("=", 1)
            track_roots[slug] = Path(path).resolve()
        else:
            slug = spec
            path = Path(__file__).resolve().parents[1] / "tests" / "tmp" / slug
            track_roots[slug] = path
    out_dir = Path(args.out).resolve()
    pages, raws = render_multi(track_roots, out_dir)
    print(f"Wrote {pages} pages and {raws} raw JSON files to {out_dir}")
    print(f"Open: file://{out_dir}/index.html")


if __name__ == "__main__":
    main()
