"""Tests for ankideck.builder."""

import os
import pytest
from ankideck.reader import Card
from ankideck.builder import build_deck, write_apkg


def _cards(*pairs):
    return [Card(front=f, back=b) for f, b in pairs]


def test_build_deck_returns_deck():
    import genanki
    cards = _cards(("a", "1"), ("b", "2"))
    deck = build_deck("Test Deck", cards)
    assert isinstance(deck, genanki.Deck)
    assert deck.name == "Test Deck"


def test_build_deck_note_count():
    import genanki
    cards = _cards(("a", "1"), ("b", "2"), ("c", "3"))
    deck = build_deck("Test", cards)
    assert len(deck.notes) == 3


def test_build_deck_tags():
    cards = [Card(front="a", back="1", tags=["french", "a1"])]
    deck = build_deck("T", cards)
    assert "french" in deck.notes[0].tags
    assert "a1" in deck.notes[0].tags


def test_write_apkg_creates_file(tmp_path):
    cards = _cards(("hello", "bonjour"), ("cat", "chat"))
    out = str(tmp_path / "test.apkg")
    n = write_apkg("Test", cards, out)
    assert os.path.exists(out)
    assert n == 2


def test_write_apkg_deduplicates_by_default(tmp_path):
    cards = _cards(("a", "1"), ("b", "2"), ("a", "3"))
    out = str(tmp_path / "test.apkg")
    n = write_apkg("Test", cards, out)
    assert n == 2


def test_write_apkg_no_dedup(tmp_path):
    cards = _cards(("a", "1"), ("b", "2"), ("a", "3"))
    out = str(tmp_path / "test.apkg")
    n = write_apkg("Test", cards, out, check_duplicates=False)
    assert n == 3


def test_write_apkg_appending(tmp_path):
    """Combining base + new cards simulates appending to an existing deck."""
    base = _cards(("a", "1"), ("b", "2"))
    new = _cards(("c", "3"), ("a", "duplicate"))
    combined = base + new
    out = str(tmp_path / "test.apkg")
    n = write_apkg("Test", combined, out)
    # "a" is duplicated, so only 3 unique cards
    assert n == 3


def test_write_apkg_adds_apkg_extension(tmp_path):
    cards = _cards(("a", "1"))
    out = str(tmp_path / "nodot")
    write_apkg("T", cards, out + ".apkg")
    assert os.path.exists(out + ".apkg")


def test_write_apkg_empty_cards(tmp_path):
    out = str(tmp_path / "empty.apkg")
    n = write_apkg("Empty", [], out)
    assert n == 0
    assert os.path.exists(out)
