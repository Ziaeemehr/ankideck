# JSON Card Input Pipeline — Design

Date: 2026-07-25

## Problem

The current PDF→Anki pipeline (`PDF_TO_ANKI_PIPELINE.md`) extracts each
chapter's vocabulary into a 4-column `.xlsx` file (`French | English |
Persian | Example`), read by `read_cards_excel()`. This shape cannot
represent:

- multiple example sentences per word
- synonyms / antonyms
- grammar-rule cards (an explanation plus one or more illustrating examples)

The clickable-word Anki template (`scripts/anki_card_type.md`, "Design 4")
also can't cleanly support these richer cards: it makes text clickable by
sniffing rendered `Back` field lines for `EN:` / `FA:` / `[sound:...]`
prefixes, which only works for the fixed single-example xlsx layout.

## Goals

- A JSON input format that can hold: word/phrase + part of speech,
  Persian + English meaning, synonyms, antonyms, and any number of
  example sentences (vocab cards); or an explanation plus any number of
  example sentences (grammar cards).
- TTS audio generated only for the front content and for French example
  sentences — never for meanings, synonyms/antonyms text, or grammar
  explanations.
- A clickable-word template that works uniformly across both card types
  and any number of examples, without text-sniffing.
- No breaking changes to the existing xlsx pipeline — `read_cards_excel`,
  `read_cards`, and their CLI paths are untouched. JSON support is purely
  additive.

## Non-goals

- No change to how the JSON files themselves get filled in (LLM-authored,
  as today with xlsx) — this design only covers the package reading and
  building from JSON, not the authoring/extraction step's content quality.
- No new genanki `Model`/note type — cards keep using the existing
  Front/Back two-field Basic model.

## 1. JSON schema

One file per chapter, mixing vocab and grammar cards freely in one list.
Schema file: `schemas/card.schema.json`. Sample: `samples/sample_vocabulary.json`.

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

Field rules:

- `type`: `"vocab"` or `"grammar"` — required, selects which required
  fields apply below.
- **vocab**: `front` (required, French word/phrase), `pos` (required,
  short abbreviation: `n.m.`, `n.f.`, `adj`, `adv`, `v`, `prep`, `conj`,
  `pron`, or `expr` for fixed expressions/idioms), `meaning_fa` (required),
  `meaning_en` (optional), `synonyms`/`antonyms` (optional string lists,
  default empty), `examples` (optional list of French sentences, default
  empty).
- **grammar**: `front` (required, one French example sentence that
  illustrates the rule), `explanation` (required, prose — English/Persian,
  not clickable/voiced), `examples` (optional list of *additional* French
  example sentences beyond `front`, default empty).
- `tags` optional on both, default empty list.
- `examples` entries are plain strings (French only) — no per-example
  translation, since the card-level `meaning_fa`/`meaning_en` (vocab) or
  `explanation` (grammar) already covers meaning.

Validation: `read_cards_json` validates the whole file against the JSON
Schema before building any cards, raising a single clear error identifying
the failing card's index and field (e.g. `card[3] ("une cravate"): missing
required field 'pos'`) rather than silently building a bad card or
crashing deep in HTML-building code.

## 2. `reader.py` changes

- `Card` dataclass gains one new optional field:
  `tts_examples: List[str] = field(default_factory=list)` — plain French
  example texts, in the same order as the `{{TTS_EX_i}}` placeholders
  emitted in `back`. All existing fields (`front`, `back`, `tags`,
  `tts_front`, `tts_back`) are unchanged; `tts_back` stays unused
  (`""`) for JSON-built cards, so the xlsx single-clip path is untouched.
- New `read_cards_json(path) -> List[Card]`:
  - Loads and schema-validates the file.
  - For each card, wraps every whitespace-separated token of the French
    front text in `<span class="clickword" data-word="...">token</span>`
    (Python-side — the template no longer parses text to find words).
  - Builds `back` as one plain (non-clickable) `<div>` per metadata line
    (pos, meaning_fa, meaning_en, synonyms, antonyms for vocab;
    explanation for grammar), followed by one block per example: the
    example's words wrapped the same way as the front, plus a
    `{{TTS_EX_i}}` placeholder token right after it.
  - `tts_front` = the plain front text (word or, for grammar, the example
    sentence). `tts_examples` = the list of plain example texts in
    placeholder order.
  - Two small private helpers, `_vocab_to_card` and `_grammar_to_card`,
    each returning one `Card` — mirrors the existing `_build_back_html`
    helper pattern already in the file.
- `read_cards_excel`, `read_cards`, `_build_back_html`: unchanged.

## 3. `builder.py` — multi-example TTS

`_generate_tts` currently generates one clip for `tts_front` and one for
`tts_back` per card. It's extended to also loop over
`card.tts_examples`: for each entry, generate
`tts_ex_{card_idx:04d}_{ex_idx:02d}.mp3` and substitute the matching
`{{TTS_EX_i}}` placeholder in that card's `back` with `[sound:...]`.

When `tts_lang` is not passed (no TTS run), any leftover `{{TTS_EX_i}}`
placeholders are stripped via regex so the field never displays raw
placeholder text.

The existing single-clip `tts_back` path (used by xlsx-built cards) is
unchanged; the two mechanisms coexist per-card via whichever field is
populated.

`main()` (CLI) gains `.json` extension handling alongside `.xlsx`/`.tsv`,
dispatching to `read_cards_json`.

## 4. `scripts/anki_card_type.md` — "Design 5" template

Because `read_cards_json` bakes `.clickword` spans directly into the HTML
at build time, the template's JavaScript no longer needs to detect which
part of the field is French — it just attaches the existing popup-menu
click handler (Reverso conjugation / WordReference dictionary) to any
`.clickword` element found anywhere in the rendered note, front or back.
This one script handles vocab (word, synonyms, antonyms, each example) and
grammar (front example, optional back examples) uniformly, since
non-French text (meanings, explanation) simply carries no `.clickword`
spans to match.

Design 4 (line-sniffing `EN:`/`FA:`/`[sound:...]`) stays documented and
marked legacy — it continues to be the correct template for existing
xlsx-built decks, which don't emit `.clickword` spans.

## 5. `PDF_TO_ANKI_PIPELINE.md` — step 4/5 update

- Step 4 target changes from `vocab/<chapter>.xlsx` to
  `vocab/<chapter>.json`, following the schema above. Instructions added
  for when to emit `type: "grammar"` (a rule explanation spotted while
  reading the chapter) vs `type: "vocab"`, and that multiple examples per
  card are now expected where the book gives more than one.
- Step 5's example `script.py` snippet swaps
  `read_cards_excel(...)` for `read_cards_json(...)`.
- The xlsx path stays documented as a legacy fallback for older
  decks/scripts that already use it.

## Testing

- `tests/test_json_reader.py`: schema validation errors (missing
  required field, wrong `type` value), vocab card HTML/placeholder
  shape, grammar card HTML/placeholder shape, multiple examples produce
  multiple placeholders in order, synonyms/antonyms render clickable with
  no placeholder/audio.
- `tests/test_builder.py` (extend existing): `_generate_tts` with
  `tts_examples` produces one clip per example and substitutes
  placeholders correctly; no-TTS run strips placeholders cleanly;
  existing xlsx/`tts_back` tests still pass unchanged.
