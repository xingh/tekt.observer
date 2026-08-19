import io
import json

from pocketbase_client import PocketBaseClient


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_client_paginates_and_sends_auth(monkeypatch):
    requests = []
    pages = [
        {"page": 1, "totalPages": 2, "items": [{"id": "a"}]},
        {"page": 2, "totalPages": 2, "items": [{"id": "b"}]},
    ]

    def open_(request, timeout):
        requests.append(request)
        return Response(json.dumps(pages.pop(0)).encode())

    monkeypatch.setattr("urllib.request.urlopen", open_)
    client = PocketBaseClient("http://127.0.0.1:8090/", token="token-value")
    assert [row["id"] for row in client.list_records("items", filter_='workspace="w"')] == ["a", "b"]
    assert requests[0].get_header("Authorization") == "token-value"
    assert "perPage=200" in requests[0].full_url
