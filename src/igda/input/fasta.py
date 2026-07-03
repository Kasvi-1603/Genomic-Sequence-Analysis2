"""FASTA/text ingestion helpers."""

from __future__ import annotations

from pathlib import Path


def load_fasta_sequence(path: str | Path) -> str:
    """
    Load a FASTA file and return sequence text as one continuous string.

    Rules kept intentionally simple for coursework:
    - ignore header lines beginning with '>'
    - ignore blank lines
    - keep character case as-is (your current data is already uppercase)
    """
    p = Path(path)
    data = p.read_text(encoding="utf-8")
    chunks: list[str] = []
    for line in data.splitlines():
        s = line.strip()
        if not s or s.startswith(">"):
            continue
        chunks.append(s)
    return "".join(chunks)


def load_plain_text(path: str | Path) -> str:
    """Load any plain text file as-is (useful for non-FASTA experiments)."""
    return Path(path).read_text(encoding="utf-8")

