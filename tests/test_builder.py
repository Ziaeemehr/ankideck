"""Tests for ankideck.builder."""

import json
import os
import pytest
from ankideck.reader import Card
from ankideck.builder import (
    build_deck, write_apkg, generate_tts, _strip_tts_placeholders,
    BASIC_MODEL, JSON_MODEL,
)
import ankideck.tts as tts_module


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


def test_build_deck_default_note_type_uses_basic_model():
    cards = _cards(("a", "1"))
    deck = build_deck("T", cards)
    assert deck.notes[0].model.name == "Basic"


def test_build_deck_json_note_type_uses_basicjson_model():
    cards = [Card(front="chat", back="gato", note_type="json")]
    deck = build_deck("T", cards)
    assert deck.notes[0].model.name == "BasicJson"


def test_build_deck_mixed_note_types_in_one_deck():
    cards = [
        Card(front="a", back="1"),
        Card(front="b", back="2", note_type="json"),
    ]
    deck = build_deck("T", cards)
    assert deck.notes[0].model.name == "Basic"
    assert deck.notes[1].model.name == "BasicJson"


def test_json_model_has_clickword_css():
    assert ".clickword" in JSON_MODEL.css
    assert "cursor: pointer" in JSON_MODEL.css


def test_json_model_template_has_popup_script():
    afmt = JSON_MODEL.templates[0]["afmt"]
    assert "clickword" in afmt
    assert "openReverso" in afmt
    assert "openDict" in afmt


def test_basic_model_unchanged_by_json_model_addition():
    assert BASIC_MODEL.name == "Basic"
    assert ".clickword" not in BASIC_MODEL.css


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


def test_strip_tts_placeholders_removes_all():
    text = '<div class="example">Le chat dort. {{TTS_EX_0}}</div><div class="example">Il joue. {{TTS_EX_1}}</div>'
    result = _strip_tts_placeholders(text)
    assert "{{TTS_EX_0}}" not in result
    assert "{{TTS_EX_1}}" not in result
    assert "Le chat dort." in result


def test_strip_tts_placeholders_no_placeholders_unchanged():
    text = "<div>plain text</div>"
    assert _strip_tts_placeholders(text) == text


def test_generate_tts_is_public(tmp_path, monkeypatch):
    """generate_tts (renamed from the former private _generate_tts) is a
    public, importable, directly-callable function."""
    def fake_make_tts(sentences, filename, cache_dir, lang="fr"):
        out_path = os.path.join(cache_dir, filename)
        with open(out_path, "wb") as f:
            f.write(b"fake-audio")
        return out_path

    monkeypatch.setattr(tts_module, "make_tts", fake_make_tts)

    card = Card(front="chien", back="", tts_front="chien")
    updated, media = generate_tts([card], "fr", str(tmp_path))
    assert len(updated) == 1
    assert "[sound:tts_front_0000.mp3]" in updated[0].front
    assert len(media) == 1


def test_generate_tts_fills_example_placeholders(tmp_path, monkeypatch):
    calls = []

    def fake_make_tts(sentences, filename, cache_dir, lang="fr"):
        calls.append(filename)
        out_path = os.path.join(cache_dir, filename)
        with open(out_path, "wb") as f:
            f.write(b"fake-audio")
        return out_path

    monkeypatch.setattr(tts_module, "make_tts", fake_make_tts)

    card = Card(
        front="chat",
        back=(
            '<div class="example">Le chat dort. {{TTS_EX_0}}</div>'
            '<div class="example">Il joue. {{TTS_EX_1}}</div>'
        ),
        tts_front="chat",
        tts_examples=["Le chat dort.", "Il joue."],
    )
    updated, media = generate_tts([card], "fr", str(tmp_path))

    assert "{{TTS_EX_0}}" not in updated[0].back
    assert "{{TTS_EX_1}}" not in updated[0].back
    assert "[sound:tts_ex_0000_00.mp3]" in updated[0].back
    assert "[sound:tts_ex_0000_01.mp3]" in updated[0].back
    assert len(media) == 3  # 1 front + 2 examples


def test_generate_tts_preserves_note_type(tmp_path, monkeypatch):
    def fake_make_tts(sentences, filename, cache_dir, lang="fr"):
        out_path = os.path.join(cache_dir, filename)
        with open(out_path, "wb") as f:
            f.write(b"fake-audio")
        return out_path

    monkeypatch.setattr(tts_module, "make_tts", fake_make_tts)

    card = Card(front="chat", back="1", tts_front="chat", note_type="json")
    updated, _ = generate_tts([card], "fr", str(tmp_path))
    assert updated[0].note_type == "json"


def test_write_apkg_strips_placeholders_without_tts(tmp_path):
    cards = [Card(
        front="chat",
        back='<div class="example">Le chat dort. {{TTS_EX_0}}</div>',
        tts_examples=["Le chat dort."],
    )]
    out = str(tmp_path / "test.apkg")
    write_apkg("Test", cards, out)  # no tts_lang passed
    assert os.path.exists(out)


def _note_model_ids(apkg_path):
    """Extract (note_flds, model_id) pairs from a built .apkg's collection."""
    import sqlite3
    import zipfile

    with zipfile.ZipFile(apkg_path) as zf:
        db_name = "collection.anki2" if "collection.anki2" in zf.namelist() else "collection.anki21"
        with zf.open(db_name) as db_file:
            data = db_file.read()
    tmp_db = os.path.join(os.path.dirname(apkg_path), "_extracted.anki2")
    with open(tmp_db, "wb") as f:
        f.write(data)
    conn = sqlite3.connect(tmp_db)
    try:
        rows = conn.execute("SELECT flds, mid FROM notes").fetchall()
    finally:
        conn.close()
    return rows


def test_write_apkg_json_note_type_uses_basicjson_model_without_tts(tmp_path):
    cards = [Card(front="chat", back="1", note_type="json")]
    out = str(tmp_path / "test.apkg")
    write_apkg("Test", cards, out)  # no tts_lang passed
    rows = _note_model_ids(out)
    assert len(rows) == 1
    assert rows[0][1] == JSON_MODEL.id


def test_write_apkg_basic_note_type_uses_basic_model_without_tts(tmp_path):
    cards = [Card(front="chat", back="1")]
    out = str(tmp_path / "test.apkg")
    write_apkg("Test", cards, out)  # no tts_lang passed
    rows = _note_model_ids(out)
    assert len(rows) == 1
    assert rows[0][1] == BASIC_MODEL.id


def test_cli_reads_json_input(tmp_path):
    from ankideck.builder import main as builder_main

    json_path = tmp_path / "cards.json"
    json_path.write_text(json.dumps({
        "cards": [{"type": "vocab", "front": "chat", "pos": "n.m.", "meaning_fa": "گربه"}],
    }), encoding="utf-8")
    out_path = tmp_path / "out.apkg"

    builder_main([str(json_path), "--deck", "Test", "-o", str(out_path)])

    assert out_path.exists()
