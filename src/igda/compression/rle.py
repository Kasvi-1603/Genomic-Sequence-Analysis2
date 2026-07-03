from __future__ import annotations

from igda.core import CompressionInfo, CompressionKind, CompressionResult


def _encode_runs(text: str) -> list[tuple[str, int]]:
    if not text:
        return []
    runs: list[tuple[str, int]] = []
    cur = text[0]
    cnt = 1
    for ch in text[1:]:
        if ch == cur:
            cnt += 1
        else:
            runs.append((cur, cnt))
            cur = ch
            cnt = 1
    runs.append((cur, cnt))
    return runs


class RleCompressor:
    info = CompressionInfo(
        id="rle",
        name="Run-Length Encoding (RLE)",
        compression_kind=CompressionKind.LOSSLESS,
        time_complexity="O(n)",
        space_complexity="O(r) runs",
        notes="Best when data has long repeated runs. Can expand on high-entropy text.",
    )

    def compress(self, text: str) -> CompressionResult:
        runs = _encode_runs(text)
        original_bytes = len(text.encode("utf-8"))
        # Store each run as (char:1 byte, count:4 bytes) in this estimator.
        compressed_bytes = len(runs) * 5
        return CompressionResult(
            compression_id=self.info.id,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            payload=runs,
            extra={"run_count": len(runs)},
        )

