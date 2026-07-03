from __future__ import annotations

from igda.core import AlgorithmInfo, MatchKind, MatchResult
from igda.matchers import utils


def _lps(pattern: str) -> list[int]:
    m = len(pattern)
    lps = [0] * m
    length = 0
    i = 1
    while i < m:
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        else:
            if length > 0:
                length = lps[length - 1]
            else:
                lps[i] = 0
                i += 1
    return lps


def _kmp_one(text: str, pat: str) -> tuple[list[dict[str, int | str]], int]:
    n, m = len(text), len(pat)
    if m == 0 or n < m:
        return [], 0
    lps = _lps(pat)
    out: list[dict[str, int | str]] = []
    comparisons = 0
    i = 0
    j = 0
    # Classic driver (cf. e.g. Knuth 1977 / standard texts): do not "mismatch" after a
    # successful partial advance — only backtrack on actual mismatch.
    while i < n:
        if j < m and text[i] == pat[j]:
            comparisons += 1
            i += 1
            j += 1
        if j == m:
            start = i - m
            out.append({"start": start, "end": start + m, "pattern": pat})
            j = lps[j - 1] if m else 0
        elif i < n and (j == 0 or text[i] != pat[j]):
            comparisons += 1
            if j:
                j = lps[j - 1]
            else:
                i += 1
    return out, comparisons


class KmpMatcher:
    info = AlgorithmInfo(
        id="kmp",
        name="Knuth–Morris–Pratt (KMP)",
        match_kind=MatchKind.EXACT,
        time_complexity="O(n + m) per pattern; multi-pattern: O(n·t + Σ|Pi|) where t = #patterns",
        space_complexity="O(m) for LPS table; total O(max |Pi|) if run sequentially",
        notes="Preprocesses the pattern: avoids rescan of matched prefix after mismatch.",
        supports_multi_pattern=True,
    )

    def match(self, text: str, patterns: list[str], **kwargs: object) -> MatchResult:
        text, patterns = utils.sanitize_text_patterns(text, patterns, allow_empty_pattern=False)
        rows: list[dict[str, int | str]] = []
        total = 0
        for pat in patterns:
            r, c = _kmp_one(text, pat)
            rows.extend(r)
            total += c
        return MatchResult(
            algorithm_id=self.info.id,
            matches=rows,
            match_count=len(rows),
            extra={"character_comparisons": total},
        )
