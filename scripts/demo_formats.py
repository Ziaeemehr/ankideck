#!/usr/bin/env python3
"""Demo: auto-detection of different input formats.

Shows that the reader handles tab, comma, semicolon, and header/no-header
automatically without any flags.

Run:
    python scripts/demo_formats.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck.reader import read_cards

SAMPLES = Path(__file__).parent.parent / "samples"


def show(label, path, **kwargs):
    cards = read_cards(path, **kwargs)
    print(f"{label} ({path.name})")
    for c in cards[:3]:
        print(f"  {c.front!r:30s} → {c.back!r}")
    if len(cards) > 3:
        print(f"  ... ({len(cards)} total)")
    print()


def main():
    print("=== Demo: auto-detect input formats ===\n")
    show("Tab-separated (no header)", SAMPLES / "sample_tab_separated.tsv")
    show("Comma-separated (no header)", SAMPLES / "sample_comma_separated.csv")
    show("Semicolon-separated (no header)", SAMPLES / "sample_semicolon_separated.csv")
    show("Tab-separated with Front/Back header", SAMPLES / "sample_with_header.tsv")
    show("With tags column", SAMPLES / "sample_with_tags.tsv")

    cards_tags = read_cards(SAMPLES / "sample_with_tags.tsv")
    print("Tags on first card:", cards_tags[0].tags)


if __name__ == "__main__":
    main()
