#!/usr/bin/env python3
"""Demo: duplicate detection and removal.

Shows how combining two card lists (e.g. base + new batch) deduplicates
before writing — useful for keeping a deck up to date without creating
duplicate cards.

Run:
    python scripts/demo_dedup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck.reader import Card
from ankideck.dedup import find_duplicates, remove_duplicates
from ankideck.builder import write_apkg


def main():
    print("=== Demo: deduplication ===\n")

    # Simulate a base deck
    base = [
        Card("bonjour", "hello"),
        Card("merci", "thank you"),
        Card("chat", "cat"),
    ]

    # Simulate a new batch — some overlap, some truly new
    new_batch = [
        Card("merci", "thank you"),          # exact duplicate
        Card("<b>chat</b>", "cat"),          # HTML variant — still a duplicate
        Card("chien", "dog"),                # genuinely new
        Card("maison", "house"),             # genuinely new
    ]

    combined = base + new_batch
    print(f"Combined list: {len(combined)} cards")

    dupes = find_duplicates(combined)
    print(f"Duplicates found: {len(dupes)}")
    for dup_i, orig_i in dupes:
        print(f"  [{dup_i}] '{combined[dup_i].front}' duplicates [{orig_i}] '{combined[orig_i].front}'")

    unique = remove_duplicates(combined)
    print(f"\nAfter dedup: {len(unique)} cards")
    for c in unique:
        print(f"  {c.front!r:25s} → {c.back!r}")

    n = write_apkg("Demo Dedup", unique, "demo_dedup.apkg")
    print(f"\nWritten {n} cards to 'demo_dedup.apkg'")


if __name__ == "__main__":
    main()
