from __future__ import annotations

from igda.core import AlgorithmInfo, MatchKind, MatchResult
from igda.matchers import utils


def levenshtein(a: str, b: str) -> int:
    """Wagner–Fischer: O(len(a)*len(b)) time, O(len(b)) space (two rows as one in-place with prev)."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    cur = [0] * (n + 1)
    for i in range(1, m + 1):
        cur[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(
                cur[j - 1] + 1,
                prev[j] + 1,
                prev[j - 1] + cost,
            )
        prev, cur = cur, prev
    return prev[n]


def _sliding_equal_length_windows(
    text: str, pat: str, max_edits: int
) -> list[dict[str, int | str]]:
    n, m = len(text), len(pat)
    if m == 0 or n < m:
        return []
    out: list[dict[str, int | str]] = []
    for i in range(0, n - m + 1):
        w = text[i : i + m]
        d = levenshtein(w, pat)
        if d <= max_edits:
            out.append(
                {
                    "start": i,
                    "end": i + m,
                    "pattern": pat,
                    "edit_distance": d,
                }
            )
    return out


class EditDistanceMatcher:
    info = AlgorithmInfo(
        id="edit_distance",
        name="Levenshtein (≈ match with bounded edits)",
        match_kind=MatchKind.APPROXIMATE,
        time_complexity="O(n·m²) in this windowed form: (n−m+1) windows × O(m²) DP each (simpler DP; can be improved)",
        space_complexity="O(m) for one DP column/row in `levenshtein`",
        notes="For DAA, distinct from exact matchers: same-length windows vs pattern; set max_edits in kwargs.",
        supports_multi_pattern=True,
    )

    def match(self, text: str, patterns: list[str], **kwargs: object) -> MatchResult:
        max_edits = int(kwargs.get("max_edits", 0))
        text, patterns = utils.sanitize_text_patterns(text, patterns, allow_empty_pattern=False)
        rows: list[dict[str, int | str]] = []
        for pat in patterns:
            rows.extend(_sliding_equal_length_windows(text, pat, max_edits))
        return MatchResult(
            algorithm_id=self.info.id,
            matches=rows,
            match_count=len(rows),
            extra={"max_edits": max_edits},
        )
