"""Tests for ankideck.dedup."""

import pytest
from ankideck.reader import Card
from ankideck.dedup import find_duplicates, remove_duplicates


def _cards(*pairs):
    return [Card(front=f, back=b) for f, b in pairs]


def test_no_duplicates():
    cards = _cards(("a", "1"), ("b", "2"), ("c", "3"))
    assert find_duplicates(cards) == []


def test_finds_duplicate_pair():
    cards = _cards(("hello", "x"), ("world", "y"), ("hello", "z"))
    dupes = find_duplicates(cards)
    assert len(dupes) == 1
    assert dupes[0] == (2, 0)


def test_finds_multiple_duplicates():
    cards = _cards(("a", "1"), ("b", "2"), ("a", "3"), ("b", "4"))
    dupes = find_duplicates(cards)
    assert len(dupes) == 2


def test_dedup_case_insensitive():
    cards = _cards(("Hello", "x"), ("HELLO", "y"))
    dupes = find_duplicates(cards)
    assert len(dupes) == 1


def test_dedup_ignores_html():
    cards = _cards(("<b>hello</b>", "x"), ("hello", "y"))
    dupes = find_duplicates(cards)
    assert len(dupes) == 1


def test_dedup_whitespace_normalized():
    cards = _cards(("hello  world", "x"), ("hello world", "y"))
    dupes = find_duplicates(cards)
    assert len(dupes) == 1


def test_remove_duplicates_keeps_first():
    cards = _cards(("a", "1"), ("b", "2"), ("a", "3"))
    result = remove_duplicates(cards, keep="first")
    assert len(result) == 2
    assert result[0].back == "1"


def test_remove_duplicates_keeps_last():
    cards = _cards(("a", "1"), ("b", "2"), ("a", "3"))
    result = remove_duplicates(cards, keep="last")
    assert len(result) == 2
    kept_a = next(c for c in result if c.front == "a")
    assert kept_a.back == "3"


def test_remove_duplicates_preserves_order():
    cards = _cards(("c", "3"), ("a", "1"), ("b", "2"), ("a", "dup"))
    result = remove_duplicates(cards)
    assert [c.front for c in result] == ["c", "a", "b"]


def test_remove_duplicates_by_back():
    cards = _cards(("a", "same"), ("b", "same"), ("c", "other"))
    result = remove_duplicates(cards, key="back")
    assert len(result) == 2


def test_remove_duplicates_invalid_keep():
    with pytest.raises(ValueError):
        remove_duplicates([], keep="middle")


def test_empty_list():
    assert find_duplicates([]) == []
    assert remove_duplicates([]) == []


def test_single_card():
    cards = _cards(("a", "b"))
    assert find_duplicates(cards) == []
    assert len(remove_duplicates(cards)) == 1
