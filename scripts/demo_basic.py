#!/usr/bin/env python3
"""Demo: build a simple deck from a tab-separated file (no TTS, no internet needed).

Run:
    python scripts/demo_basic.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck import read_cards, remove_duplicates, write_apkg

INPUT = Path(__file__).parent.parent / "samples" / "sample_tab_separated.tsv"
OUTPUT = "demo_basic.apkg"


def main():
    print("=== Demo: basic deck from TSV ===\n")

    cards = read_cards(INPUT)
    print(f"Loaded {len(cards)} cards from '{INPUT.name}'")
    for c in cards:
        print(f"  {c.front!r:30s} → {c.back!r}")

    cards = remove_duplicates(cards)
    n = write_apkg("Demo Basic", cards, OUTPUT)
    print(f"\nWritten {n} cards to '{OUTPUT}'")
    print("Import into Anki: File → Import → demo_basic.apkg")


if __name__ == "__main__":
    main()
