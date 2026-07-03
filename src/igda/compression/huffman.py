from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import heapq

from igda.core import CompressionInfo, CompressionKind, CompressionResult


@dataclass(order=True)
class _HNode:
    freq: int
    order: int
    ch: str | None = None
    left: "_HNode | None" = None
    right: "_HNode | None" = None


def _build_tree(text: str) -> _HNode | None:
    if not text:
        return None
    freq = Counter(text)
    heap: list[_HNode] = []
    order = 0
    for ch, f in freq.items():
        heapq.heappush(heap, _HNode(freq=f, order=order, ch=ch))
        order += 1
    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(
            heap,
            _HNode(freq=a.freq + b.freq, order=order, ch=None, left=a, right=b),
        )
        order += 1
    return heap[0]


def _build_codes(root: _HNode | None) -> dict[str, str]:
    if root is None:
        return {}
    if root.ch is not None:
        return {root.ch: "0"}
    out: dict[str, str] = {}
    stack: list[tuple[_HNode, str]] = [(root, "")]
    while stack:
        node, code = stack.pop()
        if node.ch is not None:
            out[node.ch] = code or "0"
            continue
        if node.right is not None:
            stack.append((node.right, code + "1"))
        if node.left is not None:
            stack.append((node.left, code + "0"))
    return out


class HuffmanCompressor:
    info = CompressionInfo(
        id="huffman",
        name="Huffman Coding",
        compression_kind=CompressionKind.LOSSLESS,
        time_complexity="O(n + k log k) where k = unique symbols",
        space_complexity="O(k) tree + codes",
        notes="Works best on skewed symbol distributions. Includes model overhead.",
    )

    def compress(self, text: str) -> CompressionResult:
        original_bytes = len(text.encode("utf-8"))
        if not text:
            return CompressionResult(
                compression_id=self.info.id,
                original_bytes=0,
                compressed_bytes=0,
                payload={"codes": {}, "bitstring": ""},
                extra={"unique_symbols": 0, "payload_bits": 0, "codebook_bits_est": 0},
            )

        root = _build_tree(text)
        codes = _build_codes(root)
        bitstring = "".join(codes[ch] for ch in text)
        payload_bits = len(bitstring)
        payload_bytes = (payload_bits + 7) // 8

        # Simple, explicit model estimate for fair reporting:
        # char byte + code length byte + code bits per symbol.
        codebook_bits_est = sum(8 + 8 + len(code) for code in codes.values())
        total_bits_est = payload_bits + codebook_bits_est
        compressed_bytes = (total_bits_est + 7) // 8

        return CompressionResult(
            compression_id=self.info.id,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            payload={"codes": codes, "bitstring": bitstring},
            extra={
                "unique_symbols": len(codes),
                "payload_bits": payload_bits,
                "payload_bytes_only": payload_bytes,
                "codebook_bits_est": codebook_bits_est,
                "estimated_total_bits": total_bits_est,
            },
        )

