from __future__ import annotations

import pytest

from igda.bench import RunConfig, run_benchmark


def test_benchmark_respects_selected_ids() -> None:
    cfg = RunConfig(
        warmup=0,
        trials=2,
        selected_algorithm_ids=["naive", "kmp"],
        selected_compression_ids=["rle"],
        max_edits=0,
    )
    summary = run_benchmark("ACGTACGTACGT", ["ACG"], cfg)
    assert [r.algorithm_id for r in summary.matcher_rows] == ["naive", "kmp"]
    assert [r.compression_id for r in summary.compression_rows] == ["rle"]


def test_benchmark_has_stats_and_counts() -> None:
    cfg = RunConfig(warmup=1, trials=3, selected_algorithm_ids=["naive"], selected_compression_ids=["huffman"])
    summary = run_benchmark("AAAAAACCCCCCGGGGGGTTTTTT", ["AAA"], cfg)
    row = summary.matcher_rows[0]
    assert row.time_ms_median >= 0.0
    assert row.time_ms_min >= 0.0
    assert row.time_ms_max >= row.time_ms_min
    assert row.match_count > 0
    c = summary.compression_rows[0]
    assert c.original_bytes > 0
    assert c.compressed_bytes >= 0


def test_benchmark_note_when_exact_and_approx_mixed() -> None:
    cfg = RunConfig(
        warmup=0,
        trials=2,
        selected_algorithm_ids=["kmp", "edit_distance"],
        selected_compression_ids=[],
        max_edits=1,
    )
    summary = run_benchmark("ACGTACGT", ["ACG"], cfg)
    assert any("Exact and approximate" in n for n in summary.notes)


def test_invalid_trials() -> None:
    with pytest.raises(ValueError):
        run_benchmark("ACGT", ["A"], RunConfig(trials=0))

