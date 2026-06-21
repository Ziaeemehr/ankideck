"""Duplicate card detection and removal.

Comparison is done on normalized text (HTML stripped, lowercased,
whitespace collapsed) so minor formatting differences are ignored.
"""

import re
from typing import List, Tuple

from ankideck.reader import Card


def _normalize(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def find_duplicates(cards: List[Card], key: str = "front") -> List[Tuple[int, int]]:
    """Return (duplicate_index, original_index) pairs.

    For each card whose normalized field value matches an earlier card,
    a tuple is appended. The original is always the lower index.
    """
    seen: dict = {}
    result = []
    for i, card in enumerate(cards):
        val = _normalize(getattr(card, key))
        if val in seen:
            result.append((i, seen[val]))
        else:
            seen[val] = i
    return result


def remove_duplicates(
    cards: List[Card], key: str = "front", keep: str = "first"
) -> List[Card]:
    """Return a deduplicated list preserving original order.

    Args:
        cards: Input card list.
        key: Card attribute to compare ('front' or 'back').
        keep: 'first' keeps the earliest occurrence; 'last' keeps the latest.
    """
    if keep not in ("first", "last"):
        raise ValueError("keep must be 'first' or 'last'")

    seen: dict = {}
    for i, card in enumerate(cards):
        val = _normalize(getattr(card, key))
        if val not in seen or keep == "last":
            seen[val] = i

    keep_indices = set(seen.values())
    return [card for i, card in enumerate(cards) if i in keep_indices]
