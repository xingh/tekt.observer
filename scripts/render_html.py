"""Render tekt.observer run data as a static HTML site.

Walks tracks/ and artifacts/ under --root, emits pages under --out.
Root-anchored URLs (/style.css, /track/foo/) are rewritten per page depth
so the output works when opened via file:// or served from any subdirectory.
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
    render_index,
    render_report,
    render_run,
    render_ranked,
    render_sources,
    render_track_index,
    render_trends,
)


_ABSOLUTE_HREF = re.compile(r'(href|src)="/([^"]*)"')


def _rewrite_absolute_paths(html: str, depth: int) -> str:
    prefix = "./" if depth == 0 else "../" * depth
    return _ABSOLUTE_HREF.sub(lambda m: f'{m.group(1)}="{prefix}{m.group(2)}"', html)


def _write_page(out_dir: Path, rel_path: str, html: str) -> None:
    target = out_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    depth = len(target.relative_to(out_dir).parts) - 1
    target.write_text(_rewrite_absolute_paths(html, depth))


def render_all(root: Path, out_dir: Path) -> tuple[int, int]:
    model = Model(root)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    (out_dir / "style.css").write_text(STYLE_CSS)

    pages = 0
    raws = 0
    _write_page(out_dir, "index.html", render_index(model))
    pages += 1

    for track in model.tracks():
        slug = track.slug
        _write_page(out_dir, f"track/{slug}/index.html", render_track_index(model, slug))
        pages += 1
        _write_page(out_dir, f"track/{slug}/sources.html", render_sources(model, slug))
        pages += 1
        if track.ranked_jobs:
            _write_page(out_dir, f"track/{slug}/ranked.html", render_ranked(model, slug))
            pages += 1
        dates = sorted(set(track.digest_dates) | set(track.discovery_dates), reverse=True)
        for date in dates:
            _write_page(out_dir, f"track/{slug}/{date}.html", render_report(model, slug, date))
            _write_page(out_dir, f"track/{slug}/{date}/details.html", render_run(model, slug, date))
            pages += 2
        for date in model.organized_dates(slug):
            _write_page(out_dir, f"track/{slug}/feed/{date}.html", render_feed(model, slug, date))
            pages += 1
        for date in model.trends_dates(slug):
            _write_page(out_dir, f"track/{slug}/trends/{date}.html", render_trends(model, slug, date))
            pages += 1
        for kind, date_list in [
            ("digests", track.digest_dates),
            ("discovery", track.discovery_dates),
            ("organized", model.organized_dates(slug)),
            ("trends", model.trends_dates(slug)),
        ]:
            for date in date_list:
                src = model.raw_path(kind, slug, date)
                if src is not None:
                    dst = out_dir / "raw" / kind / slug / f"{date}.json"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    raws += 1
    return pages, raws


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root (has tracks/ and artifacts/)")
    ap.add_argument("--out", default="site", help="Output directory")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_dir = Path(args.out).resolve()
    if not (root / "tracks").is_dir():
        print(f"warning: {root}/tracks/ not found", file=sys.stderr)
    pages, raws = render_all(root, out_dir)
    print(f"Wrote {pages} pages and {raws} raw JSON files to {out_dir}")
    print(f"Open: file://{out_dir}/index.html")


if __name__ == "__main__":
    main()
