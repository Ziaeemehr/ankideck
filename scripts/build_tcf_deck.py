#!/usr/bin/env python3
"""Build the TCF vocabulary Anki deck from the Excel file.

Usage:
    python scripts/build_tcf_deck.py vocab.xlsx
    python scripts/build_tcf_deck.py vocab.xlsx --output tcf_vocab.apkg --tts

The deck is safe to re-import after updating the Excel file:
  - Existing cards keep their review history (GUIDs are stable per front text).
  - New rows are added as fresh cards.
  - Changed translations update the back without resetting progress.

In Anki: File → Import → select .apkg → tick
  "Update existing notes when first field matches".
"""

import argparse
import sys
from pathlib import Path

# Allow running directly from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ankideck.reader import read_cards_excel
from ankideck.builder import write_apkg


DECK_NAME = "TCF Vocabulary"
DEFAULT_OUTPUT = "tcf_vocabulary.apkg"
TTS_LANG = "fr"
TTS_CACHE = "tts_cache_tcf"


def main():
    p = argparse.ArgumentParser(
        description="Build TCF vocabulary Anki deck from Excel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("input", help="Path to the .xlsx vocabulary file")
    p.add_argument("--output", "-o", default=DEFAULT_OUTPUT,
                   help=f"Output .apkg path (default: {DEFAULT_OUTPUT})")
    p.add_argument("--tts", action="store_true",
                   help="Generate French TTS audio")
    p.add_argument("--engine", default="edge",
                   choices=["edge", "gtts", "elevenlabs", "voicebox"],
                   help="TTS engine to use with --tts (default: edge)")
    p.add_argument("--voicebox-profile",
                   help="Voice profile id from the local Voicebox app "
                        "(required for --engine voicebox)")
    p.add_argument("--tts-cache", default=TTS_CACHE,
                   help=f"Directory for cached MP3s (default: {TTS_CACHE}). "
                        "Use a fresh directory when switching engines, "
                        "otherwise cached audio from the old engine is reused.")
    p.add_argument("--clickwords", action="store_true",
                   help="Wrap French text in .clickword spans so the note "
                        "type's click-to-look-up popup (Reverso / "
                        "WordReference) works")
    p.add_argument("--no-dedup", action="store_true",
                   help="Skip duplicate removal (not recommended)")
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading: {input_path}")
    cards = read_cards_excel(
        input_path,
        front_col="French",
        back_cols=["English", "Persian", "Example"],
        tts_back_col="Example" if args.tts else None,
        col_labels={"English": "EN", "Persian": "FA"},
        clickwords=args.clickwords,
    )
    print(f"  {len(cards)} cards loaded")

    output = args.output if args.output.endswith(".apkg") else args.output + ".apkg"

    tts_options = {}
    if args.tts:
        if args.engine == "voicebox" and not args.voicebox_profile:
            print("Error: --engine voicebox requires --voicebox-profile",
                  file=sys.stderr)
            sys.exit(1)
        tts_options["engine"] = args.engine
        if args.voicebox_profile:
            tts_options["voicebox_profile_id"] = args.voicebox_profile
        print(f"Generating TTS audio (lang={TTS_LANG}, engine={args.engine}) "
              "— this may take a while...")
        print(f"  Cache dir: {args.tts_cache}")

    n = write_apkg(
        DECK_NAME,
        cards,
        output,
        check_duplicates=not args.no_dedup,
        tts_lang=TTS_LANG if args.tts else None,
        tts_cache_dir=args.tts_cache,
        **tts_options,
    )

    removed = len(cards) - n
    print(f"\nDone: {n} cards written to '{output}'" +
          (f" ({removed} duplicates skipped)" if removed else ""))
    print(f"\nImport into Anki:")
    print(f"  File → Import → {output}")
    print(f"  Tick 'Update existing notes when first field matches'")


if __name__ == "__main__":
    main()
