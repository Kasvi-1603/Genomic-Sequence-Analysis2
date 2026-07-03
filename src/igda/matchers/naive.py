from __future__ import annotations

from igda.core import AlgorithmInfo, MatchKind, MatchResult
from igda.matchers import utils


def _one_pattern(text: str, pat: str) -> tuple[list[dict[str, int]], int]:
    n, m = len(text), len(pat)
    if m == 0 or n < m:
        return [], 0
    out: list[dict[str, int]] = []
    comparisons = 0
    for i in range(0, n - m + 1):
        j = 0
        while j < m:
            comparisons += 1
            if text[i + j] != pat[j]:
                break
            j += 1
        if j == m:
            out.append({"start": i, "end": i + m, "pattern": pat})
    return out, comparisons


class NaiveMatcher:
    info = AlgorithmInfo(
        id="naive",
        name="Naive / brute-force",
        match_kind=MatchKind.EXACT,
        time_complexity="O(n·m) per pattern; multiple patterns: O(Σ|Pi|·n)",
        space_complexity="O(1) auxiliary (excluding output list)",
        notes="Trivial; baseline. Retries from every shift; no preprocessing reuse.",
        supports_multi_pattern=True,
    )

    def match(self, text: str, patterns: list[str], **kwargs: object) -> MatchResult:
        text, patterns = utils.sanitize_text_patterns(text, patterns, allow_empty_pattern=False)
        all_rows: list[dict[str, int | str]] = []
        total_c = 0
        for pat in patterns:
            rows, c = _one_pattern(text, pat)
            all_rows.extend(rows)  # type: ignore[assignment]
            total_c += c
        return MatchResult(
            algorithm_id=self.info.id,
            matches=all_rows,
            match_count=len(all_rows),
            extra={"character_comparisons": total_c},
        )
