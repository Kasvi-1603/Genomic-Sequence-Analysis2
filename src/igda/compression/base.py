"""Contract for compression codecs."""

from __future__ import annotations

from typing import Protocol

from igda.core import CompressionInfo, CompressionResult


class Compressor(Protocol):
    info: CompressionInfo

    def compress(self, text: str) -> CompressionResult: ...

