"""Tests for read_cards_json in ankideck.reader."""

import json
import jsonschema
import pytest

from ankideck.reader import Card, _wrap_clickwords


def test_sample_file_is_schema_valid():
    with open("schemas/card.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    with open("samples/sample_vocabulary.json", encoding="utf-8") as f:
        data = json.load(f)
    jsonschema.validate(data, schema)


def test_card_tts_examples_defaults_empty():
    c = Card(front="a", back="b")
    assert c.tts_examples == []


def test_card_tts_examples_independent_per_instance():
    a = Card(front="a", back="b")
    b = Card(front="c", back="d")
    a.tts_examples.append("x")
    assert b.tts_examples == []


def test_wrap_clickwords_wraps_each_word():
    html = _wrap_clickwords("Le chat dort")
    assert html.count('class="clickword"') == 3
    assert 'data-word="chat"' in html


def test_wrap_clickwords_strips_punctuation_from_data_word():
    html = _wrap_clickwords("Bonjour!")
    assert 'data-word="bonjour"' in html
    assert ">Bonjour!</span>" in html  # visible text keeps punctuation


def test_wrap_clickwords_preserves_hyphens():
    html = _wrap_clickwords("par-dessus")
    assert 'data-word="par-dessus"' in html


def test_wrap_clickwords_preserves_whitespace_between_words():
    html = _wrap_clickwords("Le chat")
    assert "</span> <span" in html
