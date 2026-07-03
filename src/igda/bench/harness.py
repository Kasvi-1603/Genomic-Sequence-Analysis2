"""Benchmark harness: same input for each algorithm, warmup + repeated trials."""

from __future__ import annotations

from math import ceil
from statistics import median
from time import perf_counter

from igda.bench.types import (
    BenchmarkSummary,
    CompressionBenchmarkRow,
    MatcherBenchmarkRow,
    RunConfig,
)
from igda.compression import get_compressor, list_compression_ids
from igda.matchers import get_matcher, list_algorithm_ids


def _ms(seconds: float) -> float:
    return seconds * 1000.0


def _p95(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    s = sorted(values)
    idx = ceil(0.95 * len(s)) - 1
    idx = max(0, min(idx, len(s) - 1))
    return s[idx]


def _stats(times_ms: list[float]) -> tuple[float, float, float, float | None]:
    return median(times_ms), min(times_ms), max(times_ms), _p95(times_ms)


def _effective_algorithm_ids(cfg: RunConfig) -> list[str]:
    return list(cfg.selected_algorithm_ids) if cfg.selected_algorithm_ids else list_algorithm_ids()


def _effective_compression_ids(cfg: RunConfig) -> list[str]:
    return (
        list(cfg.selected_compression_ids)
        if cfg.selected_compression_ids
        else list_compression_ids()
    )


def run_benchmark(text: str, patterns: list[str], config: RunConfig | None = None) -> BenchmarkSummary:
    cfg = config or RunConfig()
    if cfg.trials <= 0:
        raise ValueError("trials must be >= 1")
    if cfg.warmup < 0:
        raise ValueError("warmup must be >= 0")

    matcher_rows: list[MatcherBenchmarkRow] = []
    compression_rows: list[CompressionBenchmarkRow] = []
    notes: list[str] = []

    algo_ids = _effective_algorithm_ids(cfg)
    comp_ids = _effective_compression_ids(cfg)

    saw_exact = False
    saw_approx = False

    for algorithm_id in algo_ids:
        matcher = get_matcher(algorithm_id)
        if matcher.info.match_kind.value == "exact":
            saw_exact = True
        else:
            saw_approx = True

        # Warmup runs (not measured in final stats)
        for _ in range(cfg.warmup):
            matcher.match(text, patterns, max_edits=cfg.max_edits)

        times_ms: list[float] = []
        match_counts: list[int] = []
        last_extra: dict[str, object] = {}
        for _ in range(cfg.trials):
            t0 = perf_counter()
            out = matcher.match(text, patterns, max_edits=cfg.max_edits)
            dt = perf_counter() - t0
            times_ms.append(_ms(dt))
            match_counts.append(out.match_count)
            last_extra = dict(out.extra)

        med, mn, mx, p95 = _stats(times_ms)
        if len(set(match_counts)) > 1:
            notes.append(
                f"Match counts varied across trials for {algorithm_id}. "
                "Check for non-deterministic behavior."
            )

        matcher_rows.append(
            MatcherBenchmarkRow(
                algorithm_id=matcher.info.id,
                algorithm_name=matcher.info.name,
                match_kind=matcher.info.match_kind.value,
                trials=cfg.trials,
                time_ms_median=med,
                time_ms_min=mn,
                time_ms_max=mx,
                time_ms_p95=p95,
                match_count=match_counts[-1] if match_counts else 0,
                extra=last_extra,
            )
        )

    if saw_exact and saw_approx:
        notes.append(
            "Exact and approximate algorithms are both included. "
            "Compare time directly, but interpret match_count separately."
        )

    for compression_id in comp_ids:
        compressor = get_compressor(compression_id)

        for _ in range(cfg.warmup):
            compressor.compress(text)

        times_ms: list[float] = []
        last = None
        for _ in range(cfg.trials):
            t0 = perf_counter()
            out = compressor.compress(text)
            dt = perf_counter() - t0
            times_ms.append(_ms(dt))
            last = out

        med, mn, mx, p95 = _stats(times_ms)
        compression_rows.append(
            CompressionBenchmarkRow(
                compression_id=compressor.info.id,
                compression_name=compressor.info.name,
                trials=cfg.trials,
                time_ms_median=med,
                time_ms_min=mn,
                time_ms_max=mx,
                time_ms_p95=p95,
                original_bytes=last.original_bytes if last is not None else 0,
                compressed_bytes=last.compressed_bytes if last is not None else 0,
                ratio=last.ratio if last is not None else 1.0,
                percent_saved=last.percent_saved if last is not None else 0.0,
                extra=dict(last.extra) if last is not None else {},
            )
        )

    return BenchmarkSummary(
        config=cfg,
        matcher_rows=matcher_rows,
        compression_rows=compression_rows,
        notes=notes,
    )

