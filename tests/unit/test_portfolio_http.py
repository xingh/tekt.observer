import json
import threading
import time
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from portfolio_state import PortfolioStateError, PortfolioStore
from portfolio_operations import OperationManager
from serve_html import ViewerHandler, operation_command, render_management
import pytest


def _server(tmp_path):
    (tmp_path / "tracks" / "alpha").mkdir(parents=True)
    ViewerHandler.root = tmp_path; ViewerHandler.csrf_token = "test-token"; ViewerHandler.writes_enabled = True
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), ViewerHandler)
    except PermissionError:
        pytest.skip("runtime sandbox does not permit loopback sockets")
    thread = threading.Thread(target=server.serve_forever); thread.start()
    return server, thread


def _request(server, method, path, body=None, headers=None):
    conn = HTTPConnection("127.0.0.1", server.server_port)
    conn.request(method, path, body=body, headers=headers or {})
    response = conn.getresponse(); data = response.read(); conn.close()
    return response.status, data


def test_dashboard_and_state_api(tmp_path):
    server, thread = _server(tmp_path)
    try:
        status, body = _request(server, "GET", "/")
        assert status == 200 and b"Portfolio dashboard" in body
        status, body = _request(server, "GET", "/api/v1/state")
        assert status == 200 and json.loads(body)["csrf_token"] == "test-token"
    finally: server.shutdown(); thread.join(); server.server_close()


def test_mutations_require_json_csrf_and_same_origin(tmp_path):
    server, thread = _server(tmp_path)
    try:
        payload = json.dumps({"id": "ai", "label": "AI", "description": "", "keywords": []})
        status, _ = _request(server, "POST", "/api/v1/interests", payload, {"Content-Type": "application/json"})
        assert status == 403
        status, _ = _request(server, "POST", "/api/v1/interests", payload, {"Content-Type": "text/plain", "X-CSRF-Token": "test-token"})
        assert status == 400
        status, _ = _request(server, "POST", "/api/v1/interests", payload, {"Content-Type": "application/json", "X-CSRF-Token": "test-token", "Origin": "http://evil.test"})
        assert status == 403
        status, body = _request(server, "POST", "/api/v1/interests", payload, {"Content-Type": "application/json", "X-CSRF-Token": "test-token"})
        assert status == 201 and json.loads(body)["interests"][0]["id"] == "ai"
    finally: server.shutdown(); thread.join(); server.server_close()


def test_management_page_and_schedule_command(tmp_path):
    (tmp_path / "tracks" / "alpha").mkdir(parents=True)
    store = PortfolioStore(tmp_path)
    page = render_management(tmp_path, "test-token")
    assert "Manage workflows" in page and "Save schedule" in page and "Alpha" in page
    track, kind, command = operation_command(tmp_path, store, {
        "kind": "schedule", "track": "alpha", "cadence": "weekly", "time": "08:30",
        "weekday": "fri", "delivery": ["email", "telegram"],
    })
    assert (track, kind) == ("alpha", "schedule")
    assert command[-4:] == ["--delivery", "email", "--delivery", "telegram"]
    op = OperationManager(tmp_path).create(track, kind, command)
    for _ in range(100):
        current = OperationManager(tmp_path).get(op["id"])
        if current["state"] in {"ready", "failed"}: break
        time.sleep(.01)
    assert current["state"] == "ready"
    assert (tmp_path / ".schedule.local").read_text().rstrip().endswith("weekly fri 08:30 track alpha --delivery email --delivery telegram")
    with pytest.raises(PortfolioStateError, match="month_day"):
        operation_command(tmp_path, store, {"kind": "schedule", "track": "alpha", "cadence": "monthly", "time": "08:30", "month_day": 0})
