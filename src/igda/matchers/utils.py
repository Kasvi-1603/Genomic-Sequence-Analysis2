from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def sanitize_text_patterns(
    text: str, patterns: list[str], *, allow_empty_pattern: bool
) -> tuple[str, list[str]]:
    if not allow_empty_pattern:
        patterns = [p for p in patterns if p]
    return text, patterns
