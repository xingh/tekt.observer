#!/usr/bin/env python3
"""Small standard-library client for an unmodified PocketBase server."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


class PocketBaseError(RuntimeError):
    pass


@dataclass
class PocketBaseClient:
    base_url: str
    token: str | None = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = self.token
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise PocketBaseError(f"PocketBase {exc.code} for {method} {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise PocketBaseError(f"PocketBase unavailable at {self.base_url}: {exc.reason}") from exc
        return json.loads(body) if body else {}

    def authenticate(self, identity: str, password: str) -> dict[str, Any]:
        result = self.request("POST", "/api/collections/users/auth-with-password", {"identity": identity, "password": password})
        self.token = result["token"]
        return result

    def list_records(self, collection: str, *, filter_: str | None = None, sort: str = "id") -> list[dict[str, Any]]:
        page = 1
        records: list[dict[str, Any]] = []
        while True:
            query: dict[str, str | int] = {"page": page, "perPage": 200, "sort": sort}
            if filter_:
                query["filter"] = filter_
            result = self.request("GET", f"/api/collections/{urllib.parse.quote(collection)}/records?{urllib.parse.urlencode(query)}")
            records.extend(result.get("items", []))
            if page >= result.get("totalPages", 1):
                return records
            page += 1

    def create_record(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/api/collections/{urllib.parse.quote(collection)}/records", record)

    def update_record(self, collection: str, record_id: str, record: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", f"/api/collections/{urllib.parse.quote(collection)}/records/{urllib.parse.quote(record_id)}", record)

    def upsert_records(self, collection: str, records: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        existing = {row.get(key): row for row in self.list_records(collection) if row.get(key) is not None}
        output = []
        for record in records:
            value = record.get(key)
            if value in existing:
                output.append(self.update_record(collection, existing[value]["id"], record))
            else:
                output.append(self.create_record(collection, record))
        return output
