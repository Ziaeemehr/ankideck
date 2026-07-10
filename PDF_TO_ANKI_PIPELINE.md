# PDF Textbook → Hierarchical Anki Deck: Reusable Pipeline

This is the process used to turn a French textbook PDF (e.g. `gram_dial_int`,
`vocab_dial_a1`) into one hierarchical `.apkg` file with one subdeck per
chapter and gTTS (Google Translate) audio on French text.

It works for both born-digital and scanned PDFs, because step 2 uses vision
(reading rendered page images) instead of OCR — OCR on scanned textbooks is
often unreliable, especially for tables/columns and accented French text.

Everything here assumes the `ankideck` package from
`/Users/tng/git/AnkiDecks_develop` is on `PYTHONPATH` (or installed via
`pip install -e .`).

## Directory layout for a new book

Pick a project directory, e.g. `/Users/tng/Projects/Language/FR/Anki_decks/<book_slug>/`,
containing just the source PDF to start:

```
<book_slug>/
  <Book>.pdf
```

The pipeline below builds up this directory into:

```
<book_slug>/
  <Book>.pdf
  chapters.json          # split_pdf config
  chapters/               # one PDF per chapter
  chapter_images/         # one PNG per page per chapter (for extraction)
  vocab/                  # one .xlsx per chapter (French/English/Persian/Example)
  tts_cache_full/         # cached gTTS mp3s (safe to keep across reruns)
  script.py               # builds the final .apkg
  <Book>.apkg              # final output
```

## Step 1 — Find the chapter boundaries

Render the first ~10-12 pages of the PDF to images and read them (don't OCR):

```python
import fitz  # PyMuPDF
doc = fitz.open("Book.pdf")
for i in range(0, 12):
    doc[i].get_pixmap(dpi=150).save(f"/tmp/toc_{i+1:03d}.png")
```

Read those images with the Read tool. Look for a "Sommaire"/table of contents
page listing chapter titles and their **printed** page numbers.

Then find the **offset** between printed page numbers and actual PDF page
index: render the PDF page that the TOC claims is the first chapter page,
and one or two pages near the end of the book, and visually confirm which
PDF page shows which printed footer number. Typically the offset is constant
throughout (e.g. `pdf_page = printed_page - 1` because of a cover/blank page),
but always verify near the end of the book too — some books renumber front
matter (roman numerals) which breaks a naive constant offset.

## Step 2 — Split the PDF into chapters

Write a `chapters.json`:

```json
{
  "pdf": "Book.pdf",
  "output_dir": "chapters",
  "chapters": [
    {"name": "01_Ch01_Some_Topic", "start": 5},
    {"name": "02_Ch02_Other_Topic", "start": 10}
  ]
}
```

`start` is the **PDF page number** (1-based), not the printed page number.
The tool infers each chapter's end page from the next chapter's start (last
chapter runs to the end of the PDF). Include bilans/review sections and any
appendix as their own chapters if you want them split out too — you can
skip appendices (lexique/corrigés/answer keys) in later steps.

Run it:

```bash
cd <book_slug>
PYTHONPATH=/Users/tng/git/AnkiDecks_develop/src python3 -m ankideck.split_pdf chapters.json
# or, if the package is pip-installed: split_pdf chapters.json
```

## Step 3 — Render every chapter page to an image

```python
import fitz, os, glob

for f in sorted(glob.glob("chapters/*.pdf")):
    base = os.path.splitext(os.path.basename(f))[0]
    # optionally skip a pure answer-key/appendix chapter here
    outdir = os.path.join("chapter_images", base)
    os.makedirs(outdir, exist_ok=True)
    doc = fitz.open(f)
    for i, page in enumerate(doc):
        page.get_pixmap(dpi=170).save(os.path.join(outdir, f"p{i+1:02d}.png"))
```

170dpi is a good balance of legibility vs. image size for reading French text
(including accents) in tables.

## Step 4 — Extract vocab/phrases per chapter into xlsx

Target format — every chapter gets `vocab/<chapter_name>.xlsx` with a header
row and one row per flashcard:

| French | English | Persian | Example |
|---|---|---|---|
| une cravate | a tie | کراوات | Il porte une cravate rouge pour aller au bureau. |

Conventions:
- **French**: the term/phrase as the book shows it (keep the article on
  nouns, e.g. `une cravate`; verbs in infinitive unless it's a fixed
  expression like `avoir faim`).
- **English** / **Persian**: concise, accurate translations.
- **Example**: one natural French sentence using the term — reuse/adapt a
  sentence actually seen in the book (dialogue or explanation) when
  possible, otherwise write a short original A1/A2-appropriate sentence.
- Skip pure grammar filler (bare articles/pronouns); keep nouns, adjectives,
  verbs, and useful fixed expressions.
- 15-30 items per chapter is typical. Review/"Bilan" chapters usually have no
  dedicated vocabulary list — pull useful words/expressions out of the
  exercise questions and answer choices instead.

Because this step requires viewing dozens/hundreds of page images and is
naturally parallelizable across chapters, **use several background Agent
(general-purpose) calls, one per batch of ~4 chapters**, each with a
self-contained prompt that:
1. Lists that batch's chapter folders (and page counts) under
   `chapter_images/`.
2. States the exact output path and xlsx schema (header row above), and
   gives a working `openpyxl` snippet to write it.
3. Notes any Bilan-chapter special-casing (extract from exercises instead of
   a vocab list).

Wait for all batches to complete before moving to step 5. Spot-check a few
of the resulting xlsx files (row counts, spelling, no leftover placeholder
text) before building the deck.

## Step 5 — Build the hierarchical .apkg

Adapt `script.py` (see `gram_dial_int/script.py` or `vocab_dial_a1/script.py`
for a working example). The key pieces:

- `ITEMS`: ordered list of `(file_prefix, display_title)` — one per chapter,
  in book order. `display_title` becomes the subdeck name under `PARENT`.

  **Anki always shows the deck list alphabetically**, regardless of import
  order — so `display_title` needs a leading sort key. Do **not** just use
  the 1-based position in `ITEMS` for that key (i.e. `file_prefix`'s own
  counter): if bilans/reviews are interspersed as their own chapters, the
  position index drifts away from the book's real chapter numbers (e.g. the
   16th *entry* in `ITEMS` might be "Chapitre 14" because 2 bilans came
  before it), which is confusing when browsing the deck list in Anki. Use
  the book's own chapter number instead, and give bilans a `NN.5` key so
  they sort right after the chapter they follow without claiming to be a
  numbered chapter themselves, e.g.:
  ```
  ("05_Ch05_...", "05 Les vetements et les couleurs"),
  ("06_Bilan_1",  "05.5 Bilan 1"),
  ("07_Ch06_...", "06 L'apparence physique"),
  ```
- `read_cards_excel(...)` from `ankideck.reader` reads each xlsx with
  `front_col="French"`, `back_cols=["English", "Persian", "Example"]`,
  `tts_back_col="Example"` (the example sentence gets spoken + styled
  differently on the back).
- `make_tts(...)` from `ankideck.tts` generates/caches gTTS mp3s
  (`lang="fr"`) for both the French front and the French example on the
  back.
- `genanki.Deck` per chapter, named `f"{PARENT}::{title}"` — the `::`
  separator is what makes Anki treat it as a subdeck of `PARENT`.
- A stable numeric deck id derived from `md5(deck_name)` so re-running the
  script doesn't create duplicate decks in Anki.
- One `genanki.Package(all_decks)` at the end, with all subdecks bundled and
  all generated media attached, written to a single `.apkg`.

Run it:

```bash
cd <book_slug>
PYTHONPATH=/Users/tng/git/AnkiDecks_develop/src python3 script.py
```

This produces one `.apkg` that imports into Anki as a single parent deck
with one subdeck per chapter (bilans/appendices included if you gave them
their own xlsx). gTTS requires internet access and is rate-limited-ish, so
the run can take a while for large books; the `tts_cache_full/` directory
caches by filename so re-runs only regenerate missing audio.

## Step 6 — Import and verify

Open Anki → File → Import → select the `.apkg`. Check that the parent deck
appears with the expected subdeck tree and card counts, and spot-check audio
playback on a few cards.

## Notes / gotchas

- **Scanned vs. digital PDFs**: this pipeline doesn't care — it always
  renders pages to images and reads them visually rather than relying on
  extracted text, which sidesteps OCR errors entirely.
- **Page-offset drift**: double check the printed-page → PDF-page offset
  near the *end* of the book too, not just the start; front matter (roman
  numerals, unnumbered pages) can shift it.
- **Farsi/Persian text and TTS**: `ankideck.tts` only speaks the
  `tts_back_col`/`tts_front` text with the given `lang` (French here); it
  does not attempt to speak Persian, so mixing scripts in the back HTML is
  fine.
- **Re-running is safe**: both the TTS cache and genanki's stable deck IDs
  (hash of the deck name) make it safe to re-run `script.py` after fixing a
  vocab xlsx — only new/changed audio gets regenerated, and Anki will treat
  it as an update to the same subdeck rather than a duplicate.
