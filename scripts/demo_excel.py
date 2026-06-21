#!/usr/bin/env python3
"""Demo: build a deck from the sample Excel vocabulary file (no TTS).

Shows the Excel reader with multi-column back formatting.
Run:
    python scripts/demo_excel.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck.reader import read_cards_excel
from ankideck.builder import write_apkg

INPUT = Path(__file__).parent.parent / "samples" / "sample_vocabulary.xlsx"
OUTPUT = "demo_excel.apkg"


def main():
    print("=== Demo: deck from Excel (no TTS) ===\n")

    cards = read_cards_excel(
        INPUT,
        front_col="French",
        back_cols=["English", "Persian", "Example"],
        tts_back_col=None,       # no TTS in this demo
        col_labels={"English": "EN", "Persian": "FA"},
    )
    print(f"Loaded {len(cards)} cards from '{INPUT.name}'\n")
    for c in cards:
        print(f"Front : {c.front}")
        print(f"Back  : {c.back[:80]}...")
        print()

    n = write_apkg("Demo Excel", cards, OUTPUT)
    print(f"Written {n} cards to '{OUTPUT}'")
    print("Import into Anki: File → Import → demo_excel.apkg")


if __name__ == "__main__":
    main()
