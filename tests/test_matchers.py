from __future__ import annotations

import pytest

from igda.matchers import list_algorithm_ids, run_match


def test_list_ids_covers_syllabus() -> None:
    ids = set(list_algorithm_ids())
    for need in ("naive", "kmp", "horspool", "ahocorasick", "edit_distance"):
        assert need in ids


def test_exact_same_matches_naive_kmp() -> None:
    t = "abxabcabcabz"
    p = ["abc"]
    a = run_match("naive", t, p)
    b = run_match("kmp", t, p)
    assert a.match_count == b.match_count == 2
    assert {m["start"] for m in a.matches} == {3, 6}  # "abc" at 3-5 and 6-8


def test_ac_two_patterns() -> None:
    t = "abracadabra"
    p = ["abra", "cad"]
    r = run_match("ahocorasick", t, p)
    # "abra" occurs at 0 and 7; "cad" at 3 — three reported hits
    assert r.match_count == 3


def test_edit_distance_zero_is_exact() -> None:
    t = "acgtacg"
    p = ["acg"]
    r = run_match("edit_distance", t, p, max_edits=0)
    assert r.match_count == 2


def test_edit_distance_allows_mismatch() -> None:
    t = "acgt"
    p = ["acgt"]  # exact
    r0 = run_match("edit_distance", t, p, max_edits=0)
    assert r0.match_count == 1
    t2 = "acgT"  # one substitution (last T vs t) for case-sensitive alphabet
    r1 = run_match("edit_distance", t2, p, max_edits=1)
    assert r1.match_count == 1


def test_unknown_algorithm() -> None:
    with pytest.raises(KeyError):
        run_match("not_real", "a", ["a"])
