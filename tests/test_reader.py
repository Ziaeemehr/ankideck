"""Tests for ankideck.reader."""

import pytest
from ankideck.reader import read_cards, Card


def test_tab_separated(tmp_csv):
    path = tmp_csv("cards.tsv", "bonjour\thello\nmerci\tthank you\n")
    cards = read_cards(path)
    assert len(cards) == 2
    assert cards[0].front == "bonjour"
    assert cards[0].back == "hello"
    assert cards[1].front == "merci"


def test_comma_separated(tmp_csv):
    path = tmp_csv("cards.csv", "chat,cat\nchien,dog\n")
    cards = read_cards(path, delimiter=",")
    assert len(cards) == 2
    assert cards[0].front == "chat"
    assert cards[0].back == "cat"


def test_semicolon_separated(tmp_csv):
    path = tmp_csv("cards.csv", "chat;cat\nchien;dog\n")
    cards = read_cards(path)
    assert len(cards) == 2
    assert cards[0].front == "chat"


def test_auto_detect_delimiter_tab(tmp_csv):
    path = tmp_csv("cards.tsv", "a\tb\nc\td\n")
    cards = read_cards(path)
    assert cards[0].front == "a"
    assert cards[0].back == "b"


def test_header_row_auto_detected(tmp_csv):
    path = tmp_csv("cards.tsv", "Front\tBack\nbonjour\thello\n")
    cards = read_cards(path)
    assert len(cards) == 1
    assert cards[0].front == "bonjour"
    assert cards[0].back == "hello"


def test_header_case_insensitive(tmp_csv):
    path = tmp_csv("cards.tsv", "FRONT\tBACK\nfoo\tbar\n")
    cards = read_cards(path)
    assert len(cards) == 1
    assert cards[0].front == "foo"


def test_explicit_no_header(tmp_csv):
    path = tmp_csv("cards.tsv", "front\tback\nfoo\tbar\n")
    cards = read_cards(path, has_header=False)
    assert len(cards) == 2
    assert cards[0].front == "front"


def test_tags_column(tmp_csv):
    path = tmp_csv("cards.tsv", "Front\tBack\tTags\nfoo\tbar\ta1 b1\n")
    cards = read_cards(path)
    assert cards[0].tags == ["a1", "b1"]


def test_tags_column_no_header(tmp_csv):
    path = tmp_csv("cards.tsv", "foo\tbar\ta1 b1\n")
    cards = read_cards(path, has_header=False, tag_col=2)
    assert cards[0].tags == ["a1", "b1"]


def test_empty_rows_skipped(tmp_csv):
    path = tmp_csv("cards.tsv", "a\tb\n\n\nc\td\n")
    cards = read_cards(path, has_header=False)
    assert len(cards) == 2


def test_short_rows_skipped(tmp_csv):
    path = tmp_csv("cards.tsv", "only_front\na\tb\n")
    cards = read_cards(path, has_header=False)
    assert len(cards) == 1
    assert cards[0].front == "a"


def test_whitespace_stripped(tmp_csv):
    path = tmp_csv("cards.tsv", "  hello  \t  world  \n")
    cards = read_cards(path, has_header=False)
    assert cards[0].front == "hello"
    assert cards[0].back == "world"


def test_empty_file(tmp_csv):
    path = tmp_csv("empty.tsv", "")
    cards = read_cards(path)
    assert cards == []


def test_card_dataclass():
    card = Card(front="a", back="b")
    assert card.tags == []
    card2 = Card(front="a", back="b", tags=["x"])
    assert card2.tags == ["x"]
