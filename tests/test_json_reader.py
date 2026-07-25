"""Tests for read_cards_json in ankideck.reader."""

import json
import jsonschema
import pytest

from ankideck.reader import Card, _wrap_clickwords, _vocab_to_card, _grammar_to_card, read_cards_json


def test_sample_file_is_schema_valid():
    with open("src/ankideck/schemas/card.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    with open("samples/sample_vocabulary.json", encoding="utf-8") as f:
        data = json.load(f)
    jsonschema.validate(data, schema)


def test_card_tts_examples_defaults_empty():
    c = Card(front="a", back="b")
    assert c.tts_examples == []


def test_card_note_type_defaults_basic():
    c = Card(front="a", back="b")
    assert c.note_type == "basic"


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


def test_vocab_to_card_basic_fields():
    entry = {
        "type": "vocab",
        "front": "chat",
        "pos": "n.m.",
        "meaning_fa": "گربه",
        "meaning_en": "cat",
        "tags": ["ch01"],
    }
    c = _vocab_to_card(entry)
    assert 'class="clickword"' in c.front
    assert 'data-word="chat"' in c.front
    assert c.tts_front == "chat"
    assert "n.m." in c.back
    assert "گربه" in c.back
    assert "cat" in c.back
    assert c.tags == ["ch01"]
    assert c.tts_examples == []


def test_vocab_to_card_omits_optional_meaning_en_when_absent():
    entry = {"type": "vocab", "front": "chat", "pos": "n.m.", "meaning_fa": "گربه"}
    c = _vocab_to_card(entry)
    assert "EN:" not in c.back


def test_vocab_to_card_synonyms_antonyms_clickable_no_tts():
    entry = {
        "type": "vocab", "front": "chat", "pos": "n.m.", "meaning_fa": "گربه",
        "synonyms": ["matou"], "antonyms": ["chien"],
    }
    c = _vocab_to_card(entry)
    assert 'data-word="matou"' in c.back
    assert 'data-word="chien"' in c.back
    assert c.tts_examples == []  # synonyms/antonyms never get audio


def test_vocab_to_card_multiple_examples_produce_ordered_placeholders():
    entry = {
        "type": "vocab", "front": "chat", "pos": "n.m.", "meaning_fa": "گربه",
        "examples": ["Le chat dort.", "Le chat joue."],
    }
    c = _vocab_to_card(entry)
    assert c.tts_examples == ["Le chat dort.", "Le chat joue."]
    assert "{{TTS_EX_0}}" in c.back
    assert "{{TTS_EX_1}}" in c.back
    assert c.back.index("{{TTS_EX_0}}") < c.back.index("{{TTS_EX_1}}")
    assert 'data-word="dort"' in c.back


def test_grammar_to_card_basic():
    entry = {
        "type": "grammar",
        "front": "Elle est partie tôt.",
        "explanation": "Verbes de mouvement -> être.",
        "tags": ["ch18"],
    }
    c = _grammar_to_card(entry)
    assert 'class="clickword"' in c.front
    assert c.tts_front == "Elle est partie tôt."
    assert "Verbes de mouvement" in c.back
    assert 'class="clickword"' not in c.back.split("</div>")[0]  # explanation not clickable
    assert c.tts_examples == []


def test_grammar_to_card_extra_examples():
    entry = {
        "type": "grammar",
        "front": "Elle est partie tôt.",
        "explanation": "Verbes de mouvement -> être.",
        "examples": ["Nous sommes arrivés hier."],
    }
    c = _grammar_to_card(entry)
    assert c.tts_examples == ["Nous sommes arrivés hier."]
    assert "{{TTS_EX_0}}" in c.back
    assert 'data-word="arrivés"' in c.back


def _write_json(tmp_path, data, name="cards.json"):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_read_cards_json_mixed_types(tmp_path):
    path = _write_json(tmp_path, {
        "chapter": "test",
        "cards": [
            {"type": "vocab", "front": "chat", "pos": "n.m.", "meaning_fa": "گربه"},
            {"type": "grammar", "front": "Elle est partie.", "explanation": "..."},
        ],
    })
    cards = read_cards_json(path)
    assert len(cards) == 2
    assert cards[0].tts_front == "chat"
    assert cards[1].tts_front == "Elle est partie."
    assert cards[0].note_type == "json"
    assert cards[1].note_type == "json"


def test_read_cards_json_missing_required_field_raises(tmp_path):
    path = _write_json(tmp_path, {
        "cards": [{"type": "vocab", "front": "chat", "meaning_fa": "گربه"}],  # missing pos
    })
    with pytest.raises(ValueError, match="pos"):
        read_cards_json(path)


def test_read_cards_json_invalid_type_raises(tmp_path):
    path = _write_json(tmp_path, {
        "cards": [{"type": "adjective", "front": "chat"}],
    })
    with pytest.raises(ValueError):
        read_cards_json(path)


def test_read_cards_json_empty_cards_list(tmp_path):
    path = _write_json(tmp_path, {"cards": []})
    assert read_cards_json(path) == []
