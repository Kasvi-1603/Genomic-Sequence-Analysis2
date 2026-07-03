"""One-step input preparation for benchmark/matcher calls."""

from __future__ import annotations

from pathlib import Path

from igda.input.fasta import load_fasta_sequence
from igda.input.patterns import load_patterns_file, normalize_patterns


def prepare_run_inputs(
    *,
    fasta_path: str | Path,
    patterns: list[str] | None = None,
    patterns_path: str | Path | None = None,
    dedupe_patterns: bool = True,
) -> tuple[str, list[str]]:
    """
    Return `(text, patterns)` ready for `run_match` / `run_benchmark`.

    You can provide patterns either:
    - directly via `patterns=[...]`, or
    - from a file via `patterns_path=...`
    """
    text = load_fasta_sequence(fasta_path)

    has_inline = patterns is not None
    has_file = patterns_path is not None
    if has_inline == has_file:
        raise ValueError("Provide exactly one of `patterns` or `patterns_path`.")

    if has_inline:
        resolved = normalize_patterns(patterns or [], dedupe=dedupe_patterns)
    else:
        resolved = load_patterns_file(patterns_path, dedupe=dedupe_patterns)  # type: ignore[arg-type]

    if not resolved:
        raise ValueError("No valid patterns found after normalization.")
    return text, resolved

