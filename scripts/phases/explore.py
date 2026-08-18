"""Explore a career source and return its probe artifact."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from phases import PhaseContext, PhaseResult
from probe_career_source import probe


Probe = Callable[..., dict[str, Any]]


class ExplorePhase:
    """Validate a source URL and adapt the existing source probe to a phase."""

    name = "explore"
    inputs: Mapping[str, type[Any]] = {
        "url": str,
        "source_name": str,
        "terms": list,
        "timeout": int,
    }
    outputs: Mapping[str, type[Any]] = {"exploration": dict}

    def __init__(self, probe_source: Probe = probe) -> None:
        self._probe_source = probe_source

    def run(self, context: PhaseContext) -> PhaseResult:
        url = context.values.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("explore requires a non-empty 'url' string")
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("explore 'url' must be an absolute HTTP(S) URL")

        source_name = context.values.get("source_name", "")
        if not isinstance(source_name, str):
            raise TypeError("explore 'source_name' must be a string")

        terms_value = context.values.get("terms", [])
        if isinstance(terms_value, (str, bytes)) or not isinstance(terms_value, Sequence):
            raise TypeError("explore 'terms' must be a sequence of strings")
        terms = list(terms_value)
        if not all(isinstance(term, str) for term in terms):
            raise TypeError("explore 'terms' must be a sequence of strings")

        timeout = context.values.get("timeout", 15)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            raise ValueError("explore 'timeout' must be a positive integer")

        artifact = self._probe_source(
            url,
            source_name=source_name,
            terms=terms,
            timeout=timeout,
        )
        return PhaseResult(values={"exploration": artifact})


__all__ = ["ExplorePhase"]
