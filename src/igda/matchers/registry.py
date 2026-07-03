"""Select matcher by `algorithm_id` (for a future front end / API). All metadata lives in `AlgorithmInfo`."""

from __future__ import annotations

from typing import Any

from igda.core import AlgorithmInfo, MatchResult
from igda.matchers.aho_corasick import AhoCorasickMatcher
from igda.matchers.base import Matcher
from igda.matchers.edit_distance import EditDistanceMatcher
from igda.matchers.horspool import HorspoolMatcher
from igda.matchers.kmp import KmpMatcher
from igda.matchers.naive import NaiveMatcher

_REGISTRY: dict[str, Matcher] = {
    "naive": NaiveMatcher(),
    "kmp": KmpMatcher(),
    "horspool": HorspoolMatcher(),
    "ahocorasick": AhoCorasickMatcher(),
    "edit_distance": EditDistanceMatcher(),
}


def list_algorithms() -> list[AlgorithmInfo]:
    """Front end: populate dropdown; report: print complexity table."""
    return [m.info for m in _REGISTRY.values()]


def list_algorithm_ids() -> list[str]:
    return list(_REGISTRY.keys())


def get_matcher(algorithm_id: str) -> Matcher:
    if algorithm_id not in _REGISTRY:
        raise KeyError(
            f"Unknown algorithm_id={algorithm_id!r}. Choose one of: {', '.join(_REGISTRY)}"
        )
    return _REGISTRY[algorithm_id]


def run_match(algorithm_id: str, text: str, patterns: list[str], **kwargs: Any) -> MatchResult:
    """
    One entry for backend services: O(1) registry lookup, then `match`.

    *Exact* algorithms ignore `max_edits`. *edit_distance* uses `max_edits` (default 0).
    """
    m = get_matcher(algorithm_id)
    return m.match(text, patterns, **kwargs)
