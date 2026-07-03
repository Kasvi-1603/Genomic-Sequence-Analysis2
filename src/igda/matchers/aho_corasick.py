from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from igda.core import AlgorithmInfo, MatchKind, MatchResult
from igda.matchers import utils


@dataclass
class _ACNode:
    nxt: dict[str, int] = field(default_factory=dict)
    fail: int = 0
    out: list[int] = field(default_factory=list)  # pattern ids ending *exactly* at this node, then merged
    base: list[int] = field(default_factory=list)  # pattern ids ending exactly here before merge


def _build_trie(patterns: list[str]) -> list[_ACNode]:
    g: list[_ACNode] = [_ACNode()]
    for pid, w in enumerate(patterns):
        s = 0
        for ch in w:
            if ch not in g[s].nxt:
                g[s].nxt[ch] = len(g)
                g.append(_ACNode())
            s = g[s].nxt[ch]
        g[s].base.append(pid)
    return g


def _build_fail(g: list[_ACNode]) -> None:
    q: deque[int] = deque()
    g[0].fail = 0
    for _ch, u in g[0].nxt.items():
        g[u].fail = 0
        q.append(u)
    while q:
        r = q.popleft()
        for ch, u in g[r].nxt.items():
            q.append(u)
            f = g[r].fail
            while f and ch not in g[f].nxt:
                f = g[f].fail
            g[u].fail = g[f].nxt[ch] if f and ch in g[f].nxt else g[0].nxt.get(ch, 0)


def _merge_out_bfs(g: list[_ACNode]) -> None:
    """out[u] = base[u] ∪ out[fail(u)]; BFS so fail is always processed before u."""
    order: list[int] = []
    q: deque[int] = deque([0])
    while q:
        u = q.popleft()
        order.append(u)
        for _c, v in g[u].nxt.items():
            q.append(v)
    for u in order:
        g[u].out = list(g[u].base)
        if u == 0:
            continue
        for p in g[g[u].fail].out:
            if p not in g[u].out:
                g[u].out.append(p)


def _search(text: str, g: list[_ACNode], patterns: list[str]) -> tuple[list[dict[str, int | str]], int]:
    out: list[dict[str, int | str]] = []
    steps = 0
    state = 0
    for i, c in enumerate(text):
        while state and c not in g[state].nxt:
            steps += 1
            state = g[state].fail
        if c in g[state].nxt:
            steps += 1
            state = g[state].nxt[c]
        for pid in g[state].out:
            w = patterns[pid]
            e = i + 1
            s = e - len(w)
            out.append({"start": s, "end": e, "pattern": w, "pattern_index": pid})
    return out, steps


def _run(text: str, patterns: list[str]) -> tuple[list[dict[str, int | str]], int]:
    g = _build_trie(patterns)
    _build_fail(g)
    _merge_out_bfs(g)
    return _search(text, g, patterns)


class AhoCorasickMatcher:
    info = AlgorithmInfo(
        id="ahocorasick",
        name="Aho–Corasick (multi-pattern automaton)",
        match_kind=MatchKind.EXACT,
        time_complexity="O(n + m + z) with n = |text|, m = Σ|Pi|, z = # output hits",
        space_complexity="O(m) for trie + fail links; edges bounded by m over alphabet",
        notes="One left-to-right pass over the text. Strong when many patterns. Same index may report multiple pattern ids.",
        supports_multi_pattern=True,
    )

    def match(self, text: str, patterns: list[str], **kwargs: object) -> MatchResult:
        text, patterns = utils.sanitize_text_patterns(text, patterns, allow_empty_pattern=False)
        if not patterns:
            return MatchResult(algorithm_id=self.info.id, matches=[], match_count=0, extra={})
        rows, stats = _run(text, patterns)
        return MatchResult(
            algorithm_id=self.info.id,
            matches=rows,
            match_count=len(rows),
            extra={"transition_steps": stats},
        )
