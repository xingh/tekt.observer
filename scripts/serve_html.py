"""Serve tekt.observer run data as HTML over http.server.

Reloads JSON on every request so edits in the repo show up on refresh.
Binds to 127.0.0.1 by default (loopback only) unless --host overrides.
"""

from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

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


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = "tekt.observer-viewer/0.1"
    root: Path = Path(".")

    def log_message(self, fmt: str, *args) -> None:  # noqa: N802
        sys.stderr.write(f"[viewer] {self.address_string()} - {fmt % args}\n")

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body: str, status: int = 200) -> None:
        self._write(status, body.encode("utf-8"), "text/html; charset=utf-8")

    def _text(self, body: str, status: int = 200) -> None:
        self._write(status, body.encode("utf-8"), "text/plain; charset=utf-8")

    def _json_file(self, path: Path) -> None:
        if not path.is_file():
            self._html("<h1>404 raw not found</h1>", 404)
            return
        data = path.read_bytes()
        self._write(200, data, "application/json")

    def do_GET(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        model = Model(self.root)
        query = {}
        if parts.query:
            for pair in parts.query.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query[k] = unquote(v)
        if path == "/" or path == "/index.html":
            self._html(render_index(model))
            return
        if path == "/style.css":
            self._write(200, STYLE_CSS.encode("utf-8"), "text/css; charset=utf-8")
            return
        segs = [s for s in path.split("/") if s]
        if len(segs) >= 2 and segs[0] == "raw":
            kind = segs[1]
            if kind not in ("digests", "discovery"):
                self._html(f"<h1>404 unknown raw kind {kind}</h1>", 404)
                return
            if len(segs) != 4 or not segs[3].endswith(".json"):
                self._html("<h1>404 bad raw path</h1>", 404)
                return
            slug = segs[2]
            date = segs[3][:-5]
            p = model.raw_path(kind, slug, date)
            if p is None:
                self._html("<h1>404 raw not found</h1>", 404)
                return
            self._json_file(p)
            return
        if len(segs) >= 2 and segs[0] == "track":
            slug = segs[1]
            if len(segs) == 2 or (len(segs) == 3 and segs[2] in ("", "index.html")):
                self._html(render_track_index(model, slug))
                return
            if len(segs) == 3:
                tail = segs[2]
                if tail == "ranked":
                    self._html(render_ranked(model, slug))
                    return
                if tail == "sources":
                    self._html(render_sources(model, slug))
                    return
                # date page: /track/<slug>/<date> -> full report (with fallback)
                if len(tail) == 10 and tail[4] == "-" and tail[7] == "-":
                    aud = query.get("audience")
                    self._html(render_report(model, slug, tail, audience=aud))
                    return
            if len(segs) == 4 and segs[2] in ("feed", "trends"):
                date = segs[3]
                if len(date) == 10 and date[4] == "-" and date[7] == "-":
                    if segs[2] == "feed":
                        self._html(render_feed(model, slug, date))
                    else:
                        self._html(render_trends(model, slug, date))
                    return
            if len(segs) == 4 and segs[3] == "details":
                date = segs[2]
                if len(date) == 10 and date[4] == "-" and date[7] == "-":
                    self._html(render_run(model, slug, date))
                    return
            # /track/<slug>/<date>/audience/<aud>
            if len(segs) == 5 and segs[3] == "audience":
                date = segs[2]
                aud = segs[4]
                if len(date) == 10 and date[4] == "-" and date[7] == "-":
                    self._html(render_report(model, slug, date, audience=aud))
                    return
        self._html("<h1>404</h1>", 404)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="Repo-shaped root (has tracks/ and artifacts/)")
    ap.add_argument("--host", default="127.0.0.1", help="Bind host (default loopback only)")
    ap.add_argument("--port", type=int, default=8765, help="Bind port")
    args = ap.parse_args()
    ViewerHandler.root = Path(args.root).resolve()
    server = ThreadingHTTPServer((args.host, args.port), ViewerHandler)
    print(f"Serving tekt.observer viewer on http://{args.host}:{args.port}/ (root: {ViewerHandler.root})")
    print("Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
