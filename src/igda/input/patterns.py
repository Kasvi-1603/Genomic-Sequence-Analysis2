"""Pattern ingestion helpers."""

from __future__ import annotations

from pathlib import Path


def _normalize_tokens(raw: list[str], *, dedupe: bool) -> list[str]:
    # Trim, drop empties, optional stable de-duplication.
    out = [t.strip() for t in raw if t.strip()]
    if not dedupe:
        return out
    seen: set[str] = set()
    deduped: list[str] = []
    for token in out:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def load_patterns_file(path: str | Path, *, dedupe: bool = True) -> list[str]:
    """
    Load patterns from a file.

    Supported style:
    - one pattern per line
    - optional comma-separated entries on a line
    - lines starting with '#' are treated as comments
    """
    txt = Path(path).read_text(encoding="utf-8")
    raw: list[str] = []
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [p.strip() for p in s.split(",")]
        raw.extend(parts)
    return _normalize_tokens(raw, dedupe=dedupe)


def normalize_patterns(patterns: list[str], *, dedupe: bool = True) -> list[str]:
    """Normalize user-provided in-memory patterns using same rules as file input."""
    return _normalize_tokens(list(patterns), dedupe=dedupe)

