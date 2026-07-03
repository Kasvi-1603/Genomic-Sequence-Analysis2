from __future__ import annotations

import pytest

from igda.compression import list_compression_ids, run_compression


def test_supported_compressions() -> None:
    ids = set(list_compression_ids())
    assert "huffman" in ids
    assert "rle" in ids


def test_rle_good_on_runs() -> None:
    text = "AAAAAACCCCCCCGGGGGGTTTTTT"
    out = run_compression("rle", text)
    assert out.original_bytes == len(text)
    assert out.compressed_bytes < out.original_bytes
    assert out.percent_saved > 0


def test_rle_can_expand() -> None:
    text = "ACGTACGTACGT"
    out = run_compression("rle", text)
    assert out.compressed_bytes >= out.original_bytes


def test_huffman_has_payload_metrics() -> None:
    text = "AAAAAACCCGGTTT"
    out = run_compression("huffman", text)
    assert "payload_bits" in out.extra
    assert "codebook_bits_est" in out.extra
    assert out.original_bytes == len(text)


def test_unknown_compression() -> None:
    with pytest.raises(KeyError):
        run_compression("not_real", "ACGT")

