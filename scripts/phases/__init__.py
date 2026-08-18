"""Shared contracts for independently runnable observation phases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


PhaseSchema = Mapping[str, type[Any]]


@dataclass(frozen=True)
class PhaseContext:
    """Named values supplied to a phase invocation."""

    values: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseResult:
    """Named values produced by a successful phase invocation."""

    values: Mapping[str, Any] = field(default_factory=dict)


class Phase(Protocol):
    """Structural contract implemented by each observation phase."""

    name: str
    inputs: PhaseSchema
    outputs: PhaseSchema

    def run(self, context: PhaseContext) -> PhaseResult:
        """Run the phase once with the supplied context."""
        ...


__all__ = ["Phase", "PhaseContext", "PhaseResult", "PhaseSchema"]
