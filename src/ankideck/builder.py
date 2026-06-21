"""Build Anki .apkg deck files from card lists.

Primary workflow:
    cards = read_cards("my_input.tsv")
    write_apkg("My Deck", cards, "my_deck.apkg")

To combine multiple input files and deduplicate before writing:
    cards = read_cards("base.tsv") + read_cards("new_cards.tsv")
    write_apkg("My Deck", cards, "my_deck.apkg")  # dedup is on by default
"""

import argparse
import random
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
    css=".card { font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white; }",
)


def build_deck(
    deck_name: str,
    cards: List[Card],
    deck_id: Optional[int] = None,
) -> genanki.Deck:
    """Build a genanki Deck from a list of Cards."""
    if deck_id is None:
        deck_id = random.randrange(1 << 30, 1 << 31)
    deck = genanki.Deck(deck_id, deck_name)
    for card in cards:
        note = genanki.Note(
            model=BASIC_MODEL,
            fields=[card.front, card.back],
            tags=card.tags,
        )
        deck.add_note(note)
    return deck


def write_apkg(
    deck_name: str,
    cards: List[Card],
    output_path: str,
    media_files: Optional[List[str]] = None,
    check_duplicates: bool = True,
) -> int:
    """Write cards to an .apkg file.

    Args:
        deck_name: Anki deck name shown inside the app.
        cards: Cards to include. Pass existing + new combined to append.
        output_path: Destination .apkg file path.
        media_files: Paths to media files (audio, images) to bundle.
        check_duplicates: Remove duplicate fronts before writing (default True).

    Returns:
        Number of cards written.
    """
    all_cards = list(cards)
    if check_duplicates:
        all_cards = remove_duplicates(all_cards, key="front")

    deck = build_deck(deck_name, all_cards)
    pkg = genanki.Package(deck)
    if media_files:
        pkg.media_files = media_files
    pkg.write_to_file(output_path)
    return len(all_cards)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Build an Anki .apkg deck from CSV/TSV file(s).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ankideck-build --deck "French A2" input.tsv
  ankideck-build --deck "French A2" base.tsv new_cards.tsv --output french_a2.apkg
  ankideck-build --deck "French A2" input.csv --delimiter , --no-dedup
""",
    )
    p.add_argument("input", nargs="+", help="Input file(s) (TSV, CSV, TXT)")
    p.add_argument("--deck", "-d", required=True, help="Anki deck name")
    p.add_argument("--output", "-o", default="deck.apkg", help="Output .apkg path (default: deck.apkg)")
    p.add_argument("--delimiter", help="Column delimiter (auto-detected if omitted)")
    p.add_argument("--no-header", action="store_true", help="Treat first row as data, not a header")
    p.add_argument("--no-dedup", action="store_true", help="Skip duplicate removal")
    args = p.parse_args(argv)

    cards: List[Card] = []
    for f in args.input:
        has_header = False if args.no_header else None
        batch = read_cards(f, delimiter=args.delimiter, has_header=has_header)
        print(f"  {f}: {len(batch)} cards")
        cards.extend(batch)

    output = args.output
    if not output.endswith(".apkg"):
        output += ".apkg"

    n = write_apkg(args.deck, cards, output, check_duplicates=not args.no_dedup)
    removed = len(cards) - n
    print(f"\nWritten {n} cards to '{output}'" + (f" ({removed} duplicates removed)" if removed else ""))


if __name__ == "__main__":
    sys.exit(main())
