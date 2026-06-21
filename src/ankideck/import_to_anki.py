#!/usr/bin/env python3
"""Import all CSV/TSV files from a directory into a single Anki package.

Each file becomes a separate named deck inside the package.
For a single-file, single-deck workflow prefer ankideck-build (builder.py).
"""

import os
import sys
from pathlib import Path

import genanki

from ankideck.builder import build_deck
from ankideck.reader import read_cards


def _collect_input_files(directory: str):
    extensions = (".csv", ".tsv", ".txt")
    return sorted(
        p for p in Path(directory).iterdir()
        if p.suffix.lower() in extensions and p.is_file()
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: import_to_anki <csv_folder> [output.apkg]")
        print("\nEach CSV/TSV file in the folder becomes a separate deck.")
        print("See `ankideck-build --help` for single-deck imports.")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.isdir(csv_path):
        print(f"Error: '{csv_path}' is not a directory.")
        sys.exit(1)

    output_file = sys.argv[2] if len(sys.argv) >= 3 else "anki_deck.apkg"
    if not output_file.endswith(".apkg"):
        output_file += ".apkg"

    input_files = _collect_input_files(csv_path)
    if not input_files:
        print(f"No CSV/TSV/TXT files found in '{csv_path}'.")
        sys.exit(1)

    print(f"Found {len(input_files)} file(s) in '{csv_path}'\n")

    decks = []
    for path in input_files:
        try:
            cards = read_cards(path)
            deck_name = path.stem
            deck = build_deck(deck_name, cards)
            decks.append(deck)
            print(f"  {path.name}: {len(cards)} cards -> deck '{deck_name}'")
        except Exception as e:
            print(f"  {path.name}: ERROR - {e}")
            continue

    if not decks:
        print("\nNo decks were created.")
        sys.exit(1)

    package = genanki.Package(decks)
    package.write_to_file(output_file)
    print(f"\nCreated '{output_file}' with {len(decks)} deck(s).")


if __name__ == "__main__":
    main()
