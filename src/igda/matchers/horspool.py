from __future__ import annotations

from collections import defaultdict

from igda.core import AlgorithmInfo, MatchKind, MatchResult
from igda.matchers import utils


def _shift_table(pattern: str) -> dict[str, int]:
    """Boyer–Moore–Horspool: bad-symbol on pattern[0..m-2], default m."""
    m = len(pattern)
    t: dict[str, int] = defaultdict(lambda: m)
    if m <= 1:
        return dict(t)
    for i in range(m - 1):
        t[pattern[i]] = m - 1 - i
    return dict(t)


def _horspool_one(text: str, pat: str) -> tuple[list[dict[str, int | str]], int]:
    n, m = len(text), len(pat)
    if m == 0 or n < m:
        return [], 0
    table = _shift_table(pat)
    out: list[dict[str, int | str]] = []
    comparisons = 0
    i = 0
    while i <= n - m:
        j = m - 1
        while j >= 0:
            comparisons += 1
            if text[i + j] != pat[j]:
                break
            j -= 1
        if j < 0:
            out.append({"start": i, "end": i + m, "pattern": pat})
            i += 1
        else:
            shift = table.get(text[i + m - 1], m)
            i += shift
    return out, comparisons


class HorspoolMatcher:
    info = AlgorithmInfo(
        id="horspool",
        name="Boyer–Moore–Horspool",
        match_kind=MatchKind.EXACT,
        time_complexity="O(n·m) worst; often sublinear on large alphabets in practice; multi: ~O(t·n) worst per pattern",
        space_complexity="O(|Σ|) if dense dict; at most O(m) unique chars in table",
        notes="Jumps by scanning end of window first. Multiple patterns = separate scans (not one-pass).",
        supports_multi_pattern=True,
    )

    def match(self, text: str, patterns: list[str], **kwargs: object) -> MatchResult:
        text, patterns = utils.sanitize_text_patterns(text, patterns, allow_empty_pattern=False)
        rows: list[dict[str, int | str]] = []
        total = 0
        for pat in patterns:
            r, c = _horspool_one(text, pat)
            rows.extend(r)
            total += c
        return MatchResult(
            algorithm_id=self.info.id,
            matches=rows,
            match_count=len(rows),
            extra={"character_comparisons": total},
        )
