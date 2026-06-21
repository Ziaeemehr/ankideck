"""Input parsing for Anki deck card files.

Supports tab-separated, comma-separated, semicolon-separated, and pipe-separated
files, with or without a header row. Delimiter and header presence are auto-detected
when not specified.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Card:
    front: str
    back: str
    tags: List[str] = field(default_factory=list)


def _sniff_delimiter(path: Path) -> str:
    with path.open(encoding="utf-8", errors="replace") as f:
        sample = f.read(4096)
    for char in ("\t", ";", ",", "|"):
        if char in sample:
            return char
    return "\t"


def read_cards(
    path,
    delimiter: Optional[str] = None,
    has_header: Optional[bool] = None,
    front_col: int = 0,
    back_col: int = 1,
    tag_col: Optional[int] = None,
) -> List[Card]:
    """Read flashcards from a delimited text file.

    Args:
        path: Path to the input file.
        delimiter: Column separator. Auto-detected from the file if None.
        has_header: Whether the first row is a header. Auto-detected if None
            (looks for 'front'/'back' in the first row, case-insensitive).
        front_col: Zero-based column index for the front field (default 0).
        back_col: Zero-based column index for the back field (default 1).
        tag_col: Zero-based column index for space-separated tags (default None).

    Returns:
        List of Card objects.
    """
    path = Path(path)
    if delimiter is None:
        delimiter = _sniff_delimiter(path)

    with path.open(encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f, delimiter=delimiter))

    if not rows:
        return []

    _front_col = front_col
    _back_col = back_col
    _tag_col = tag_col

    if has_header is None:
        first = [c.strip().lower() for c in rows[0]]
        has_header = "front" in first or "back" in first

    start = 0
    if has_header:
        header = [c.strip().lower() for c in rows[0]]
        if "front" in header:
            _front_col = header.index("front")
        if "back" in header:
            _back_col = header.index("back")
        if _tag_col is None and "tags" in header:
            _tag_col = header.index("tags")
        start = 1

    cards = []
    for row in rows[start:]:
        max_needed = max(_front_col, _back_col)
        if len(row) <= max_needed:
            continue
        front = row[_front_col].strip()
        back = row[_back_col].strip()
        if not front and not back:
            continue
        tags: List[str] = []
        if _tag_col is not None and len(row) > _tag_col:
            raw = row[_tag_col].strip()
            tags = [t for t in raw.split() if t]
        cards.append(Card(front=front, back=back, tags=tags))

    return cards
