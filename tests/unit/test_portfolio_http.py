import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from serve_html import ViewerHandler
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
