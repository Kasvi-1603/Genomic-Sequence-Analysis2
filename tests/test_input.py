from __future__ import annotations

import pytest

from igda.input import (
    load_fasta_sequence,
    load_patterns_file,
    normalize_patterns,
    prepare_run_inputs,
)


def test_load_fasta_sequence_skips_headers_and_blanks(tmp_path) -> None:
    p = tmp_path / "x.fasta"
    p.write_text(">header one\nACGT\n\nTTAA\n>second\nGG\n", encoding="utf-8")
    out = load_fasta_sequence(p)
    assert out == "ACGTTTAAGG"


def test_load_patterns_file_supports_comments_and_commas(tmp_path) -> None:
    p = tmp_path / "patterns.txt"
    p.write_text("# ignore me\nATG, TAA\n\nCGT\nATG\n", encoding="utf-8")
    out = load_patterns_file(p, dedupe=True)
    assert out == ["ATG", "TAA", "CGT"]


def test_normalize_patterns_dedupe_optional() -> None:
    raw = ["ATG", " ", "ATG", "TAA"]
    assert normalize_patterns(raw, dedupe=True) == ["ATG", "TAA"]
    assert normalize_patterns(raw, dedupe=False) == ["ATG", "ATG", "TAA"]


def test_prepare_run_inputs_inline_patterns(tmp_path) -> None:
    fasta = tmp_path / "s.fasta"
    fasta.write_text(">h\nACGTACGT\n", encoding="utf-8")
    text, patterns = prepare_run_inputs(fasta_path=fasta, patterns=["ACG", "ACG", ""])
    assert text == "ACGTACGT"
    assert patterns == ["ACG"]


def test_prepare_run_inputs_from_patterns_file(tmp_path) -> None:
    fasta = tmp_path / "s.fasta"
    pats = tmp_path / "p.txt"
    fasta.write_text(">h\nACGTACGT\n", encoding="utf-8")
    pats.write_text("ACG\nTAC\n", encoding="utf-8")
    text, patterns = prepare_run_inputs(fasta_path=fasta, patterns_path=pats)
    assert text == "ACGTACGT"
    assert patterns == ["ACG", "TAC"]


def test_prepare_run_inputs_requires_exactly_one_pattern_source(tmp_path) -> None:
    fasta = tmp_path / "s.fasta"
    pats = tmp_path / "p.txt"
    fasta.write_text(">h\nACGT\n", encoding="utf-8")
    pats.write_text("ACG\n", encoding="utf-8")

    with pytest.raises(ValueError):
        prepare_run_inputs(fasta_path=fasta)
    with pytest.raises(ValueError):
        prepare_run_inputs(fasta_path=fasta, patterns=["ACG"], patterns_path=pats)

