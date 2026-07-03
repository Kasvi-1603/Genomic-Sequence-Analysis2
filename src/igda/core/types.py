"""Shared data types for matchers and (later) benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MatchKind(str, Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"


class CompressionKind(str, Enum):
    LOSSLESS = "lossless"


@dataclass(frozen=True, slots=True)
class AlgorithmInfo:
    """What the UI (or report) can show: identity + DAA-style complexity + capabilities."""

    id: str
    name: str
    match_kind: MatchKind
    time_complexity: str
    space_complexity: str
    notes: str  # when the algorithm wins; exact vs approx caveats; fairness notes
    supports_multi_pattern: bool

    def as_public_dict(self) -> dict[str, Any]:
        """JSON-friendly; safe for a future REST layer."""
        return {
            "id": self.id,
            "name": self.name,
            "match_kind": self.match_kind.value,
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
            "notes": self.notes,
            "supports_multi_pattern": self.supports_multi_pattern,
        }


@dataclass(slots=True)
class MatchResult:
    """Result of a single matcher run. Exact vs approximate can differ; keep optional fields."""

    algorithm_id: str
    matches: list[dict[str, Any]]
    """
    List of match records. Suggested keys:
    - "start" (int), "end" (int) half-open [start, end) in the text
    - "pattern" (str) or "pattern_index" (int) when multi-pattern
    - "edit_distance" (int) for approximate
    """
    match_count: int
    extra: dict[str, Any] = field(default_factory=dict)
    """Optional: comparisons_made, shifts, or algorithm-specific stats for analysis."""


@dataclass(frozen=True, slots=True)
class CompressionInfo:
    """Metadata for a compression option (for UI dropdown + complexity display)."""

    id: str
    name: str
    compression_kind: CompressionKind
    time_complexity: str
    space_complexity: str
    notes: str

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "compression_kind": self.compression_kind.value,
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
            "notes": self.notes,
        }


@dataclass(slots=True)
class CompressionResult:
    """Result of one compression run; includes payload and front-end friendly metrics."""

    compression_id: str
    original_bytes: int
    compressed_bytes: int
    payload: Any
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        """Compressed/original; < 1 means space saved."""
        if self.original_bytes == 0:
            return 1.0
        return self.compressed_bytes / self.original_bytes

    @property
    def percent_saved(self) -> float:
        """Positive => reduced size, negative => expansion."""
        if self.original_bytes == 0:
            return 0.0
        return (1.0 - self.ratio) * 100.0
