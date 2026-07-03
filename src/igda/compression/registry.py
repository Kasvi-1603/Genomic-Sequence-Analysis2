"""Select compression by `compression_id` (frontend dropdown / API query param)."""

from __future__ import annotations

from igda.compression.base import Compressor
from igda.compression.huffman import HuffmanCompressor
from igda.compression.rle import RleCompressor
from igda.core import CompressionInfo, CompressionResult

_REGISTRY: dict[str, Compressor] = {
    "huffman": HuffmanCompressor(),
    "rle": RleCompressor(),
}


def list_compressions() -> list[CompressionInfo]:
    return [c.info for c in _REGISTRY.values()]


def list_compression_ids() -> list[str]:
    return list(_REGISTRY.keys())


def get_compressor(compression_id: str) -> Compressor:
    if compression_id not in _REGISTRY:
        raise KeyError(
            f"Unknown compression_id={compression_id!r}. Choose one of: {', '.join(_REGISTRY)}"
        )
    return _REGISTRY[compression_id]


def run_compression(compression_id: str, text: str) -> CompressionResult:
    return get_compressor(compression_id).compress(text)

