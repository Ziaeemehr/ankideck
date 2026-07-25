# JSON Card Input Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a JSON input format (dictionary-style vocab cards + grammar-rule cards, multiple examples, synonyms/antonyms) to `ankideck`, alongside the existing xlsx pipeline, with a clickable-word Anki template that no longer relies on text-sniffing.

**Architecture:** A new `read_cards_json()` in `reader.py` validates each chapter's JSON file against a JSON Schema, then converts each entry into the same `Card` dataclass the rest of the package (`builder.py`, `dedup.py`) already knows how to write to `.apkg`. The only new `Card` field is `tts_examples: List[str]` (plain French example texts). The reader bakes `.clickword` spans directly into the HTML at build time, so `builder.py`'s TTS step just fills in audio + strips markup, and the Anki template's JS only needs to attach click handlers — no text parsing anywhere.

**Tech Stack:** Python 3.8+, `jsonschema` (new dependency) for schema validation, existing `genanki`/`edge-tts`/`openpyxl` stack.

## Global Constraints

- No breaking changes to `read_cards`, `read_cards_excel`, or their CLI paths — JSON support is purely additive (per spec Non-goals).
- No new genanki `Model`/note type — cards keep using the existing Front/Back two-field Basic model (per spec Non-goals).
- `examples` entries are plain French strings only — no per-example translation fields (per spec §1).
- TTS audio is generated only for front content and French example sentences — never for meanings, synonyms/antonyms, or grammar explanations (per spec Goals).
- The plain delimited-text reader (`read_cards()`, `.tsv`/`.csv`/`.txt` support) stays in place for now — its removal was discussed and explicitly deferred to a separate follow-up, not part of this plan.

---

## File Structure

- `schemas/card.schema.json` — new. JSON Schema (draft-07) for the chapter JSON file shape.
- `samples/sample_vocabulary.json` — new. One vocab card + one grammar card, valid against the schema.
- `src/ankideck/reader.py` — modified. Add `tts_examples` field to `Card`; add `_wrap_clickwords`, `_vocab_to_card`, `_grammar_to_card`, `read_cards_json`.
- `src/ankideck/builder.py` — modified. Extend `_generate_tts` to handle `tts_examples`; add `_strip_tts_placeholders`; wire placeholder stripping into the no-TTS path of `write_apkg`; add `.json` dispatch to CLI `main()`.
- `tests/test_json_reader.py` — new.
- `tests/test_builder.py` — extended with TTS-example tests.
- `scripts/anki_card_type.md` — modified. New "Design 5" section.
- `PDF_TO_ANKI_PIPELINE.md` — modified. Step 4/5 updated to target JSON.
- `pyproject.toml` — modified. Add `jsonschema` dependency.

---

### Task 1: JSON Schema + sample file + dependency

**Files:**
- Create: `schemas/card.schema.json`
- Create: `samples/sample_vocabulary.json`
- Modify: `pyproject.toml`
- Test: `tests/test_json_reader.py` (schema-validity smoke test only — full reader tests come in Task 4)

**Interfaces:**
- Produces: `schemas/card.schema.json` on disk, loadable via `json.load`. Consumed by `read_cards_json` in Task 4 (loaded relative to `reader.py`'s own file location: `Path(__file__).resolve().parents[2] / "schemas" / "card.schema.json"`).

- [ ] **Step 1: Add the `jsonschema` dependency**

In `pyproject.toml`, add to the `dependencies` list (after `"openpyxl>=3.1.0",`):

```toml
    "jsonschema>=4.17.0",
```

- [ ] **Step 2: Install it**

Run: `pip install -e .`
Expected: installs `jsonschema` into the active environment (editable install already covers the rest of the package).

- [ ] **Step 3: Write the schema file**

Create `schemas/card.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Ankideck chapter card list",
  "type": "object",
  "required": ["cards"],
  "properties": {
    "chapter": {"type": "string"},
    "cards": {
      "type": "array",
      "items": {"$ref": "#/definitions/card"}
    }
  },
  "definitions": {
    "card": {
      "type": "object",
      "required": ["type", "front"],
      "properties": {
        "type": {"enum": ["vocab", "grammar"]},
        "front": {"type": "string", "minLength": 1},
        "tags": {"type": "array", "items": {"type": "string"}}
      },
      "allOf": [
        {
          "if": {"properties": {"type": {"const": "vocab"}}},
          "then": {
            "required": ["pos", "meaning_fa"],
            "properties": {
              "pos": {"type": "string", "minLength": 1},
              "meaning_fa": {"type": "string", "minLength": 1},
              "meaning_en": {"type": "string"},
              "synonyms": {"type": "array", "items": {"type": "string"}},
              "antonyms": {"type": "array", "items": {"type": "string"}},
              "examples": {"type": "array", "items": {"type": "string"}}
            }
          }
        },
        {
          "if": {"properties": {"type": {"const": "grammar"}}},
          "then": {
            "required": ["explanation"],
            "properties": {
              "explanation": {"type": "string", "minLength": 1},
              "examples": {"type": "array", "items": {"type": "string"}}
            }
          }
        }
      ]
    }
  }
}
```

- [ ] **Step 4: Write the sample file**

Create `samples/sample_vocabulary.json`:

```json
{
  "chapter": "05_Ch05_Les_vetements",
  "cards": [
    {
      "type": "vocab",
      "front": "une cravate",
      "pos": "n.f.",
      "meaning_fa": "کراوات",
      "meaning_en": "a tie",
      "synonyms": ["une écharpe"],
      "antonyms": [],
      "examples": ["Il porte une cravate rouge pour aller au bureau."],
      "tags": ["ch05"]
    },
    {
      "type": "grammar",
      "front": "Elle est partie tôt.",
      "explanation": "Les verbes de mouvement (aller, partir, sortir...) se conjuguent avec être au passé composé; le participe s'accorde avec le sujet.",
      "examples": ["Nous sommes arrivés hier."],
      "tags": ["ch18", "grammar"]
    }
  ]
}
```

- [ ] **Step 5: Write a failing smoke test**

Create `tests/test_json_reader.py`:

```python
"""Tests for read_cards_json in ankideck.reader."""

import json
import jsonschema
import pytest


def test_sample_file_is_schema_valid():
    with open("schemas/card.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    with open("samples/sample_vocabulary.json", encoding="utf-8") as f:
        data = json.load(f)
    jsonschema.validate(data, schema)
```

- [ ] **Step 6: Run it to verify it passes**

Run: `pytest tests/test_json_reader.py -v`
Expected: PASS (this only checks the schema/sample files agree; no reader code involved yet)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml schemas/card.schema.json samples/sample_vocabulary.json tests/test_json_reader.py
git commit -m "feat: add JSON card schema and sample file"
```

---

### Task 2: `Card.tts_examples` field + `_wrap_clickwords` helper

**Files:**
- Modify: `src/ankideck/reader.py`
- Test: `tests/test_json_reader.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Card.tts_examples: List[str]` (new field, default `[]`). `_wrap_clickwords(text: str) -> str` — used by Task 3.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_json_reader.py`:

```python
from ankideck.reader import Card, _wrap_clickwords


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_json_reader.py -v`
Expected: FAIL with `ImportError: cannot import name '_wrap_clickwords'` (and `Card` has no field `tts_examples` once that assertion is reached)

- [ ] **Step 3: Add the field and helper**

In `src/ankideck/reader.py`, add `import html` and `import re` is already imported? No — `re` is not currently imported in `reader.py` (`csv` is). Add `import html` and `import re` near the top with the other imports:

```python
import csv
import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
```

Add `tts_examples` to the `Card` dataclass:

```python
@dataclass
class Card:
    front: str
    back: str
    tags: List[str] = field(default_factory=list)
    tts_front: str = ""   # plain text for front audio (falls back to stripped front)
    tts_back: str = ""    # plain text for back audio (empty = no back audio)
    tts_examples: List[str] = field(default_factory=list)  # plain French example texts (JSON cards)
```

Add `_wrap_clickwords` near the bottom of the file (after the Excel section, before a new "JSON" section):

```python
# ---------------------------------------------------------------------------
# JSON (dictionary-style vocab / grammar cards)
# ---------------------------------------------------------------------------

def _wrap_clickwords(text: str) -> str:
    """Wrap each word of French text in a clickable span for the Anki template.

    Punctuation is stripped from data-word (used for dictionary/conjugation
    lookup URLs) but kept in the visible text.
    """
    tokens = re.split(r"(\s+)", text)
    parts = []
    for tok in tokens:
        if tok.strip() == "":
            parts.append(tok)
            continue
        clean = re.sub(r"[.,!?;:«»\"']", "", tok).lower()
        parts.append(
            f'<span class="clickword" data-word="{html.escape(clean)}">'
            f'{html.escape(tok)}</span>'
        )
    return "".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_json_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ankideck/reader.py tests/test_json_reader.py
git commit -m "feat: add Card.tts_examples field and clickword-wrapping helper"
```

---

### Task 3: `_vocab_to_card` and `_grammar_to_card`

**Files:**
- Modify: `src/ankideck/reader.py`
- Test: `tests/test_json_reader.py`

**Interfaces:**
- Consumes: `Card` (Task 2), `_wrap_clickwords(text: str) -> str` (Task 2).
- Produces: `_vocab_to_card(entry: dict) -> Card`, `_grammar_to_card(entry: dict) -> Card` — used by `read_cards_json` in Task 4. Both assume `entry` already passed schema validation (required keys present).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_json_reader.py`:

```python
from ankideck.reader import _vocab_to_card, _grammar_to_card


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_json_reader.py -v`
Expected: FAIL with `ImportError: cannot import name '_vocab_to_card'`

- [ ] **Step 3: Implement both functions**

Add to `src/ankideck/reader.py`, right after `_wrap_clickwords`:

```python
def _meta_line(label: str, value: str) -> str:
    return f"<div><b>{html.escape(label)}:</b> {html.escape(value)}</div>"


def _wordlist_line(label: str, words: List[str]) -> str:
    spans = ", ".join(_wrap_clickwords(w) for w in words)
    return f'<div><b>{html.escape(label)}:</b> {spans}</div>'


def _example_block(example_text: str, index: int) -> str:
    return (
        f'<div class="example">{_wrap_clickwords(example_text)} '
        f"{{{{TTS_EX_{index}}}}}</div>"
    )


def _vocab_to_card(entry: Dict) -> Card:
    """Build a Card from a schema-valid vocab entry (see schemas/card.schema.json)."""
    front_text = entry["front"]
    examples = entry.get("examples", [])

    back_parts = [
        _meta_line("POS", entry["pos"]),
        _meta_line("FA", entry["meaning_fa"]),
    ]
    meaning_en = entry.get("meaning_en", "")
    if meaning_en:
        back_parts.append(_meta_line("EN", meaning_en))
    synonyms = entry.get("synonyms", [])
    if synonyms:
        back_parts.append(_wordlist_line("Syn", synonyms))
    antonyms = entry.get("antonyms", [])
    if antonyms:
        back_parts.append(_wordlist_line("Ant", antonyms))
    for i, ex in enumerate(examples):
        back_parts.append(_example_block(ex, i))

    return Card(
        front=_wrap_clickwords(front_text),
        back="\n".join(back_parts),
        tags=list(entry.get("tags", [])),
        tts_front=front_text,
        tts_examples=list(examples),
    )


def _grammar_to_card(entry: Dict) -> Card:
    """Build a Card from a schema-valid grammar entry (see schemas/card.schema.json)."""
    front_text = entry["front"]
    examples = entry.get("examples", [])

    back_parts = [f'<div class="explanation">{html.escape(entry["explanation"])}</div>']
    for i, ex in enumerate(examples):
        back_parts.append(_example_block(ex, i))

    return Card(
        front=_wrap_clickwords(front_text),
        back="\n".join(back_parts),
        tags=list(entry.get("tags", [])),
        tts_front=front_text,
        tts_examples=list(examples),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_json_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ankideck/reader.py tests/test_json_reader.py
git commit -m "feat: build vocab and grammar Cards from JSON entries"
```

---

### Task 4: `read_cards_json` (validation + dispatch)

**Files:**
- Modify: `src/ankideck/reader.py`
- Test: `tests/test_json_reader.py`

**Interfaces:**
- Consumes: `_vocab_to_card`, `_grammar_to_card` (Task 3), `schemas/card.schema.json` (Task 1).
- Produces: `read_cards_json(path) -> List[Card]` — used by `builder.py` CLI in Task 6 and by pipeline scripts.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_json_reader.py`:

```python
from ankideck.reader import read_cards_json


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_json_reader.py -v`
Expected: FAIL with `ImportError: cannot import name 'read_cards_json'`

- [ ] **Step 3: Implement `read_cards_json`**

Add to `src/ankideck/reader.py`, after `_grammar_to_card`:

```python
def read_cards_json(path) -> List[Card]:
    """Read vocab/grammar cards from a chapter JSON file.

    Validates the file against schemas/card.schema.json before building
    any cards, raising ValueError with the failing card's location if the
    file doesn't conform.
    """
    import json
    import jsonschema
    from jsonschema.exceptions import best_match

    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "card.schema.json"
    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)

    validator = jsonschema.Draft7Validator(schema)
    error = best_match(validator.iter_errors(data))
    if error is not None:
        loc = "/".join(str(p) for p in error.absolute_path)
        raise ValueError(f"Invalid card JSON at '{loc}' in {path}: {error.message}")

    cards: List[Card] = []
    for entry in data.get("cards", []):
        if entry["type"] == "vocab":
            cards.append(_vocab_to_card(entry))
        else:
            cards.append(_grammar_to_card(entry))
    return cards
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_json_reader.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `pytest -q`
Expected: all tests PASS (existing xlsx/text-reader/builder/dedup tests untouched)

- [ ] **Step 6: Commit**

```bash
git add src/ankideck/reader.py tests/test_json_reader.py
git commit -m "feat: add read_cards_json with schema validation"
```

---

### Task 5: `builder.py` — multi-example TTS + placeholder stripping

**Files:**
- Modify: `src/ankideck/builder.py`
- Test: `tests/test_builder.py`

**Interfaces:**
- Consumes: `Card.tts_examples` (Task 2), placeholder format `{{TTS_EX_i}}` (Task 3).
- Produces: `_generate_tts` now also fills `{{TTS_EX_i}}` placeholders; `_strip_tts_placeholders(text: str) -> str`; `write_apkg` strips leftover placeholders when `tts_lang` is not given.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_builder.py`:

```python
import ankideck.tts as tts_module
from ankideck.builder import _generate_tts, _strip_tts_placeholders


def test_strip_tts_placeholders_removes_all():
    text = '<div class="example">Le chat dort. {{TTS_EX_0}}</div><div class="example">Il joue. {{TTS_EX_1}}</div>'
    result = _strip_tts_placeholders(text)
    assert "{{TTS_EX_0}}" not in result
    assert "{{TTS_EX_1}}" not in result
    assert "Le chat dort." in result


def test_strip_tts_placeholders_no_placeholders_unchanged():
    text = "<div>plain text</div>"
    assert _strip_tts_placeholders(text) == text


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
    updated, media = _generate_tts([card], "fr", str(tmp_path))

    assert "{{TTS_EX_0}}" not in updated[0].back
    assert "{{TTS_EX_1}}" not in updated[0].back
    assert "[sound:tts_ex_0000_00.mp3]" in updated[0].back
    assert "[sound:tts_ex_0000_01.mp3]" in updated[0].back
    assert len(media) == 3  # 1 front + 2 examples


def test_write_apkg_strips_placeholders_without_tts(tmp_path):
    cards = [Card(
        front="chat",
        back='<div class="example">Le chat dort. {{TTS_EX_0}}</div>',
        tts_examples=["Le chat dort."],
    )]
    out = str(tmp_path / "test.apkg")
    write_apkg("Test", cards, out)  # no tts_lang passed
    assert os.path.exists(out)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_builder.py -v`
Expected: FAIL with `ImportError: cannot import name '_strip_tts_placeholders'`

- [ ] **Step 3: Implement the changes**

In `src/ankideck/builder.py`, add `_strip_tts_placeholders` right after `_stable_guid`:

```python
def _strip_tts_placeholders(text: str) -> str:
    """Remove leftover {{TTS_EX_i}} markers when no TTS run has filled them in."""
    return re.sub(r"\{\{TTS_EX_\d+\}\}", "", text)
```

Replace the body of `_generate_tts`'s per-card loop (the block from `for i, card in bar:` through `updated.append(...)`) with:

```python
    for i, card in bar:
        front_text = card.tts_front or strip_html(card.front)
        back_text = card.tts_back

        new_front = card.front
        new_back = card.back

        # --- front audio ---
        if front_text.strip():
            fname = f"tts_front_{i:04d}.mp3"
            bar.set_postfix_str(f"front: {front_text[:20]}", refresh=False)
            path = make_tts([front_text], fname, cache_dir, lang=lang)
            if path:
                media_files.append(path)
                new_front = card.front + f"<br>[sound:{fname}]"

        # --- back audio (single legacy example sentence, xlsx cards) ---
        if back_text.strip():
            fname = f"tts_back_{i:04d}.mp3"
            bar.set_postfix_str(f"example: {back_text[:20]}", refresh=False)
            path = make_tts([back_text], fname, cache_dir, lang=lang)
            if path:
                media_files.append(path)
                new_back = card.back + f"<br>[sound:{fname}]"

        # --- per-example audio (JSON cards: 0..N examples) ---
        for j, example_text in enumerate(card.tts_examples):
            placeholder = f"{{{{TTS_EX_{j}}}}}"
            if not example_text.strip():
                new_back = new_back.replace(placeholder, "")
                continue
            fname = f"tts_ex_{i:04d}_{j:02d}.mp3"
            bar.set_postfix_str(f"example {j}: {example_text[:20]}", refresh=False)
            path = make_tts([example_text], fname, cache_dir, lang=lang)
            if path:
                media_files.append(path)
                new_back = new_back.replace(placeholder, f"[sound:{fname}]")
            else:
                new_back = new_back.replace(placeholder, "")

        updated.append(Card(
            front=new_front,
            back=new_back,
            tags=card.tags,
            tts_front=card.tts_front,
            tts_back=card.tts_back,
            tts_examples=card.tts_examples,
        ))
```

Also remove the now-unused `need_front`/`need_back`/`cached` pre-count block above the loop (it only prints a "already cached" hint and doesn't affect behavior) — leave it in place if present; it's cosmetic and out of scope, no change required either way. (Skip this — no action needed.)

In `write_apkg`, replace:

```python
    if tts_lang:
        print(f"Generating TTS audio (lang={tts_lang}) into '{tts_cache_dir}/'...")
        all_cards, extra_media = _generate_tts(all_cards, tts_lang, tts_cache_dir)
        print(f"  {len(extra_media)} audio file(s) ready.")
```

with:

```python
    if tts_lang:
        print(f"Generating TTS audio (lang={tts_lang}) into '{tts_cache_dir}/'...")
        all_cards, extra_media = _generate_tts(all_cards, tts_lang, tts_cache_dir)
        print(f"  {len(extra_media)} audio file(s) ready.")
    else:
        all_cards = [
            Card(
                front=c.front,
                back=_strip_tts_placeholders(c.back),
                tags=c.tags,
                tts_front=c.tts_front,
                tts_back=c.tts_back,
                tts_examples=c.tts_examples,
            )
            for c in all_cards
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_builder.py -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `pytest -q`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/ankideck/builder.py tests/test_builder.py
git commit -m "feat: generate per-example TTS audio and strip unused placeholders"
```

---

### Task 6: CLI `.json` dispatch

**Files:**
- Modify: `src/ankideck/builder.py`
- Test: `tests/test_builder.py`

**Interfaces:**
- Consumes: `read_cards_json` (Task 4).
- Produces: `ankideck-build some_chapter.json --deck "X" --tts fr` works end-to-end.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_builder.py`:

```python
from ankideck.builder import main as builder_main


def test_cli_reads_json_input(tmp_path):
    json_path = tmp_path / "cards.json"
    json_path.write_text(json.dumps({
        "cards": [{"type": "vocab", "front": "chat", "pos": "n.m.", "meaning_fa": "گربه"}],
    }), encoding="utf-8")
    out_path = tmp_path / "out.apkg"

    builder_main([str(json_path), "--deck", "Test", "-o", str(out_path)])

    assert out_path.exists()
```

(Add `import json` to the top of `tests/test_builder.py` if not already present.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_builder.py::test_cli_reads_json_input -v`
Expected: FAIL — `.json` files fall through to the delimited-text reader (`read_cards`), which will misparse or error on the JSON content.

- [ ] **Step 3: Add `.json` dispatch**

In `src/ankideck/builder.py`'s `main()`, change:

```python
    cards: List[Card] = []
    for f in args.input:
        ext = Path(f).suffix.lower()
        if ext in (".xlsx", ".xls"):
            from ankideck.reader import read_cards_excel
            batch = read_cards_excel(
                f,
                front_col=args.front_col,
                tts_back_col=args.tts_back_col if args.tts else None,
            )
        else:
            has_header = False if args.no_header else None
            batch = read_cards(f, delimiter=args.delimiter, has_header=has_header)
```

to:

```python
    cards: List[Card] = []
    for f in args.input:
        ext = Path(f).suffix.lower()
        if ext in (".xlsx", ".xls"):
            from ankideck.reader import read_cards_excel
            batch = read_cards_excel(
                f,
                front_col=args.front_col,
                tts_back_col=args.tts_back_col if args.tts else None,
            )
        elif ext == ".json":
            from ankideck.reader import read_cards_json
            batch = read_cards_json(f)
        else:
            has_header = False if args.no_header else None
            batch = read_cards(f, delimiter=args.delimiter, has_header=has_header)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_builder.py::test_cli_reads_json_input -v`
Expected: PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `pytest -q`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/ankideck/builder.py tests/test_builder.py
git commit -m "feat: dispatch .json input files to read_cards_json in CLI"
```

---

### Task 7: "Design 5" clickable-word template doc

**Files:**
- Modify: `scripts/anki_card_type.md`

**Interfaces:**
- Consumes: `.clickword` / `data-word` markup produced by `_wrap_clickwords` (Task 2) — this is documentation, not executed by the test suite; it's verified by inspection against the actual HTML shape `read_cards_json` produces.

- [ ] **Step 1: Mark Design 4 as legacy**

In `scripts/anki_card_type.md`, change the Design 4 heading (currently `## 4. Clickable-word popup — only on the French example line of Back`) to:

```markdown
## 4. Clickable-word popup — only on the French example line of Back (legacy, xlsx decks)

**Legacy**: this template's line-sniffing (`EN:`/`FA:`/`[sound:...]` prefix
detection) only works for the single-example xlsx pipeline's Back field
shape. Decks built from `read_cards_json` (see Design 5 below) don't need
this — use Design 5 for those instead.
```

- [ ] **Step 2: Add the Design 5 section**

Append to the end of `scripts/anki_card_type.md`:

```markdown
---

## 5. Clickable-word popup — schema-driven (JSON-built decks)

For decks built from `read_cards_json` (vocab and grammar cards), the
`.clickword` spans are already baked into the `Front`/`Back` field HTML by
the Python reader (`ankideck.reader._wrap_clickwords`) — every French word
in the front, in each example, and in synonyms/antonyms is wrapped as:

```html
<span class="clickword" data-word="chat">chat</span>
```

Non-French text (meanings, POS label, grammar explanation) is never
wrapped, so the template doesn't need to detect or skip anything by
content — it just attaches the popup handler to whatever `.clickword`
elements exist, front or back, however many there are.

Paste into the **Back Template** field:

```html
{{FrontSide}}
<hr id="answer">
{{Back}}

<!-- Floating popup menu (hidden until a word is clicked) -->
<div id="word-menu" style="
    display:none; position:fixed; z-index:9999;
    background:#fff; border:1px solid #ccc; border-radius:8px;
    box-shadow:0 4px 12px rgba(0,0,0,0.2); padding:8px; min-width:175px;">
  <div id="menu-label" style="
      font-weight:bold; font-size:13px; color:#555;
      margin-bottom:6px; text-align:center; border-bottom:1px solid #eee; padding-bottom:4px;">
  </div>
  <button onclick="openReverso()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#2b6cb0; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Conjugate — Reverso
  </button>
  <button onclick="openDict()" style="
      display:block; width:100%; margin:3px 0; padding:6px 10px;
      background:#276749; color:#fff; border:none; border-radius:5px;
      font-size:13px; cursor:pointer;">
    Dictionary — WordReference
  </button>
</div>

<script>
(function() {
  var currentWord = "";
  var menu = document.getElementById("word-menu");

  document.addEventListener("click", function(e) {
    var span = e.target.closest ? e.target.closest(".clickword") : null;
    if (!span) {
      menu.style.display = "none";
      return;
    }
    e.stopPropagation();
    currentWord = span.dataset.word;
    document.getElementById("menu-label").innerText = currentWord;
    menu.style.display = "block";
    var x = Math.min(e.clientX, window.innerWidth - 195);
    var y = e.clientY + 14;
    menu.style.left = x + "px";
    menu.style.top = y + "px";
  });

  window.openReverso = function() {
    window.open("https://conjugator.reverso.net/conjugation-french-verb-" + currentWord + ".html", "_blank");
    menu.style.display = "none";
  };

  window.openDict = function() {
    window.open("https://www.wordreference.com/fren/" + currentWord, "_blank");
    menu.style.display = "none";
  };
})();
</script>
```

### Why this is simpler than Design 4

- No line-splitting, no `EN:`/`FA:`/`[sound:...]` regex detection — the
  reader already knows which spans are French at build time, so the
  template only needs one `querySelector`-style click delegation, shared
  by front and back.
- Works unchanged for vocab cards (front word + synonyms + antonyms +
  N examples) and grammar cards (front example + optional N extra
  examples) — the explanation/meaning text simply has no `.clickword`
  spans to match, so it's naturally skipped.
- Adding a second, third, or tenth example to a card requires no template
  change — same spans, same delegated handler.
```

- [ ] **Step 3: Commit**

```bash
git add scripts/anki_card_type.md
git commit -m "docs: add schema-driven Design 5 clickable-word template"
```

---

### Task 8: `PDF_TO_ANKI_PIPELINE.md` step 4/5 update

**Files:**
- Modify: `PDF_TO_ANKI_PIPELINE.md`

**Interfaces:**
- Consumes: `read_cards_json` (Task 4), schema at `schemas/card.schema.json` (Task 1). Documentation only — no test.

- [ ] **Step 1: Update the directory layout section**

In `PDF_TO_ANKI_PIPELINE.md`, change:

```
  vocab/                  # one .xlsx per chapter (French/English/Persian/Example)
```

to:

```
  vocab/                  # one .json per chapter (see schemas/card.schema.json)
```

- [ ] **Step 2: Replace Step 4's content**

Replace the entire "## Step 4 — Extract vocab/phrases per chapter into xlsx" section with:

```markdown
## Step 4 — Extract vocab/phrases per chapter into JSON

Target format — every chapter gets `vocab/<chapter_name>.json` conforming
to `schemas/card.schema.json` (see `samples/sample_vocabulary.json` for a
worked example):

```json
{
  "chapter": "<chapter_name>",
  "cards": [
    {
      "type": "vocab",
      "front": "une cravate",
      "pos": "n.f.",
      "meaning_fa": "کراوات",
      "meaning_en": "a tie",
      "synonyms": [],
      "antonyms": [],
      "examples": ["Il porte une cravate rouge pour aller au bureau."],
      "tags": ["<chapter_name>"]
    }
  ]
}
```

Conventions:
- **`front`**: the term/phrase as the book shows it (keep the article on
  nouns, e.g. `une cravate`; verbs in infinitive unless it's a fixed
  expression like `avoir faim`).
- **`pos`**: short abbreviation — `n.m.`, `n.f.`, `adj`, `adv`, `v`,
  `prep`, `conj`, `pron`, or `expr` for fixed expressions/idioms.
- **`meaning_fa`** / **`meaning_en`**: concise, accurate translations of
  the front term. `meaning_fa` is required; `meaning_en` is optional.
- **`synonyms`** / **`antonyms`**: optional lists of related French
  words/phrases — omit or leave empty if none apply.
- **`examples`**: a list of natural French sentences using the term —
  reuse/adapt sentences actually seen in the book (dialogue or
  explanation) when possible, otherwise write short original A1/A2
  sentences. Include more than one when the book gives more than one
  usage worth capturing (e.g. different senses of a verb) — unlike the
  old xlsx format, there's no fixed limit.
- Skip pure grammar filler (bare articles/pronouns); keep nouns,
  adjectives, verbs, and useful fixed expressions.
- 15-30 items per chapter is typical. Review/"Bilan" chapters usually have
  no dedicated vocabulary list — pull useful words/expressions out of the
  exercise questions and answer choices instead.

**Grammar-rule cards**: when a chapter explains a grammar point worth its
own card (e.g. "passé composé with être"), add a `type: "grammar"` entry
instead of `vocab`:

```json
{
  "type": "grammar",
  "front": "Elle est partie tôt.",
  "explanation": "Les verbes de mouvement (aller, partir, sortir...) se conjuguent avec être au passé composé; le participe s'accorde avec le sujet.",
  "examples": ["Nous sommes arrivés hier."],
  "tags": ["<chapter_name>", "grammar"]
}
```

`front` is one French example sentence illustrating the rule (this is
what gets spoken + made clickable, same as a vocab word's front).
`explanation` is prose (English, optionally mixing in Persian) — plain
text, not clickable or voiced. `examples` (optional) adds further
illustrating sentences beyond the front one.

Because this step requires viewing dozens/hundreds of page images and is
naturally parallelizable across chapters, **use several background Agent
(general-purpose) calls, one per batch of ~4 chapters**, each with a
self-contained prompt that:
1. Lists that batch's chapter folders (and page counts) under
   `chapter_images/`.
2. States the exact output path and JSON schema (above), and gives a
   worked example (`samples/sample_vocabulary.json`) to follow.
3. Notes any Bilan-chapter special-casing (extract from exercises instead
   of a vocab list).

Wait for all batches to complete before moving to step 5. Spot-check a few
of the resulting JSON files against `schemas/card.schema.json` (e.g. with
`python -c "import json,jsonschema; jsonschema.validate(json.load(open('vocab/ch05.json')), json.load(open('schemas/card.schema.json')))"`)
before building the deck.
```

- [ ] **Step 3: Update Step 5's reader reference**

In the "## Step 5 — Build the hierarchical .apkg" section, change:

```
- `read_cards_excel(...)` from `ankideck.reader` reads each xlsx with
  `front_col="French"`, `back_cols=["English", "Persian", "Example"]`,
  `tts_back_col="Example"` (the example sentence gets spoken + styled
  differently on the back).
```

to:

```
- `read_cards_json(...)` from `ankideck.reader` reads each chapter's
  `vocab/<chapter>.json`, building one `Card` per entry (vocab or
  grammar). Front content and every French example already carry
  `.clickword` markup and TTS placeholders — no extra reader arguments
  needed, unlike the old xlsx column-mapping.

  (Older decks/scripts using the legacy `vocab/<chapter>.xlsx` format can
  still call `read_cards_excel(...)` exactly as before — it's unchanged.)
```

- [ ] **Step 4: Commit**

```bash
git add PDF_TO_ANKI_PIPELINE.md
git commit -m "docs: update PDF-to-Anki pipeline to target JSON vocab/grammar cards"
```

---

## Self-Review Notes

- **Spec coverage:** §1 schema → Task 1; §2 reader changes → Tasks 2-4; §3 builder TTS → Task 5; CLI dispatch (implied by "no breaking changes to CLI paths" + needed for pipeline usability) → Task 6; §4 template → Task 7; §5 pipeline doc → Task 8. Testing section's two test files → covered across Tasks 1-6.
- **Placeholder scan:** no TBD/TODO; every step has literal code or literal doc text to write.
- **Type consistency:** `Card.tts_examples: List[str]` (Task 2) is the type threaded through `_vocab_to_card`/`_grammar_to_card` (Task 3), `_generate_tts` (Task 5), and CLI dispatch (Task 6) — consistent throughout. Placeholder format `{{TTS_EX_i}}` is identical in `_example_block` (Task 3), `_generate_tts`/`_strip_tts_placeholders` (Task 5), and the template doc (Task 7).
