"""Input parsing for Anki deck card files.

Supports:
- Tab / comma / semicolon / pipe separated text files (auto-detected)
- Excel (.xlsx) files with named columns

The Card dataclass carries optional tts_front / tts_back strings that hold
the plain text to be spoken when TTS is enabled.  The front/back fields
may contain HTML; tts_* fields are always plain text.
"""

import csv
import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Card:
    front: str
    back: str
    tags: List[str] = field(default_factory=list)
    tts_front: str = ""   # plain text for front audio (falls back to stripped front)
    tts_back: str = ""    # plain text for back audio (empty = no back audio)
    tts_examples: List[str] = field(default_factory=list)  # plain French example texts (JSON cards)


# ---------------------------------------------------------------------------
# Delimited text files (TSV / CSV / TXT)
# ---------------------------------------------------------------------------

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
        delimiter: Column separator. Auto-detected if None.
        has_header: Whether the first row is a header. Auto-detected if None
            (looks for 'front'/'back' in first row, case-insensitive).
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


# ---------------------------------------------------------------------------
# Excel (.xlsx) files
# ---------------------------------------------------------------------------

def _build_back_html(
    row_data: Dict[str, str],
    back_cols: List[str],
    tts_back_col: Optional[str],
    col_labels: Dict[str, str],
) -> str:
    """Format back-side HTML from a row's column values."""
    parts = []
    for col in back_cols:
        val = row_data.get(col, "").strip()
        if not val:
            continue
        label = col_labels.get(col, col)
        if col == tts_back_col:
            # Example / spoken sentence: visually separated and italicised
            parts.append(
                f'<div style="margin-top:8px;font-style:italic;color:#444">{val}</div>'
            )
        else:
            parts.append(f"<div><b>{label}:</b> {val}</div>")
    return "\n".join(parts)


def read_cards_excel(
    path,
    front_col: str = "French",
    back_cols: Optional[List[str]] = None,
    tts_back_col: Optional[str] = None,
    col_labels: Optional[Dict[str, str]] = None,
    sheet_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[Card]:
    """Read flashcards from an Excel (.xlsx) file with named columns.

    Args:
        path: Path to the .xlsx file.
        front_col: Column name to use as the card front (also becomes tts_front).
        back_cols: Column names to include in the back (default: all except front_col).
            The order determines display order.
        tts_back_col: Column whose plain text is spoken on the back side
            (e.g. "Example" for a French example sentence).  It is styled
            differently in the HTML back field.
        col_labels: Display labels for back columns, e.g. {"English": "EN"}.
            Defaults to the column name itself.
        sheet_name: Sheet to read (default: first sheet).
        tags: Tags to attach to every card.

    Returns:
        List of Card objects with tts_front and optionally tts_back set.

    Example::

        cards = read_cards_excel(
            "vocabulary.xlsx",
            front_col="French",
            back_cols=["English", "Persian", "Example"],
            tts_back_col="Example",
            col_labels={"English": "EN", "Persian": "FA"},
        )
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl is required for Excel support: pip install openpyxl")

    path = Path(path)
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    col_index = {name: i for i, name in enumerate(header)}

    if front_col not in col_index:
        raise ValueError(f"Column '{front_col}' not found. Available: {header}")

    if back_cols is None:
        back_cols = [c for c in header if c and c != front_col]

    missing = [c for c in back_cols if c not in col_index]
    if missing:
        raise ValueError(f"Column(s) not found: {missing}. Available: {header}")

    _col_labels = {c: c for c in back_cols}
    if col_labels:
        _col_labels.update(col_labels)

    _tags = list(tags) if tags else []
    cards: List[Card] = []

    for row in rows[1:]:
        row_data = {
            name: (str(row[i]).strip() if row[i] is not None else "")
            for name, i in col_index.items()
        }

        front_val = row_data.get(front_col, "").strip()
        if not front_val:
            continue

        back_html = _build_back_html(row_data, back_cols, tts_back_col, _col_labels)

        tts_back = ""
        if tts_back_col:
            tts_back = row_data.get(tts_back_col, "").strip()

        cards.append(Card(
            front=front_val,
            back=back_html,
            tags=_tags,
            tts_front=front_val,
            tts_back=tts_back,
        ))

    wb.close()
    return cards


# ---------------------------------------------------------------------------
# JSON (dictionary-style vocab / grammar cards)
# ---------------------------------------------------------------------------

def _wrap_clickwords(text: str) -> str:
    """Wrap each word of French text in a clickable span for the Anki template.

    Punctuation is stripped from data-word (used for dictionary/conjugation
    lookup URLs) but kept in the visible text.
    """
    tokens = re.split(r"(\s+)", text)
    parts = []
    for tok in tokens:
        if tok.strip() == "":
            parts.append(tok)
            continue
        clean = re.sub(r"[.,!?;:«»\"']", "", tok).lower()
        parts.append(
            f'<span class="clickword" data-word="{html.escape(clean)}">'
            f'{html.escape(tok)}</span>'
        )
    return "".join(parts)
