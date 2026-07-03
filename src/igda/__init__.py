"""Public entry points for the `igda` package (matchers, later bench/viz)."""

from igda.bench import (
    BenchmarkSummary,
    CompressionBenchmarkRow,
    MatcherBenchmarkRow,
    RunConfig,
    run_benchmark,
)
from igda.compression import (
    get_compressor,
    list_compression_ids,
    list_compressions,
    run_compression,
)
from igda.core import (
    AlgorithmInfo,
    CompressionInfo,
    CompressionKind,
    CompressionResult,
    MatchKind,
    MatchResult,
)
from igda.input import (
    load_fasta_sequence,
    load_patterns_file,
    load_plain_text,
    normalize_patterns,
    prepare_run_inputs,
)
from igda.matchers import get_matcher, list_algorithm_ids, list_algorithms, run_match

__all__ = [
    "AlgorithmInfo",
    "CompressionInfo",
    "CompressionKind",
    "CompressionResult",
    "MatchKind",
    "MatchResult",
    "get_matcher",
    "list_algorithms",
    "list_algorithm_ids",
    "run_match",
    "RunConfig",
    "MatcherBenchmarkRow",
    "CompressionBenchmarkRow",
    "BenchmarkSummary",
    "run_benchmark",
    "get_compressor",
    "list_compressions",
    "list_compression_ids",
    "run_compression",
    "load_fasta_sequence",
    "load_plain_text",
    "load_patterns_file",
    "normalize_patterns",
    "prepare_run_inputs",
]
