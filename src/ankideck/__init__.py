"""ankideck — tools for creating Anki decks from text files.

Typical workflow:
    from ankideck.reader import read_cards
    from ankideck.dedup import remove_duplicates
    from ankideck.builder import write_apkg

    cards = read_cards("my_vocab.tsv")
    cards = remove_duplicates(cards)
    write_apkg("My Deck", cards, "my_deck.apkg")
"""

__version__ = "0.2.0"

from ankideck.reader import Card, read_cards
from ankideck.dedup import find_duplicates, remove_duplicates
from ankideck.builder import build_deck, write_apkg

__all__ = [
    "Card",
    "read_cards",
    "find_duplicates",
    "remove_duplicates",
    "build_deck",
    "write_apkg",
]
