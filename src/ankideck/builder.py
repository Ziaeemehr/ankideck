"""Build Anki .apkg deck files from card lists.

Typical workflow (plain deck)::

    cards = read_cards("my_input.tsv")
    write_apkg("My Deck", cards, "my_deck.apkg")

With inline TTS (generates and embeds audio)::

    cards = read_cards_excel("vocab.xlsx", front_col="French", tts_back_col="Example")
    write_apkg("TCF Vocab", cards, "tcf.apkg", tts_lang="fr")

Update without losing study progress::

    # Just run write_apkg again with the updated card list.
    # GUIDs are derived from the front text, so Anki matches existing notes
    # and only adds genuinely new ones. No review history is lost.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

import genanki

from ankideck.dedup import remove_duplicates
from ankideck.reader import Card, read_cards

BASIC_MODEL = genanki.Model(
    1607392319,
    "Basic",
    fields=[{"name": "Front"}, {"name": "Back"}],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
        }
    ],
    css=(
        ".card { font-family: arial; font-size: 20px; text-align: center; "
        "color: black; background-color: white; }"
    ),
)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _stable_guid(front: str) -> str:
    """Derive a stable GUID from the front field plain text.

    Using the front text (not the full note content) means:
    - Importing an updated deck will UPDATE an existing note (same GUID)
      instead of creating a duplicate, preserving review progress.
    - Only genuinely new fronts get new GUIDs (new cards).
    """
    key = _strip_html(front).strip().lower()
    return genanki.guid_for(key)


def _strip_tts_placeholders(text: str) -> str:
    """Remove leftover {{TTS_EX_i}} markers when no TTS run has filled them in."""
    return re.sub(r"\{\{TTS_EX_\d+\}\}", "", text)


def build_deck(
    deck_name: str,
    cards: List[Card],
    deck_id: Optional[int] = None,
) -> genanki.Deck:
    """Build a genanki Deck from a list of Cards."""
    if deck_id is None:
        deck_id = abs(hash(deck_name)) % (1 << 31)
    deck = genanki.Deck(deck_id, deck_name)
    for card in cards:
        note = genanki.Note(
            model=BASIC_MODEL,
            fields=[card.front, card.back],
            tags=card.tags,
            guid=_stable_guid(card.front),
        )
        deck.add_note(note)
    return deck


def _generate_tts(
    cards: List[Card],
    lang: str,
    cache_dir: str,
) -> tuple:
    """Generate TTS audio for cards that carry tts_front / tts_back.

    Returns (modified_cards, media_files) where each card's front/back
    fields have the sound tag appended and media_files is the list of
    generated MP3 paths.
    """
    from tqdm import tqdm
    from ankideck.tts import make_tts, strip_html

    os.makedirs(cache_dir, exist_ok=True)
    media_files: List[str] = []
    updated: List[Card] = []

    # Count how many actually need generation (not already cached)
    need_front = sum(
        1 for i, c in enumerate(cards)
        if (c.tts_front or strip_html(c.front)).strip()
        and not os.path.exists(os.path.join(cache_dir, f"tts_front_{i:04d}.mp3"))
    )
    need_back = sum(
        1 for i, c in enumerate(cards)
        if c.tts_back.strip()
        and not os.path.exists(os.path.join(cache_dir, f"tts_back_{i:04d}.mp3"))
    )
    cached = len(cards) - need_front  # rough cached count for front

    if cached > 0:
        print(f"  {cached} front audio file(s) already cached, skipping.")

    bar = tqdm(
        enumerate(cards),
        total=len(cards),
        desc="Generating audio",
        unit="card",
        ncols=72,
    )

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

    return updated, media_files


def write_apkg(
    deck_name: str,
    cards: List[Card],
    output_path: str,
    media_files: Optional[List[str]] = None,
    check_duplicates: bool = True,
    tts_lang: Optional[str] = None,
    tts_cache_dir: str = "tts_cache",
) -> int:
    """Write cards to an .apkg file.

    Args:
        deck_name: Anki deck name shown inside the app.
        cards: Cards to include.  Pass existing + new combined to append.
        output_path: Destination .apkg file path.
        media_files: Extra media files to bundle (audio, images).
        check_duplicates: Remove duplicate fronts before writing (default True).
        tts_lang: If set (e.g. "fr"), generate TTS audio and embed it.
            Uses each Card's tts_front / tts_back fields.
        tts_cache_dir: Directory for cached TTS MP3 files.

    Returns:
        Number of cards written.

    Note on updates:
        GUIDs are derived from the front text only.  Re-running with an
        updated card list and importing with "Update existing notes when
        first field matches" in Anki will add new cards and update changed
        backs without resetting review progress for existing cards.
    """
    all_cards = list(cards)
    if check_duplicates:
        all_cards = remove_duplicates(all_cards, key="front")

    extra_media: List[str] = []

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

    print(f"Building deck '{deck_name}' ({len(all_cards)} cards)...")
    deck = build_deck(deck_name, all_cards)
    pkg = genanki.Package(deck)
    pkg.media_files = list(media_files or []) + extra_media
    pkg.write_to_file(output_path)
    print(f"Written: {output_path}")
    return len(all_cards)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Build an Anki .apkg deck from CSV/TSV/XLSX file(s).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ankideck-build --deck "French A2" input.tsv
  ankideck-build --deck "French A2" base.tsv new_cards.tsv -o french.apkg
  ankideck-build --deck "TCF Vocab" vocab.xlsx --tts fr
""",
    )
    p.add_argument("input", nargs="+", help="Input file(s) (.tsv / .csv / .txt / .xlsx)")
    p.add_argument("--deck", "-d", required=True, help="Anki deck name")
    p.add_argument("--output", "-o", default="deck.apkg", help="Output .apkg path")
    p.add_argument("--delimiter", help="Column delimiter (auto-detected if omitted)")
    p.add_argument("--no-header", action="store_true", help="First row is data, not a header")
    p.add_argument("--no-dedup", action="store_true", help="Skip duplicate removal")
    p.add_argument("--tts", metavar="LANG", help="Generate TTS audio (e.g. 'fr', 'en', 'de')")
    p.add_argument("--tts-cache", default="tts_cache", metavar="DIR",
                   help="Directory for cached TTS MP3s (default: tts_cache)")
    # Excel-specific options
    p.add_argument("--front-col", default="French",
                   help="Excel: column name for card front (default: French)")
    p.add_argument("--tts-back-col", default="Example",
                   help="Excel: column whose text is spoken on the back (default: Example)")
    args = p.parse_args(argv)

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
        print(f"  {f}: {len(batch)} cards")
        cards.extend(batch)

    output = args.output if args.output.endswith(".apkg") else args.output + ".apkg"
    n = write_apkg(
        args.deck,
        cards,
        output,
        check_duplicates=not args.no_dedup,
        tts_lang=args.tts,
        tts_cache_dir=args.tts_cache,
    )
    removed = len(cards) - n
    suffix = f" ({removed} duplicates removed)" if removed else ""
    print(f"\nWritten {n} cards to '{output}'{suffix}")


if __name__ == "__main__":
    sys.exit(main())
