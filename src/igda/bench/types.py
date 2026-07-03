"""Simple benchmark config + output table shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RunConfig:
    warmup: int = 1
    trials: int = 5
    selected_algorithm_ids: list[str] = field(default_factory=list)
    selected_compression_ids: list[str] = field(default_factory=list)
    max_edits: int = 0


@dataclass(slots=True)
class MatcherBenchmarkRow:
    algorithm_id: str
    algorithm_name: str
    match_kind: str
    trials: int
    time_ms_median: float
    time_ms_min: float
    time_ms_max: float
    time_ms_p95: float | None
    match_count: int
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompressionBenchmarkRow:
    compression_id: str
    compression_name: str
    trials: int
    time_ms_median: float
    time_ms_min: float
    time_ms_max: float
    time_ms_p95: float | None
    original_bytes: int
    compressed_bytes: int
    ratio: float
    percent_saved: float
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkSummary:
    config: RunConfig
    matcher_rows: list[MatcherBenchmarkRow]
    compression_rows: list[CompressionBenchmarkRow]
    notes: list[str] = field(default_factory=list)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "config": {
                "warmup": self.config.warmup,
                "trials": self.config.trials,
                "selected_algorithm_ids": list(self.config.selected_algorithm_ids),
                "selected_compression_ids": list(self.config.selected_compression_ids),
                "max_edits": self.config.max_edits,
            },
            "matcher_rows": [row.__dict__ for row in self.matcher_rows],
            "compression_rows": [row.__dict__ for row in self.compression_rows],
            "notes": list(self.notes),
        }

