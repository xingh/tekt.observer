"""Serve tekt.observer run data as HTML over http.server.

Reloads JSON on every request so edits in the repo show up on refresh.
Binds to 127.0.0.1 by default (loopback only) unless --host overrides.
"""

from __future__ import annotations

import argparse
import html
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import json  # noqa: E402
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
from track_feedback import append_event  # noqa: E402
from portfolio_state import PortfolioStateError, PortfolioStore, unified_items  # noqa: E402
from portfolio_operations import OperationManager  # noqa: E402

MAX_JSON_BYTES = 256 * 1024


def render_dashboard(root: Path, csrf_token: str, query: dict[str, str], writes_enabled: bool = True) -> str:
    store = PortfolioStore(root)
    portfolios = store.portfolios()
    pid = query.get("portfolio") or portfolios["default_portfolio_id"]
    portfolio = next((p for p in portfolios["portfolios"] if p["id"] == pid), portfolios["portfolios"][0])
    track_filter = set(portfolio["track_ids"])
    if query.get("track"): track_filter &= {query["track"]}
    items = unified_items(root, tracks=track_filter)
    needle = query.get("q", "").casefold()
    audience, topic = query.get("audience", ""), query.get("topic", "")
    if needle: items = [x for x in items if needle in (str(x.get("title", "")) + " " + str(x.get("description", ""))).casefold()]
    if audience: items = [x for x in items if x.get("audience") == audience]
    if topic: items = [x for x in items if topic in (x.get("topic_ids") or [x.get("topic")])]
    opts = "".join(f'<option value="{html.escape(p["id"])}" {"selected" if p["id"] == portfolio["id"] else ""}>{html.escape(p["name"])}</option>' for p in portfolios["portfolios"] if not p.get("archived"))
    cards = []
    for item in items[:250]:
        score = "—" if item["score_percent"] is None else f'{item["score_percent"]:.0f}%'
        actions = (f'<div class="actions" data-track="{html.escape(item["track"])}" data-item="{html.escape(item["item_key"])}" data-audience="{html.escape(item.get("audience") or "")}"><button data-action="save">Save</button><button data-action="hide">Hide</button><button data-action="click">Clicked</button></div>' if writes_enabled else '')
        cards.append(f'''<article class="signal" data-track="{html.escape(item["track"])}">
<p class="meta">{html.escape(item["track"])} · {html.escape(str(item.get("date") or "unknown date"))} · score {score}</p>
<h2><a href="{html.escape(item.get("url") or "#")}">{html.escape(item["title"])}</a></h2>
<p class="meta">{html.escape(item["artifact_kind"])} · {html.escape(item.get("audience") or "default audience")}</p>
{actions}</article>''')
    track_cards = "".join(f'<a class="track-health" href="/track/{html.escape(t)}">{html.escape(store.track(t)["display_name"])}<small>{html.escape(store.track(t)["status"])}</small></a>' for t in portfolio["track_ids"] if t in store.track_ids())
    empty = '<div class="empty"><h2>No signals yet</h2><p>Run a track or change the filters. Existing CLI and static workflows continue to work.</p></div>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>tekt.observer portfolio</title><link rel="stylesheet" href="/style.css"><style>
.toolbar{{display:flex;gap:10px;flex-wrap:wrap;align-items:end}} .toolbar label{{display:grid;gap:4px}} .tracks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0}} .track-health,.signal{{background:var(--card);border:1px solid var(--border);border-radius:9px;padding:14px;text-decoration:none;color:inherit}} .track-health small{{display:block;margin-top:6px}} .inbox{{display:grid;gap:10px}} .signal h2{{font-size:17px;margin:5px 0}} .actions{{display:flex;gap:7px}} button,input,select{{font:inherit;padding:7px}} button:focus,a:focus,input:focus,select:focus{{outline:3px solid var(--accent)}} @media(max-width:600px){{main{{padding:12px}}.toolbar>*{{width:100%}}}}
</style></head><body><main><h1>Portfolio dashboard</h1><form class="toolbar" method="get"><label>Portfolio<select name="portfolio" onchange="this.form.submit()">{opts}</select></label><label>Track<input name="track" value="{html.escape(query.get('track',''))}"></label><label>Audience<input name="audience" value="{html.escape(audience)}"></label><label>Topic<input name="topic" value="{html.escape(topic)}"></label><label>Search<input name="q" value="{html.escape(query.get('q',''))}"></label><button>Filter</button></form><div class="tracks">{track_cards}</div><h2>Signal inbox <small>({len(items)})</small></h2><section class="inbox">{''.join(cards) or empty}</section></main><script>
const csrf={json.dumps(csrf_token)}; document.addEventListener('click',async e=>{{let b=e.target.closest('[data-action]');if(!b)return;let row=b.closest('.actions');let audience=row.dataset.audience;if(!audience){{let r=await fetch('/api/v1/tracks/'+row.dataset.track);if(r.ok)audience=(await r.json()).default_audience}}if(!audience){{alert('Configure a default audience for this track first.');return}}b.disabled=true;let r=await fetch('/api/v1/feedback',{{method:'POST',headers:{{'Content-Type':'application/json','X-CSRF-Token':csrf}},body:JSON.stringify({{track:row.dataset.track,item_key:row.dataset.item,audience,action:b.dataset.action}})}});b.disabled=false;if(r.ok){{b.textContent='Done';if(b.dataset.action==='hide')b.closest('.signal').remove()}}else alert((await r.json()).error)}});
</script></body></html>'''


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = "tekt.observer-viewer/0.1"
    root: Path = Path(".")
    csrf_token: str = ""
    writes_enabled: bool = True

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
        # Keep feedback controls on legacy report/feed pages compatible with the
        # secured mutation endpoint without changing static renderer output.
        if self.writes_enabled and "<head>" in body:
            bootstrap = ("<script>window.TEKT_CSRF=" + json.dumps(self.csrf_token) + ";"
                         "const _tektFetch=window.fetch;window.fetch=(u,o={})=>{if(typeof u==='string'&&(u==='/feedback'||u.startsWith('/api/v1/'))){o.headers={...(o.headers||{}),'X-CSRF-Token':window.TEKT_CSRF};}return _tektFetch(u,o)};</script>")
            body = body.replace("<head>", "<head>" + bootstrap, 1)
        self._write(status, body.encode("utf-8"), "text/html; charset=utf-8")

    def _text(self, body: str, status: int = 200) -> None:
        self._write(status, body.encode("utf-8"), "text/plain; charset=utf-8")

    def _json_file(self, path: Path) -> None:
        if not path.is_file():
            self._html("<h1>404 raw not found</h1>", 404)
            return
        data = path.read_bytes()
        self._write(200, data, "application/json")

    def _json(self, payload, status=200):
        self._write(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _request_json(self):
        if not self.writes_enabled: raise PermissionError("writes are disabled on non-loopback bindings")
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json": raise PortfolioStateError("Content-Type must be application/json")
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and urlsplit(origin).netloc != host: raise PermissionError("cross-origin writes are not allowed")
        if self.headers.get("X-CSRF-Token") != self.csrf_token: raise PermissionError("invalid CSRF token")
        try: length = int(self.headers.get("Content-Length", "0"))
        except ValueError: raise PortfolioStateError("invalid Content-Length")
        if length <= 0 or length > MAX_JSON_BYTES: raise PortfolioStateError("request body size is invalid")
        try: value = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise PortfolioStateError(f"malformed JSON: {exc}") from exc
        if not isinstance(value, dict): raise PortfolioStateError("JSON body must be an object")
        return value

    def do_POST(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        if path == "/feedback":
            # Legacy endpoint remains available to old rendered pages, but now shares validation.
            path = "/api/v1/feedback"
        if not path.startswith("/api/v1/"):
            self._html("<h1>404</h1>", 404)
            return
        try:
            body = self._request_json(); store = PortfolioStore(self.root)
            if path == "/api/v1/feedback":
                if body.get("track") not in store.track_ids(): raise PortfolioStateError("unknown track")
                if not any(x["id"] == f'{body.get("track")}:{body.get("item_key")}' for x in unified_items(self.root, tracks={body.get("track")})): raise PortfolioStateError("unknown item")
                path_written = append_event(self.root, body); self._json({"ok": True, "wrote": str(path_written.relative_to(self.root))}); return
            if path == "/api/v1/interests":
                def add(data): data["interests"].append(body); return data
                self._json(store.mutate("interests", add), 201); return
            if path == "/api/v1/portfolios":
                def add(data): data["portfolios"].append(body); return data
                self._json(store.mutate("portfolios", add), 201); return
            if path == "/api/v1/operations":
                kind, track = body.get("kind"), body.get("track")
                if track not in store.track_ids() and kind != "setup": raise PortfolioStateError("unknown track")
                commands = {
                    "run": ["bash", "scripts/run_pipeline.sh", "--track", str(track), "--live"],
                    "validate_sources": [sys.executable, "scripts/discover_jobs.py", "--track", str(track), "--plan-only"],
                }
                if kind not in commands: raise PortfolioStateError("this operation requires its dedicated setup or schedule form")
                self._json(OperationManager(self.root).create(str(track), str(kind), commands[kind]), 202); return
            if path.startswith("/api/v1/operations/") and path.endswith("/cancel"):
                self._json(OperationManager(self.root).cancel(path.split("/")[-2])); return
            self._json({"error": "route not found"}, 404)
        except PermissionError as exc: self._json({"error": str(exc)}, 403)
        except (PortfolioStateError, ValueError) as exc: self._json({"error": str(exc)}, 400)

    def do_PUT(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path); segs = [s for s in path.split("/") if s]
        try:
            body = self._request_json(); store = PortfolioStore(self.root)
            if len(segs) == 4 and segs[:3] == ["api", "v1", "tracks"]: self._json(store.save_track(segs[3], body)); return
            if len(segs) == 5 and segs[:3] == ["api", "v1", "tracks"] and segs[4] == "taxonomy": self._json(store.save_taxonomy(segs[3], body)); return
            kind = segs[2] if len(segs) == 4 else ""; ident = segs[3] if len(segs) == 4 else ""
            if kind in ("interests", "portfolios"):
                key = kind; singular = "id"
                def replace(data):
                    rows = data[key]; index = next((i for i,x in enumerate(rows) if x[singular] == ident), None)
                    if index is None: raise PortfolioStateError(f"unknown {kind[:-1]}")
                    if body.get("id", ident) != ident: raise PortfolioStateError("stable IDs are immutable")
                    rows[index] = {**body, "id": ident}; return data
                self._json(store.mutate(kind, replace)); return
            self._json({"error": "route not found"}, 404)
        except PermissionError as exc: self._json({"error": str(exc)}, 403)
        except (PortfolioStateError, ValueError) as exc: self._json({"error": str(exc)}, 400)

    def do_DELETE(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path); segs = [s for s in path.split("/") if s]
        try:
            self._request_json(); store = PortfolioStore(self.root)
            if len(segs) != 4 or segs[:2] != ["api", "v1"] or segs[2] not in {"interests", "portfolios"}:
                self._json({"error": "route not found"}, 404); return
            kind, ident = segs[2], segs[3]
            if kind == "interests":
                portfolios = store.portfolios()["portfolios"]
                track_refs = [t for t in store.track_ids() if ident in store.track(t)["interest_ids"] or ident in store.track(t)["interest_topic_mappings"]]
                portfolio_refs = [p["id"] for p in portfolios if ident in p["interest_ids"]]
                if track_refs or portfolio_refs: raise PortfolioStateError(f"interest is referenced by tracks={track_refs}, portfolios={portfolio_refs}")
            else:
                if ident == store.portfolios()["default_portfolio_id"]: raise PortfolioStateError("cannot delete the default portfolio; archive or change the default first")
            def remove(data):
                before = len(data[kind]); data[kind] = [x for x in data[kind] if x["id"] != ident]
                if len(data[kind]) == before: raise PortfolioStateError(f"unknown {kind[:-1]}")
                return data
            self._json(store.mutate(kind, remove))
        except PermissionError as exc: self._json({"error": str(exc)}, 403)
        except (PortfolioStateError, ValueError) as exc: self._json({"error": str(exc)}, 400)

    def do_GET(self) -> None:  # noqa: N802
        parts = urlsplit(self.path)
        path = unquote(parts.path)
        model = Model(self.root)
        query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
        if path == "/" or path == "/index.html":
            self._html(render_dashboard(self.root, self.csrf_token, query, self.writes_enabled))
            return
        if path == "/style.css":
            self._write(200, STYLE_CSS.encode("utf-8"), "text/css; charset=utf-8")
            return
        segs = [s for s in path.split("/") if s]
        if segs[:2] == ["api", "v1"]:
            try:
                store = PortfolioStore(self.root)
                if segs == ["api", "v1", "state"]: self._json({"interests": store.interests(), "portfolios": store.portfolios(), "csrf_token": self.csrf_token, "writes_enabled": self.writes_enabled}); return
                if segs == ["api", "v1", "interests"]: self._json(store.interests()); return
                if segs == ["api", "v1", "portfolios"]: self._json(store.portfolios()); return
                if segs == ["api", "v1", "items"]:
                    tracks = set(query["track"].split(",")) if query.get("track") else None
                    items = unified_items(self.root, tracks=tracks)
                    if query.get("q"): items = [x for x in items if query["q"].casefold() in str(x).casefold()]
                    if query.get("audience"): items = [x for x in items if x.get("audience") == query["audience"]]
                    if query.get("topic"): items = [x for x in items if query["topic"] in (x.get("topic_ids") or [x.get("topic")])]
                    if query.get("date_from"): items = [x for x in items if str(x.get("date") or "") >= query["date_from"]]
                    if query.get("date_to"): items = [x for x in items if str(x.get("date") or "") <= query["date_to"]]
                    if query.get("interest"):
                        allowed = {t for t in store.track_ids() if query["interest"] in store.track(t)["interest_ids"]}
                        items = [x for x in items if x["track"] in allowed]
                    self._json({"items": items, "count": len(items)}); return
                if segs == ["api", "v1", "operations"]: self._json({"operations": OperationManager(self.root).list()}); return
                if len(segs) == 4 and segs[:3] == ["api", "v1", "operations"]:
                    op = OperationManager(self.root).get(segs[3]); self._json(op or {"error": "not found"}, 200 if op else 404); return
                if len(segs) == 4 and segs[:3] == ["api", "v1", "tracks"]: self._json(store.track(segs[3])); return
                if len(segs) == 5 and segs[:3] == ["api", "v1", "tracks"] and segs[4] == "taxonomy": self._json(store.taxonomy(segs[3])); return
                self._json({"error": "route not found"}, 404); return
            except PortfolioStateError as exc: self._json({"error": str(exc)}, 422); return
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
    ViewerHandler.csrf_token = secrets.token_urlsafe(32)
    ViewerHandler.writes_enabled = args.host in {"127.0.0.1", "::1", "localhost"}
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
