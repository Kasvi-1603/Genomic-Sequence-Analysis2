"""Contract every matcher must satisfy so a UI/API can pick one by `algorithm_id` uniformly."""

from __future__ import annotations

from typing import Any, Protocol

from igda.core import AlgorithmInfo, MatchResult


class Matcher(Protocol):
    """Duck-typed: concrete classes below implement `info` + `match`."""

    info: AlgorithmInfo

    def match(self, text: str, patterns: list[str], **kwargs: Any) -> MatchResult: ...
