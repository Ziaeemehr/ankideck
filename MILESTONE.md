# ankideck — Development Milestones

## Current state (v0.2.0)

### Package structure

| Module | Purpose |
|---|---|
| `reader.py` | Parse TSV / CSV / TXT with auto-detected delimiter and header |
| `dedup.py` | File-level duplicate detection and removal (no Anki required) |
| `builder.py` | Build `.apkg` from a card list; CLI `ankideck-build` |
| `tts.py` | TTS audio via gTTS (default) or ElevenLabs |
| `anki_connect.py` | AnkiConnect API wrapper (requires Anki running) |
| `add_tts.py` | CLI: attach TTS audio to an existing live deck via AnkiConnect |
| `import_to_anki.py` | CLI: batch-import a folder of CSVs, one deck per file |
| `fix_format.py` | CLI: normalise delimiters in messy CSV files |
| `extract_text.py` | CLI: OCR a PDF to text |
| `split_pdf.py` | CLI: split a PDF into chapters from a JSON config |

### Supported input formats

- Tab-separated (`.tsv`, `.txt`) — **primary format**
- Comma-separated (`.csv`)
- Semicolon-separated (`.csv`)
- Pipe-separated
- With or without `Front` / `Back` header row (auto-detected)
- Optional `Tags` column

### CLI commands

```bash
# Build a deck from one or more input files
ankideck-build --deck "French A2" samples/sample_with_tags.tsv

# Combine base + new cards (duplicates removed on front field)
ankideck-build --deck "French A2" base.tsv new_cards.tsv --output french_a2.apkg

# Batch-import a folder (one deck per file)
ankideck-import ./csv

# Fix delimiter problems in a messy CSV
ankideck-fix input.csv --find ';'

# Add TTS audio to a deck already inside Anki (needs AnkiConnect)
ankideck-tts "French A2" gtts none

# OCR a PDF to text
ankideck-ocr book.pdf output.txt fra
```

---

## Milestone 1 — Inline TTS in standalone `.apkg`  *(priority: high)*

**Goal:** generate audio during deck build so the output `.apkg` already
contains sound tags and MP3 files — no Anki and no AnkiConnect required.

**Approach:**
1. `builder.py`: add `--tts / --tts-lang` flags to `ankideck-build`.
2. For each card, call `tts.make_tts(card.front, ...)` into a temp cache dir.
3. Embed collected MP3s via `genanki.Package.media_files`.
4. Rewrite the `Front` field to append `[sound:filename.mp3]`.

**Estimated effort:** medium — gTTS works offline-ish; ElevenLabs adds API
cost and can be deferred (see Milestone 3).

---

## Milestone 2 — Append to an existing `.apkg`  *(priority: medium)*

**Goal:** let users add new cards to a deck they already have without
re-importing everything from scratch.

**Current workaround:** pass existing CSV + new CSV together to
`ankideck-build`; dedup handles the rest.  This is fine until the original
source files are lost.

**Proper solution options:**
- **Option A** (simple): export the existing deck from Anki as a new CSV via
  AnkiConnect (`notesInfo` → write CSV), then merge + rebuild.
- **Option B** (no Anki): parse the `.apkg` file directly.  An `.apkg` is a
  ZIP containing `collection.anki2` (SQLite).  A small reader could extract
  notes from that database.

**Estimated effort:** Option A — low.  Option B — medium (SQLite schema
knowledge required).

---

## Milestone 3 — ElevenLabs TTS integration (deferred)

The ElevenLabs engine is already wired in `tts.py` and `add_tts.py` for the
AnkiConnect workflow.  Extending it to the standalone build (Milestone 1)
needs the same approach; no new design work required.

When ready, expose via `ankideck-build --tts-engine elevenlabs --tts-key-file api_key.txt`.

---

## Milestone 4 — Richer note types  *(priority: low)*

- **Cloze deletion**: detect `{{c1::...}}` patterns in the front field and
  use `genanki.Model` with cloze template automatically.
- **Reverse cards**: optional `--reverse` flag adds a Back→Front card for
  each note.
- **Image support**: detect image paths/URLs in fields and bundle the files.

---

## Milestone 5 — Configuration file  *(priority: low)*

Replace long CLI flags with a YAML/TOML project config:

```toml
[deck]
name = "French A2"
output = "french_a2.apkg"

[input]
files = ["base.tsv", "new_cards.tsv"]

[tts]
enabled = true
engine = "gtts"
lang = "fr"
```

---

## Milestone 6 — Quality / CI

- Add `pytest` to `[project.optional-dependencies]` and a `tox.ini`.
- Lint with `ruff`.
- GitHub Actions workflow: run tests on push.
- Type annotations throughout (currently partial).
